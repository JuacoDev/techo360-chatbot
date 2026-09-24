# Evaluación de alucinación fuera de dominio — v2 vs v3

> ⚠️ **MATERIAL DE INVESTIGACIÓN EN BRUTO — ESTADO TEMPORAL DEL REPO.**
> Esta carpeta se versiona para no perder la evidencia de una ronda de
> diagnóstico (24-sep-2026), **no** porque esta sea la forma definitiva en
> que debe quedar. Queda **pendiente consolidarla en un README definitivo
> una vez se decida el modelo final** (v3, un futuro v3.2, u otro): en esa
> consolidación deberían quedar solo las conclusiones y la metodología, y
> probablemente comprimirse o eliminarse los volcados de respuestas.
> Si estás leyendo esto y ya hay un modelo decidido, esta carpeta está
> vencida.

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

| | v2 | v3 |
|---|---|---|
| correcta | 45 (47,4%) | 43 (45,3%) |
| incorrecta | 10 (10,5%) | 25 (26,3%) |
| **alucinación** | **40 (42,1%)** | **27 (28,4%)** |
| se negó | 0 | 0 |

Sobre 95 preguntas puntuables (5 apartadas por confianza media del
evaluador, ver `RUBRICA.md`).

v2 queda **por encima** del umbral del 40% acordado; v3 **por debajo**.
Matiz importante: v3 no acierta más (45 → 43 correctas), sino que 13
respuestas migraron de `alucinación` a `incorrecta`. Se equivoca casi
igual de seguido, pero fabrica menos datos con apariencia de fuente.

## Archivos

| archivo | qué es |
|---|---|
| `preguntas_generales.py` | las 100 preguntas, su categoría, la respuesta de referencia y la confianza del evaluador |
| `RUBRICA.md` | criterio de las 4 categorías, **fijado antes** de leer las respuestas, con los casos límite resueltos |
| `correr_preguntas.py` | lanza las 100 preguntas contra el servicio y guarda cada respuesta |
| `puntajes_v2.py` / `puntajes_v3.py` | la clasificación manual de cada respuesta, con notas de los casos ilustrativos |
| `calcular.py` | agrega los porcentajes globales y por categoría, y compara dos versiones |
| `respuestas_v2.json` / `respuestas_v3.json` | las 200 respuestas completas, tal como las devolvió el servicio |
| `analizar_dataset.py` | mide qué proporción del dataset de fine-tuning es conocimiento general puro |

## Cómo reproducirlo

```bash
# 1. Levantar el servicio apuntando al modelo que se quiera medir
OLLAMA_MODEL=techo360-chatbot:v3 python -m uvicorn app.main:app --port 8078

# 2. Correr las 100 preguntas
python correr_preguntas.py http://localhost:8078 v3 respuestas_v3.json

# 3. Clasificar a mano en puntajes_v3.py y agregar
python calcular.py v2 v3
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
reales), pero sigue siendo un juicio — y es justo donde se juega la
diferencia de 13,7 puntos entre v2 y v3.

## Hallazgos de despliegue (no se cambió nada de esto)

- El servicio **desplegado** expone únicamente `GET /health`; `POST
  /chatbot/send` devuelve 404. El endpoint solo existe en el working tree.
- El tag `techo360-chatbot:latest` apunta a **v1**, y `app/main.py` usa
  `OLLAMA_MODEL=techo360-chatbot` por defecto.
- v3 no estaba empaquetado: existía solo como adaptador LoRA. Para esta
  prueba se fusionó y registró como `techo360-chatbot:v3` (ver
  `../ollama/Modelfile.v3`), **sin tocar** `v1`, `v2` ni `latest`.
