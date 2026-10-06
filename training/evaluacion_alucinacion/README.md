# Evaluación de alucinación fuera de dominio — v2 vs v3 vs v3.2

> ⚠️ **MATERIAL DE INVESTIGACIÓN EN BRUTO — ESTADO TEMPORAL DEL REPO.**
> Esta carpeta se versiona para no perder la evidencia de una ronda de
> diagnóstico (24-sep-2026), **no** porque esta sea la forma definitiva en
> que debe quedar. Queda **pendiente consolidarla en un README definitivo
> una vez se decida el modelo final** (v3.2, un futuro v3.3, u otro): en
> esa consolidación deberían quedar solo las conclusiones y la
> metodología, y probablemente comprimirse o eliminarse los volcados de
> respuestas. Si estás leyendo esto y ya hay un modelo decidido, esta
> carpeta está vencida.
>
> **v3.2 (24-sep-2026) queda como el modelo de referencia** de esta
> ronda — ver resultados abajo. Salvo que se abra una v3.3 para el caso
> de salud (único hallazgo abierto, ver más abajo), no hay más cambios
> de dataset ni de hiperparámetros pendientes.

## Qué se midió

Si el fine-tuning sobre el dominio de Techo 360 degradó la capacidad del
modelo de responder preguntas **ajenas al proyecto** — es decir, si las
alucinaciones ya documentadas en v1/v2/v3 son síntoma de overfitting y no
solo huecos puntuales de contenido.

100 preguntas de conocimiento general (ciencia, historia, geografía,
matemáticas, cultura, tecnología, salud, deportes, lengua), enviadas por
el **servicio real** (`POST /chatbot/send` de `app/main.py`, con el system
prompt sincronizado), no por una llamada directa a Ollama.

## Resultado

| | v2 | v3 | **v3.2** |
|---|---|---|---|
| correcta | 45 (47,4%) | 43 (45,3%) | **84 (88,4%)** |
| incorrecta | 10 (10,5%) | 25 (26,3%) | 8 (8,4%) |
| **alucinación** | **40 (42,1%)** | **27 (28,4%)** | **3 (3,2%)** |
| se negó | 0 | 0 | 0 |

Sobre 95 preguntas puntuables (5 apartadas por confianza media del
evaluador, ver `RUBRICA.md`).

v2 queda **por encima** del umbral del 40% acordado; v3 **por debajo**;
v3.2 **una novena parte** de v3. Matiz importante sobre v2→v3: v3 no
acertaba más (45 → 43 correctas), sino que 13 respuestas migraron de
`alucinación` a `incorrecta` — se equivocaba casi igual de seguido, pero
fabricaba menos datos con apariencia de fuente.

**v3→v3.2 es un patrón distinto y mejor**: no es solo que baje la
alucinación, es que **las respuestas correctas casi se duplican** (43 →
84). Esto confirma la causa raíz diagnosticada antes de entrenar v3.2 —
0 de los 592 pares de entrenamiento de v3 eran de conocimiento general
puro, y ninguno modelaba una respuesta corta (mediana de 91 palabras,
sin un solo ejemplo de "responder en una línea y parar"). El síntoma no
era falta de conocimiento factual sino el hábito aprendido de rellenar
cada respuesta con justificación — y esa justificación, cuando el tema
no era Techo 360, terminaba inventada.

### Por categoría (% de alucinación)

| categoría | v2 | v3 | **v3.2** |
|---|---|---|---|
| ciencia | 46,7% | 33,3% | **0,0%** |
| historia | 26,7% | 40,0% | **6,7%** |
| geografía | 54,5% | 27,3% | **9,1%** |
| matemáticas | 50,0% | 8,3% | **0,0%** |
| cultura | 50,0% | 35,7% | **0,0%** |
| tecnología | 40,0% | 30,0% | **0,0%** |
| salud | 0,0% | 12,5% | 12,5% |
| deportes | 40,0% | 40,0% | **0,0%** |
| lengua | 80,0% | 20,0% | **0,0%** |

Las dos categorías peores de v3 (historia e deportes, ambas 40,0%)
mejoraron drásticamente. **Salud es la única categoría sin cambio entre
v3 y v3.2** (12,5% en ambas) — ver "Hallazgo abierto" más abajo.

### Longitud de respuesta — mejora transversal, no solo memorización

| categoría | v3 (prom. palabras) | **v3.2** |
|---|---|---|
| ciencia | 67,3 | **1,8** |
| historia | 82,4 | **14,6** |
| geografía | 63,3 | **2,3** |
| matemáticas | 34,9 | **1,1** |
| cultura | 62,2 | **2,3** |
| tecnología | 68,2 | **7,4** |
| salud | 77,2 | **2,0** |
| deportes | 55,2 | **1,4** |
| lengua | 58,4 | **3,4** |

Mediana global: 59,5 → **2,0 palabras**. La caída es pareja en las 9
categorías, incluidas las que no recibieron ningún par nuevo de
entrenamiento en esa categoría específica — descarta que el modelo
simplemente memorizó los 189 pares nuevos; generalizó el *patrón* de
responder corto.

### Holdout ampliado (11 pares nunca vistos en entrenamiento)

Medición independiente de las 100 preguntas de evaluación: 11 pares de
conocimiento general apartados de los 200 generados para v3.2 (ver
`dataset/holdout.jsonl`, líneas 19-29), de confianza alta, que el modelo
**nunca vio durante el entrenamiento**.

| resultado | n |
|---|---|
| correcta | 8 / 11 |
| incorrecta | 3 / 11 |
| **alucinación** | **0 / 11** |

Las 3 incorrectas: gas más abundante en la atmósfera (responde
"oxígeno" en vez de "nitrógeno"), año de fin de la Segunda Guerra
Mundial (responde sobre Pearl Harbor 1941 en vez de contestar la
pregunta), y 9×8 (responde "1,125"). **Cero alucinaciones** en datos
genuinamente no vistos confirma que lo que se corrigió es el *formato*
de respuesta (corto, sin rellenar con justificación), no que el modelo
memorizó los 189 pares específicos del entrenamiento.

### Hallazgo abierto: salud sin mejora

`salud` es la única categoría que no mejoró (12,5% en v3 y en v3.2, 1
de 8 preguntas). Mismo patrón de fallo en ambas versiones: el modelo
inventa un término técnico no estándar para la célula que transporta
oxígeno ("hemociana" en v3, "hemocitina" en v3.2) en vez de responder
"glóbulo rojo" o "eritrocito". No amerita bloquear v3.2 como modelo de
referencia, pero queda anotado como candidato a revisar en una v3.3 si
se decide abrir una — posiblemente agregando más pares de vocabulario
médico/biológico específico al set de conocimiento general.

### Ejemplos, priorizando cambios v3 → v3.2

**Alucinación corregida** (el patrón dominante — el núcleo ya era
correcto en v3, pero llevaba una justificación inventada pegada):
- Juegos Olímpicos: v3 → "cada cinco años" + inventa una "Organización
  Internacional del Deporte"; v3.2 → *"Cuatro años."*
- Protocolo de correo: v3 → no responde SMTP, inventa que usa
  Flask-Mail y Google Workspace; v3.2 → *"SMTP."*
- Capilla Sixtina: v3 → inventa "Miguel Ángel Sánchez Coello" y tres
  pintores más; v3.2 → *"Michelangelo Buonarroti."*

**Alucinación persistente** (única respuesta larga que quedó en toda la
ronda, 4,6s de generación — sugiere que preguntas que invitan a
respuesta extensa siguen siendo el punto débil): Simón Bolívar — inventa
que "estudió leyes en San Fernando", que Colombia fue "el primer país"
en independizarse, y una cronología falsa de su regreso a la política
en 1830 para liderar la independencia de Perú (la campaña real de Perú
fue 1823-1826, no 1830).

**Alucinación nueva** (no estaba en v3): lago más grande del mundo →
inventa "el Gran Lago Saimaa, ubicado en Finlandia" (lago real, pero ni
cerca de ser el más grande — la referencia es el mar Caspio).

## Archivos

| archivo | qué es |
|---|---|
| `preguntas_generales.py` | las 100 preguntas, su categoría, la respuesta de referencia y la confianza del evaluador |
| `RUBRICA.md` | criterio de las 4 categorías, **fijado antes** de leer las respuestas, con los casos límite resueltos |
| `correr_preguntas.py` | lanza las 100 preguntas contra el servicio y guarda cada respuesta |
| `puntajes_v2.py` / `puntajes_v3.py` / `puntajes_v3_2.py` | la clasificación manual de cada respuesta, con notas de los casos ilustrativos |
| `calcular.py` | agrega los porcentajes globales y por categoría, y compara dos versiones |
| `respuestas_v2.json` / `respuestas_v3.json` / `respuestas_v3_2.json` | las respuestas completas, tal como las devolvió el servicio |
| `analizar_dataset.py` | mide qué proporción del dataset de fine-tuning es conocimiento general puro |

**Nota de nomenclatura**: el nombre de archivo/módulo usa `v3_2` (guion
bajo), no `v3.2` (punto) — `calcular.py` importa `puntajes_{version}`
como módulo Python, y un punto en el nombre rompe el import
(`puntajes_v3.2` se interpreta como atributo `.2` del paquete
`puntajes_v3`). El tag de Ollama y el resto del proyecto sí usan
`v3.2` con punto; solo estos dos archivos de esta carpeta usan guion
bajo por esta limitación de Python.

## Cómo reproducirlo

```bash
# 1. Levantar el servicio apuntando al modelo que se quiera medir
OLLAMA_MODEL=techo360-chatbot:v3.2 python -m uvicorn app.main:app --port 8078

# 2. Correr las 100 preguntas (usar v3_2, no v3.2, ver nota de arriba)
python correr_preguntas.py http://localhost:8078 v3_2 respuestas_v3_2.json

# 3. Clasificar a mano en puntajes_v3_2.py y agregar
python calcular.py v3 v3_2
```

## Límite metodológico, explícito

Quien generó las preguntas y quien juzgó las respuestas es el mismo
evaluador (Claude), comparando contra su propio conocimiento factual. Para
hechos estables (capitales, aritmética, fórmulas) el criterio es sólido;
las preguntas ambiguas o dependientes de la fecha se apartaron de
antemano. **No es una evaluación independiente**: los números sirven para
comparar dos versiones bajo un criterio constante, no como medida absoluta
auditada por un tercero.

Además, la frontera entre `alucinación` e `incorrecta` se resolvió con una
regla operativa fija (fabricar un dato específico vs. confundir dos cosas
reales), pero sigue siendo un juicio — y es justo donde se jugó la
diferencia de 13,7 puntos entre v2 y v3. En v3.2 esa frontera fue
relevante en dos casos concretos (preguntas 21 y 22, sobre Simón
Bolívar y la independencia de Colombia — ver notas en `puntajes_v3_2.py`),
donde hubo que distinguir explícitamente entre confundir dos fechas
reales (`incorrecta`) e inventar una institución o cronología que no
existió (`alucinación`).

## Hallazgos de despliegue (no se cambió nada de esto)

- El servicio **desplegado** expone únicamente `GET /health`; `POST
  /chatbot/send` devuelve 404. El endpoint solo existe en el working tree.
- El tag `techo360-chatbot:latest` apunta a **v1**, y `app/main.py` usa
  `OLLAMA_MODEL=techo360-chatbot` por defecto. Esto sigue siendo así
  después de v3.2 — no se tocó `latest` a propósito.
- v3 no estaba empaquetado: existía solo como adaptador LoRA. Para esta
  prueba se fusionó y registró como `techo360-chatbot:v3` (ver
  `../ollama/Modelfile.v3`), **sin tocar** `v1`, `v2` ni `latest`.
- v3.2 se entrenó, fusionó, convirtió a GGUF, cuantizó y registró como
  `techo360-chatbot:v3.2` (ver `../ollama/Modelfile.v3.2`) el mismo día
  (24-sep-2026), **sin tocar** `v1`, `v2`, `v3` ni `latest`.
