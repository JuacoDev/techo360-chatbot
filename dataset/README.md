# Dataset de entrenamiento — Techo 360 Chatbot

## Archivo canónico

- `entrenamiento.jsonl`: **214 pares**, fuente única de verdad para
  fine-tuning. Se edita/crece en este mismo archivo en rondas futuras — no
  se crean archivos nuevos por ronda.

## Formato

Un objeto JSON por línea:

```json
{"instruction": "...", "response": "...", "source": "..."}
```

El campo `source` está presente en los pares de categoría (a) — contenido
general sobre vivienda/pobreza/política pública colombiana, cada afirmación
factual respaldada por una fuente verificable (DANE, DNP, Minvivienda,
SSPD, leyes/decretos, jurisprudencia). Se omite por completo en los pares
de categoría (b) — específicos de Techo 360 (Score de Privación,
arquitectura, indicadores, casos especiales de datos), que no requieren
fuente externa.

## Composición actual

- 214 pares totales, 0 duplicados internos (por `instruction`).
- 138 con fuente (categoría a), 76 sin fuente (categoría b).
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
