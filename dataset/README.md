# Dataset de entrenamiento — Techo 360 Chatbot

## Archivo canónico

- `entrenamiento.jsonl`: **450 pares**, fuente única de verdad para
  fine-tuning. Se edita/crece en este mismo archivo en rondas futuras — no
  se crean archivos nuevos por ronda.

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

## Composición actual

- 450 pares totales, 0 duplicados internos (por `instruction`).
- 280 con fuente (categorías a + c), 170 sin fuente (categoría b).
- Desglose por categoría: (a) 209 pares, (b) 170 pares, (c) 71 pares.
- 0 emojis, 0 montos en pesos ni datos volátiles (cupos, vigencias, topes
  de programas de subsidio).

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
verificar.
