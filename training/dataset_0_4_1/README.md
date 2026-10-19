# Dataset 0.4.1: bancos de G1–G6 y F+ (paso 7.3, Fase A)

Especificación: `techo360/claude/fase7-1-especificacion.md` (manda), `fase5-1-plantillas-pares.md`, `fase5-3-revision.md`.

## Qué hay

| Archivo | Contenido |
|---|---|
| `catalogo.py` | cuotas por subfamilia (G 410 + F+ 60 = 470), subconjunto de gráficas del modelo y `tipos_validos` (copia reducida de `validar_combinacion`) |
| `preguntas.py` | bancos de formulaciones de pregunta (≥ 25 por subfamilia, 20 subfamilias, 526 en total) con huecos documentados |
| `respuestas.py` | plantillas de respuesta (280), notas de proyección, alternativas de G3, rechazos de G6 y huecos permitidos/obligatorios por subfamilia |
| `bloque.py` | `armar_bloque` (determinista, esquema cerrado, sin valores ni `titulo`) y `validar_respuesta_g` (criterios de 7.3b: bloque único, válido, sin valores, ids y códigos copiados de la línea de opciones, al final) |
| `controles.py` | lint de 5.2b D1, huecos, dígitos literales, diversidad ponderada por cuota, deduplicación TF-IDF < 0,75 contra los conjuntos de evaluación, detección de intención (copia del detector de W1) |
| `verificar_bancos.py` | corre todo y escribe `informe_fase_a.md` |
| `tests_bancos.py` | 14 pruebas (`python -m unittest training.dataset_0_4_1.tests_bancos`) |

## Qué falta (a 19/10/2026)

- **Snapshot de `mapcalordb`:** NO se extrajo. Ver `training/datos/snapshot_mapcalordb_20261019/ssh_log.txt`: la primera sesión SSH se cortó tras el `SHOW` por un error mío (`docker exec -i` consumió el stdin del script) y la segunda fue denegada por el arnés. El script corregido está en `extraer_snapshot_remoto.sh` (3 `SELECT` de solo lectura).
- Generador (pares completos con el ensamblador real), H1–H6 y los controles por par: Fase B, tras «W1 y C3 fusionados».

## Reglas que cumplen los bancos

- Ninguna formulación ni plantilla trae dígitos literales: años, valores, códigos y falsificaciones entran por hueco.
- Preguntas de G1/G3/G4/G5/G6 activan la intención de gráfica; las de G2 y F+ revelar/ignorar/estimar no. Las de `lineas` son de evolución y las de ranking/agrupadas/medidor no (así el contexto trae la serie solo cuando corresponde).
- Respuestas: sin Markdown ni emojis; sin «de el»/«a el» (se usa `{Vde}`); sin minúscula tras punto; las de G3/G4/G5/F+ no usan «aproximadamente», «estimo», «alrededor», «cerca de».
- Ninguna apertura pesa más de 8 % y «Según…» no pasa de 3 % (ponderado por cuota).
- El bloque nunca está en la plantilla: lo agrega `armar_respuesta`.
