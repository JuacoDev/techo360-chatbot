# Dataset 0.4.1: bancos de G1–G6, F+, HS y listas (paso 7.3, Fase A)

Especificación: `techo360/claude/fase7-1-especificacion.md` y la adenda `fase7-1b-adenda-modelo-final.md` (manda donde chocan), `fase5-1-plantillas-pares.md`, `fase5-3-revision.md`.

## Qué hay

| Archivo | Contenido |
|---|---|
| `catalogo.py` | cuotas por subfamilia (G 410 + F+ 60 = 470), subconjunto de gráficas del modelo y `tipos_validos` (copia reducida de `validar_combinacion`) |
| `preguntas.py` | bancos de formulaciones de pregunta (≥ 25 por subfamilia, 20 subfamilias, 526 en total) con huecos documentados |
| `respuestas.py` | plantillas de respuesta (280), notas de proyección, alternativas de G3, rechazos de G6 y huecos permitidos/obligatorios por subfamilia |
| `bloque.py` | `armar_bloque` (determinista, esquema cerrado, sin valores ni `titulo`) y `validar_respuesta_g` (criterios de 7.3b: bloque único, válido, sin valores, ids y códigos copiados de la línea de opciones, al final) |
| `controles.py` | lint de 5.2b D1, huecos, dígitos literales, diversidad ponderada por cuota, deduplicación TF-IDF < 0,75 contra los conjuntos de evaluación, detección de intención (copia del detector de W1) |
| `preguntas_hs.py`, `respuestas_hs.py` | familias HS (adenda §4, 220 pares: HS1 50, HS2 50, HS3 40, HS4 30 en 15 real / 15 estimado, HS5 30, HS6 20): turno actual de cada seguimiento y plantillas de respuesta; el turno previo lo arma la Fase B con el ensamblador y el resolver con herencia de H1 |
| `listas.py` | regeneración de A3/A4/A5 con listas de guiones solo con ≥ 3 elementos (adenda §2), `armar_lista` y `validar_formato` (sin encabezados, tablas, negritas ni emojis) |
| `verificar_bancos.py` | corre todo y escribe `informe_fase_a.md` |
| `tests_bancos.py`, `tests_listas_hs.py` | 19 pruebas (`python -m unittest training.dataset_0_4_1.tests_bancos training.dataset_0_4_1.tests_listas_hs`); incluye que el validador 4.5 y el sanitizador 4.7 del backend no tocan los guiones |

## Qué falta (a 19/10/2026)

- **Snapshot de `mapcalordb`:** extraído el 19/10/2026 en una sesión SSH de solo lectura autorizada por Juan (log en `training/datos/snapshot_mapcalordb_20261019/ssh_log.txt`, sha256 en `SHA256SUMS`): `mapcalordb.csv` (167.031 filas, 5 variables de BD; el score se deriva) y `zonas_municipio.csv` (1.105). Falta el generador que lo use sin volver a la BD.
- Fase B, notas de Juan: (1) el Score de privación no está en el snapshot: se calcula con la función del backend (límites por año; el de 2024 es fijo) y una prueba compara una muestra con el backend; (2) huecos y proyecciones salen del núcleo de `techo360-proyeccion`, importado o copiado con prueba de sha256 y registro del commit.
- Generador (pares completos con el ensamblador real), H1–H6 y los controles por par: Fase B, tras «W1 y C3 fusionados».

## Reglas que cumplen los bancos

- Ninguna formulación ni plantilla trae dígitos literales: años, valores, códigos y falsificaciones entran por hueco.
- Preguntas de G1/G3/G4/G5/G6 activan la intención de gráfica; las de G2 y F+ revelar/ignorar/estimar no. Las de `lineas` son de evolución y las de ranking/agrupadas/medidor no (así el contexto trae la serie solo cuando corresponde).
- Respuestas: sin Markdown ni emojis; sin «de el»/«a el» (se usa `{Vde}`); sin minúscula tras punto; las de G3/G4/G5/F+ no usan «aproximadamente», «estimo», «alrededor», «cerca de».
- Ninguna apertura pesa más de 8 % y «Según…» no pasa de 3 % (ponderado por cuota).
- El bloque nunca está en la plantilla: lo agrega `armar_respuesta`.
