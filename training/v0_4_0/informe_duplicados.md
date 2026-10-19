# Informe de respuestas duplicadas (train v3.3) — solo reporte, nada eliminado

Método (COMPROBADO): comparación exacta de `response` (strip) entre las 825 líneas de `dataset/entrenamiento_v3_3.jsonl`. Preguntas duplicadas: 0.

| Respuesta | Líneas | Preguntas | Qué se conserva |
|---|---|---|---|
| `9.` | L674, L760 | raíz cuadrada de 81 / jugadores en el campo en béisbol | Ambas (en `base`) |
| `5.` | L683, L754, L764, L770 | lados de un pentágono / jugadores de baloncesto / anillos olímpicos / vocales del español | Las cuatro (en `base`) |

Observaciones (COMPROBADO): las preguntas son distintas y la respuesta es de 2 caracteres; no son copias del mismo par sino coincidencias de respuestas numéricas cortas (de relleno fuera de dominio). Ninguna de las 6 líneas está retirada/actualizada/reconvertida; solo L683 figura en el CSV maestro (VIGENTE). Decisión de eliminar o no: pendiente de Juan/Claude (HIPÓTESIS: no son un problema de duplicación real).
