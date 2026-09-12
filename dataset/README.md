# Dataset de entrenamiento — Techo 360 Chatbot

## Archivos

- `dataset_consolidado_40.jsonl` (en `Downloads/files pi2/`, fuera de este repo): 40 pares semilla originales, ya validados, que definen el formato y el estilo de referencia.
- `entrenamiento_v1.jsonl`: **174 pares nuevos**, generados en esta ronda de escalamiento. No incluye los 40 pares semilla.

Para entrenar, concatenar ambos archivos (semilla primero, luego `entrenamiento_v1.jsonl`), o usarlos como dos shards del mismo dataset — el formato es idéntico en ambos.

## Formato

Un objeto JSON por línea:

```json
{"instruction": "...", "response": "...", "source": "..."}
```

El campo `source` está presente en los pares de categoría (a) — contenido general sobre vivienda/pobreza/política pública colombiana, cada afirmación factual respaldada por una fuente verificable (DANE, DNP, Minvivienda, SSPD, leyes/decretos, jurisprudencia). Se omite por completo en los pares de categoría (b) — específicos de Techo 360 (Score de Privación, arquitectura, indicadores, casos especiales de datos), que no requieren fuente externa.

## Composición de `entrenamiento_v1.jsonl`

- 174 pares totales.
- 108 de categoría (a) con fuente (62.1%).
- 66 de categoría (b) sin fuente (37.9%).
- 0 duplicados internos, 0 duplicados de pregunta contra los 40 pares semilla, 0 emojis, 0 montos en pesos ni datos volátiles (cupos, vigencias, topes en pesos de programas de subsidio).
