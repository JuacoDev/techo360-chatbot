# Dataset de entrenamiento — Techo 360 Chatbot

## Archivo canónico

- `entrenamiento.jsonl`: **582 pares**, fuente única de verdad para
  fine-tuning. Se edita/crece en este mismo archivo en rondas futuras — no
  se crean archivos nuevos por ronda.
- `holdout.jsonl`: **18 pares**, apartados exclusivamente para evaluación
  (T-93) — nunca deben usarse para entrenar. Ver sección
  [Holdout de evaluación](#holdout-de-evaluación-t-69) más abajo.

## Formato

Un objeto JSON por línea:

```json
{"instruction": "...", "response": "...", "source": "..."}
```

El campo `source` está presente en los pares de categoría (a) y (c) —
afirmaciones factuales respaldadas por una fuente verificable (DANE, DNP,
Minvivienda, SSPD, INS, IGAC, leyes/decretos, jurisprudencia). Se omite por
completo en los pares de categoría (b) — específicos de Techo 360 (Score
de Privación, arquitectura, indicadores, casos especiales de datos), que
no requieren fuente externa.

Tres categorías de contenido:

- **(a) General/core, con fuente**: política pública colombiana de
  vivienda y pobreza — IPM/metodología Alkire-Foster, déficit habitacional,
  cobertura de acueducto/alcantarillado, y normativa institucional
  relacionada. Ancla directamente el Score de Privación de Techo 360.
- **(b) Techo 360, sin fuente**: contenido propio del sistema — cálculo
  exacto del Score de Privación, arquitectura de los cinco repositorios,
  stack técnico (FastAPI, PostGIS, pgvector, LightGBM, Redis, RabbitMQ,
  Ollama), autenticación y OTP, y casos especiales de calidad de dato
  (fuentes bloqueadas, agregados nacionales mal etiquetados, DIVIPOLA).
- **(c) Híbrida, con fuente**: conecta explícitamente el Score de
  Privación (o cualquier indicador) de Techo 360 con el dato oficial o la
  normativa que lo respalda o lo limita — por ejemplo, por qué el score de
  un municipio puede no coincidir con el IPM oficial del DANE, o de qué
  fuente exacta proviene cada variable del panel. Esta categoría existe
  desde la segunda ronda de escalamiento (ver historial abajo).

## Composición actual (`entrenamiento.jsonl`)

- 582 pares totales, 0 duplicados internos (por `instruction`).
- 361 con fuente (categorías a + c) — 62.0%, 221 sin fuente (categoría b)
  — 38.0%.
- Desglose por categoría: (a) 247 pares, (b) 221 pares, (c) 114 pares.
- 0 emojis, 0 montos en pesos ni datos volátiles (cupos, vigencias, topes
  de programas de subsidio).
- Cifras antes de separar el holdout de T-69 (600 pares totales, 370 con
  fuente / 230 sin fuente, (a) 254 / (b) 230 / (c) 116) quedan trazables
  en el commit anterior a T-69 y en las secciones de historial abajo.

## Historial de consolidación

`entrenamiento.jsonl` es la fusión de dos rondas que antes vivían como
archivos separados y requerían concatenarse manualmente para entrenar:

- **40 pares semilla** (`dataset_consolidado_40.jsonl`, fuera del repo
  originalmente en `Downloads/files pi2/`): pares originales que definieron
  el formato y el estilo de referencia. Ya validados.
- **174 pares** (`entrenamiento_v1.jsonl`, commit
  `82a8ec3`): primera ronda de escalamiento, sin duplicados contra los 40
  semilla. 108 de categoría (a) con fuente (62.1%), 66 de categoría (b) sin
  fuente (37.9%).

Ambos se fusionaron en un solo archivo (`entrenamiento.jsonl`, orden:
semilla primero, luego v1) para eliminar el paso manual de concatenación
antes de entrenar. `entrenamiento_v1.jsonl` fue eliminado del repo — su
contenido y estadísticas quedan trazables en el commit `82a8ec3` y en este
README.

### Lotes intermedios descartados (no migrados al repo)

Durante la generación de los 40 pares semilla se trabajó en cuatro lotes
temáticos por separado (`dataset_v2_lote1_vivienda_pobreza.jsonl`,
`dataset_v2_lote2_cobertura.jsonl`, `dataset_v2_lote3_techo360.jsonl`,
`dataset_v2_lote4_marco_vis_vip.jsonl`, 12+8+10+10 = 40 pares). Se verificó
que la unión exacta de los cuatro lotes es idéntica, par por par, a
`dataset_consolidado_40.jsonl` — son el mismo contenido dividido por
categoría durante el trabajo de redacción, ya absorbido por completo en el
consolidado. No se copiaron al repo por ser archivos de trabajo muertos una
vez consolidados; se eliminaron de `Downloads/files pi2/`.

### Segunda ronda de escalamiento (236 pares nuevos, 2026-09-16)

Sobre la base de 214 pares (138 con fuente / 76 sin fuente), se agregaron
236 pares nuevos directamente a `entrenamiento.jsonl` (sin archivos
intermedios por lote), verificados por muestreo contra fuentes primarias
antes de incorporarse:

- **71 pares (a)**: enfocados exclusivamente en IPM/Alkire-Foster,
  déficit habitacional y cobertura de acueducto/alcantarillado — el
  núcleo que sostiene el Score de Privación. Se evitó deliberadamente
  seguir profundizando en normativa institucional de cola larga
  (curadurías, leasing habitacional, fiducia inmobiliaria, resguardos
  indígenas, ORIP, CAR), ya sobre-representada en la ronda anterior.
- **94 pares (b)**: profundizan el cálculo exacto del Score de Privación
  (fórmula, casos nulos, normalización), el stack técnico real
  (LightGBM por variable en el servicio de proyección, límites de RAM
  por contenedor, scripts de despliegue/rollback/backup), OTP y
  autenticación (límites de intentos, rate-limiting por IP), y casos
  reales de calidad de dato encontrados en el código de ingesta (el
  adaptador del FNA quedó bloqueado por baja del dataset origen, el
  agregado nacional "01001" de TerriData se filtra explícitamente, la
  tenencia informal se mide en predios del catastro IGAC y no en
  hogares). Se revisó la lista completa de los 76 pares (b) existentes
  antes de escribir, para no duplicar preguntas ya cubiertas.
- **71 pares (c)**, categoría nueva: conectan explícitamente el Score de
  Privación con el dato oficial o la normativa — por ejemplo, por qué el
  score de un municipio puede diferir del IPM oficial del DANE, de qué
  fuente exacta (TerriData, censo DANE, catastro IGAC) proviene cada
  variable, y por qué no es correcto citar el score como si fuera una
  cifra oficial del DANE.

Verificación aplicada: además de una investigación inicial de fuentes
oficiales (DANE, INS, SSPD), se hicieron verificaciones cruzadas
independientes de las cifras estadísticas de mayor reúso en el lote
(déficit habitacional 2024, prevalencia de privaciones del IPM 2024,
cobertura de acueducto CNPV 2018, definición del IRCA), cada una
confirmada contra al menos dos fuentes independientes, incluyendo los
boletines oficiales del DANE y del INS. Cifras que no pudieron
confirmarse con una fuente primaria legible (por ejemplo, un ranking
departamental exacto de cobertura de acueducto/alcantarillado 2023, o
los nombres de los integrantes académicos del Comité de Expertos del
IPM) se excluyeron deliberadamente del dataset en lugar de incluirse sin
verificar. Cuando la fuente sí respaldaba el hecho general pero no un
detalle específico (los organismos exactos que integran el Comité de
Expertos), se generalizó también la pregunta para no prometer más
especificidad de la que la respuesta entrega (ver commit `4cb0f93`).

### Tercera ronda de escalamiento (150 pares nuevos, 2026-09-16)

Sobre la base de 450 pares (280 con fuente / 170 sin fuente), se agregaron
150 pares nuevos manteniendo la proporción ~30/40/30 de la ronda anterior:

- **45 pares (a)**: siguen priorizando IPM/Alkire-Foster, déficit
  habitacional y cobertura de servicios públicos. Hallazgo principal de
  esta ronda: el DANE sí publicó, en 2020, una "Medida de pobreza
  multidimensional de fuente censal" con representatividad **municipal**
  (e incluso a nivel de manzana urbana) con base en el Censo 2018 —
  distinta del IPM anual por encuesta, que solo tiene representatividad
  nacional/regional. Se incluyen los municipios extremos de esa medida
  (Uribia, Cumaribo, Alto Baudó como los de mayor incidencia; Sabaneta,
  Envigado, Chía como los de menor) — ver nota de verificación abajo
  sobre el nivel de confianza distinto entre la existencia de la medida y
  estas seis cifras puntuales. El resto evita normativa de cola larga,
  igual que la ronda anterior.
- **60 pares (b)**: nueva lectura del código real de los repos —
  `ingestion/scheduler.py` (cron semanal de indicadores vs. trimestral de
  geometría IGAC, guardia contra doble ejecución vía Redis, ejecución en
  hilo aparte para no bloquear FastAPI), `services/email_service.py`
  (cupo diario de Brevo, umbral de advertencia al 85%, TTL de 26h),
  `ingestion/validacion.py` (reglas de aceptación de datos: no nulo, no
  negativo, identificador de municipio obligatorio, advertencia — no
  rechazo — ante variación mayor al 60% interanual), `core/config.py`
  (por qué unas variables de entorno tienen default de desarrollo y
  otras no) y `setup-server.sh` (usuario de sistema limitado para
  despliegue en vez de root). También profundiza en normalización
  mínimo-máximo frente a valores atípicos, y en el frontend/stack
  (FastAPI, SQLAlchemy, SPA, Ollama). Se revisó la lista completa de los
  170 pares (b) existentes antes de escribir.
- **45 pares (c)**: conectan el hallazgo de la medida censal municipal
  del DANE con el Score de Privación (por qué Techo 360 no la usa como
  fuente directa, pese a tener granularidad municipal, dado que no se
  actualiza periódicamente), además de nuevas conexiones entre
  normativa/entidades ya cubiertas en (a) de rondas previas y el
  comportamiento real del score.

Verificación aplicada: la **existencia** de la "Medida de pobreza
multidimensional de fuente censal" (DANE, 2020, base CNPV 2018) como
producto oficial del DANE está confirmada contra tres fuentes
independientes distintas — dos páginas oficiales separadas de
dane.gov.co (una de ellas el boletín técnico, la otra la página de
"actualidad-dane") y un tercero externo (Multidimensional Poverty Peer
Network, MPPN). Las **seis cifras municipales puntuales** que se citan
como ejemplo de esa medida (Uribia 92,2%, Cumaribo 91,4%, Alto Baudó
90,6%, Sabaneta 4,5%, Envigado 4,9%, Chía 6,7%, líneas 434-435 de
`entrenamiento.jsonl` — antes 452-453, desplazadas -18 tras separar el
holdout de T-69) tienen un nivel de verificación distinto y más
débil: no se leyó directamente el boletín del DANE (los PDF del DANE
resultan ilegibles para extracción automática, igual que en la ronda
anterior), por lo que esas seis cifras descansan en **una sola fuente
periodística independiente** (elpilon.com.co) más resúmenes de buscador
que citan el mismo boletín sin que se haya podido confirmar la cifra
línea por línea contra el documento original. Las respuestas de esas dos
líneas ya se redactaron con el calificador "según fuentes que citan el
boletín del DANE" para reflejar esta diferencia, en vez de presentarlas
con la misma firmeza que el resto del corpus. El resto del contenido (b)
proviene directamente de lectura del código fuente de los repos, no
requiere verificación externa.

Autorrevisión de desajuste pregunta/respuesta: se revisaron los 150
pares nuevos aplicando el mismo criterio que corrigió el caso del
Comité de Expertos del IPM (ronda anterior). Se encontraron y corrigieron
4 preguntas que prometían más especificidad de la que la respuesta
entregaba — en los cuatro casos se generalizó la pregunta en vez de
inventar el dato faltante (números de línea originales; ver nota sobre
el desplazamiento -18 tras T-69 más abajo):
- Línea 459 → **441** (barreras de acceso a cuidado de primera infancia):
  la pregunta pedía el grupo de edad exacto, la respuesta no lo daba.
- Línea 480 → **462** (bajo logro educativo): la pregunta pedía la edad
  mínima exacta, la respuesta no la daba.
- Línea 494 → **476** (ECV, versión anterior): la pregunta pedía el año
  exacto desde el que se aplica de forma continua, la respuesta no lo daba.
- Línea 530 → **512** (modelo de lenguaje del chatbot): la pregunta pedía
  el modelo "específico", la respuesta solo da un rango de tamaño y el
  motor (Ollama), consistente con que el código real lo deja como
  ejemplo no decidido.

No se descartó ningún par completo en esta ronda por falta de fuente —
se mantiene el conteo exacto 45/60/45 = 150.

## Holdout de evaluación (T-69)

`holdout.jsonl` contiene **18 pares** apartados de `entrenamiento.jsonl`
exclusivamente para la evaluación posterior del modelo entrenado (T-93).
**Nunca deben usarse para entrenar** — ni en este fine-tuning ni en
ninguno futuro sobre este mismo dataset — precisamente para poder medir,
con datos que el modelo nunca vio, si aprendió el contenido central o
solo memorizó lo que se le mostró en entrenamiento.

**Criterios de selección**:
- **Cobertura de ambas categorías amplias**: 9 pares con fuente
  (categorías a+c, política pública general e híbrida) y 9 pares sin
  fuente (categoría b, específicos de Techo 360) — ningún extremo
  sobre-representado.
- **Representatividad de temas centrales**, no casos raros ni de cola
  larga: de (a) se tomaron las definiciones y cifras nacionales más
  básicas (qué es el IPM, sus 15 indicadores, el umbral de privación,
  déficit habitacional cuantitativo/cualitativo, cobertura nacional de
  acueducto y alcantarillado, qué es la VIS); de (c) las dos preguntas
  híbridas más fundamentales (si el Score de Privación equivale al IPM
  oficial, y cómo se compara la cobertura de acueducto de Techo 360 con
  la de la SSPD); de (b) los conceptos base de la plataforma (qué es
  Techo 360, qué es el Score de Privación, cómo se calcula paso a paso,
  cuándo queda nulo, los cinco repositorios, las siete variables y sus
  fuentes, autenticación, y el rol del servicio de proyección).
- **Sin problemas de calidad conocidos**: se excluyeron explícitamente
  las cuatro preguntas corregidas por desajuste pregunta/respuesta y las
  dos líneas con verificación más débil (las cifras municipales de la
  medida censal, líneas 434-435) — el holdout debe medir aprendizaje
  contra pares de máxima confianza, no arrastrar ninguna duda de calidad
  ya documentada.

**Efecto en `entrenamiento.jsonl`**: bajó de 600 a 582 pares. Como se
retiraron 18 líneas de puntos distintos y anteriores a la línea 400, toda
referencia a un número de línea específico documentada en las secciones
de historial de arriba (para pares que no fueron parte del holdout) quedó
desplazada **-18** respecto al número original citado en su momento — se
anotó el nuevo número junto al original donde aplicaba, en vez de
reescribir silenciosamente la cifra histórica.
