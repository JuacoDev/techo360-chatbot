# Fase A de 7.3: bancos de preguntas y plantillas de respuesta (G1–G6 y F+)

Resultado: **sin fallos**. Generado por `python -m training.dataset_0_4_1.verificar_bancos`.

## Conteos por subfamilia

| Subfamilia | Cuota | Preguntas | Plantillas de respuesta | Con bloque |
|---|---:|---:|---:|:--:|
| g1_lineas_individual | 60 | 30 | 16 | sí |
| g1_lineas_comparar | 40 | 28 | 14 | sí |
| g1_barras_ranking | 40 | 28 | 14 | sí |
| g1_barras_agrupadas_ind | 24 | 25 | 12 | sí |
| g1_barras_agrupadas_cmp | 16 | 25 | 12 | sí |
| g1_gauge | 30 | 28 | 14 | sí |
| g2_serie | 40 | 26 | 14 | no |
| g2_comparacion | 20 | 26 | 12 | no |
| g2_puntual | 20 | 25 | 12 | no |
| g3_un_anio | 20 | 25 | 12 | no |
| g3_sin_dato | 20 | 25 | 12 | no |
| g4_tipo_no_soportado | 30 | 26 | 12 | no |
| g5_sin_municipio | 15 | 26 | 12 | no |
| g5_sin_variable | 15 | 26 | 12 | no |
| g6_valores | 10 | 25 | 12 | sí |
| g6_codigo | 10 | 25 | 12 | sí |
| fp_revelar | 15 | 28 | 20 | no |
| fp_ignorar | 15 | 26 | 20 | no |
| fp_falsos | 15 | 27 | 20 | no |
| fp_estimar | 15 | 26 | 16 | no |
| hs1_anio | 50 | 26 | 14 | no |
| hs2_municipio | 50 | 26 | 14 | no |
| hs3_variable | 40 | 25 | 12 | no |
| hs4_real | 15 | 25 | 12 | no |
| hs4_estimado | 15 | 25 | 12 | no |
| hs5_cambio_tema | 30 | 26 | 12 | no |
| hs6_inyeccion_previa | 20 | 26 | 12 | no |
| **Total** | **690** | **705** | **368** | |

Por familia: G1 210, G2 80, G3 40, G4 30, G5 30, G6 20, F+ 60, HS 220 (G 410 + F+ 60 + HS 220 = 690; H 400 queda para la Fase B).

Listas (adenda 7.1b §2), plantillas que regeneran A3/A4/A5 con ≥ 3 elementos: lst_serie 14 introducciones, lst_municipios 14 introducciones, lst_perfil 14 introducciones.

## Diversidad (ponderada por cuota; dos primeras palabras)

| Medida | Preguntas | Respuestas |
|---|---:|---:|
| Apertura más frecuente | y en (2.3%) | en huecoy (3.0%) |
| «Según…» | 0.0% | 0.2% |
| Aperturas distintas | 356 | 213 |

Límites: ninguna apertura > 8 %, «Según…» ≤ 3 %.

## Deduplicación (similitud < 0,75, TF-IDF de simlib)

Máximo coseno de cualquier formulación (renderizada con 3 muestras de huecos) contra cada conjunto de evaluación:

| Conjunto | Preguntas cargadas | Máximo coseno |
|---|---:|---:|
| holdout_v3_3 | 28 | 0.443 |
| holdout_v0_4 | 28 | 0.443 |
| holdout_ctx_v0_4 | 60 | 0.643 |
| conjunto_5_6b | 50 | 0.514 |
| preguntas_6_4 | 50 | 0.508 |
| rag_prueba | 10 | 0.312 |
| ciega_6_7b | 18 | 0.514 |

## Alcance de los controles

Estos controles son de **banco** (plantillas con huecos de muestra). Los controles por **par** (prueba dorada contra el ensamblador, validador 4.5, tokens medidos, dedup contra el dataset real) corren en la Fase B con el generador completo.

