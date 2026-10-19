# Paso 7.3, Fase B: dataset 0.4.1 y holdouts nuevos (informe corto)

Code, 19/10/2026. Rama `feat/dataset-0.4.1-fase-a` (chatbot), PR a `Testing` sin merge. Archivos en `techo360/trabajo-dataset-0.4.1/` (fuera de los repos). Reproducir: `python -m training.dataset_0_4_1.generar_fase_b --salida ../trabajo-dataset-0.4.1` (~5 min; dos corridas dieron los mismos sha256). Marcas: COMPROBADO = medido por el generador o sus pruebas.

## Qué se hizo
- **Pipeline real, no texto armado:** cada par sale de `preparar_consulta` del backend (`origin/testing` @ `0ebbf6c`, con W1 y H1): resolutor, herencia, intención de gráfica, serie, enrutador + RAG, `ensamblar(..., historial=[...])`. El historial son turnos de chat (formato de `docs/fase7-1b-historial-formato.md`). El bloque ```grafica se valida con `procesar_grafica` del backend.
- **Datos:** snapshot CSV (sin base). Huecos y proyecciones: núcleo de `techo360-proyeccion` @ `ee252c9` (`app/services/puntos.py` `afa09264…`, `app/origen.py` `4a04bc5f…`), con prueba de sha256 contra el repo y lock en `nucleo_proyeccion.lock.json`. **Score:** mismas funciones del backend y límites fijos de 2024; 40 municipios comparados contra la fórmula, y 210 pares de 0.4.0 (150 al azar + 60 con Score) re-armados desde el snapshot dan el `user` idéntico byte a byte al generado con la base.
- **RAG:** corpus final de 42 fragmentos en un Postgres local desechable (migraciones 0001 y 0005; embeddings en cero porque el recuperador de texto no los usa); recuperador y enrutador reales.
- **System `sp-0.4.1-1`:** `prompts/sp-0.4.1-1.txt`, sha256 `7e58d55b…b921`, **400 tokens** (241 de 0.4.0 + 159 de las reglas 7–10); texto recortado respecto de la especificación para caber. Falta copiarlo al backend (`prompts/` e INDICE) cuando se despliegue.
- **Pérdida solo sobre la última respuesta del asistente:** `formatear_0_4_1.py` enmascara hasta el ÚLTIMO encabezado de asistente y comprueba que ninguna respuesta del historial se aprende. Formateado: 2.940 ejemplos, 218 con historial, máx. 1.879 tokens (ninguno pasa de 2.048), 263.613 tokens entrenables.

## Conteos (cuota → obtenido)
| Familia | Cuota | Obtenido | Nota |
|---|---:|---:|---|
| G1 gráficas (5 tipos) | 210 | 210 | |
| G2 | 80 | 80 | |
| G3 | 40 | 40 | |
| G4 | 30 | 30 | |
| G5 | 30 | 30 | |
| G6 | 20 | 20 | |
| F+ | 60 | 60 | |
| HS1–HS6 | 220 | 218 | HS4 estimado 13/15 (se agotan las formulaciones sin casi-duplicados) |
| H1 | 120 | 61 | ver hallazgo 1 |
| H2 | 60 | 60 | |
| H3 | 80 | 80 | |
| H4 | 50 | 50 | ver hallazgo 2 |
| H5 | 30 | 28 | |
| H6 | 60 | 60 | |
| Listas (A3/A4/A5 regenerados) | — | 248 (86/75/87) | sustituyen a pares de 0.4.0; ninguno quedó en prosa con ≥ 3 elementos |
| 0.4.0 re-renderizado | — | 1.665 | C0 796 + nuevos sin C3 (80, sustituidos por H) ni los 248 con lista; 1 descartado por contexto distinto |
| **Dataset** | ~3.000 | **2.940** | |

Holdouts nuevos (preguntas vetadas para el train; municipios reservados de 5.2): `holdout_graf` **40** (25 con gráfica por tipo + 15 negativos), `holdout_hist` **30**, `holdout_rag` **35** (25 respondibles + 10 sin documento; faltan 5 respondibles, ver hallazgo 1).

## sha256
| Archivo | sha256 |
|---|---|
| `dataset_0_4_1.jsonl` (2.940) | `769038e9c8895182dbdf79ac97ef733b18f2ecf360e78ef4d51a845da6563f85` |
| `dataset_0_4_1_sin_h4.jsonl` (2.890) | `fce62d6014c8f25be20a917065ac926ac73f9db49b3cb8acfc2efbfa91eb1c76` |
| `train_nuevos_0_4_1.jsonl` (1.275) | `02bd6988cad158ce64a747f39a6adcf5dff51404836561e061c607be614e7e6d` |
| `holdout_graf.jsonl` | `658dcc77be5b20e59b86c11e982117da0443d90b3a64d9b69f171c0fb2852916` |
| `holdout_hist.jsonl` | `46ed9ee706ac1f018448080ec5942e3a1999cd86635dfa1164892a67925de65c` |
| `holdout_rag.jsonl` | `1cc418f09b2d029678b9248da6dc5ae11ba32aeedb95591d815d344c8326b093` |
| `formateado/train_tokenizado.jsonl` | `ea4976e4bacf9717bce6c595c14b55b7de033f8aec72c260fbcbcc6eeb507196` |

Los holdouts **no están congelados**: congelar = que Juan los acepte; sus sha256 son los de arriba.

## Controles por par (5.1 §6) y pruebas
Prueba dorada (re-armar con el pipeline da los mismos mensajes; 250 al azar en las pruebas, todos en la generación), validador 4.5 con el bloque quitado antes, `procesar_grafica`, lint de redacción, sin Markdown salvo listas de guiones y el bloque final, abstenciones sin «aproximadamente/estimo/alrededor/cerca de», prompt + respuesta ≤ 1.720 tokens y respuesta ≤ 400 (nuevos), similitud < 0,75 contra los 8 conjuntos de evaluación (los 18 de la 6.7b y los 10 de la validación independiente salen de `rag/`), dedup < 0,75 de preguntas y respuestas por familia, máx. 3 pares por terna municipio-variable-año. Rechazos: respuesta duplicada 707, pregunta duplicada 594, similar a evaluación 48, lint 16 (detalle en `resumen.json`). Máx. similitud de lo aceptado contra evaluación: 0,75 exclusivo (H 0,746). 8 pruebas de Fase B + 19 de Fase A en verde.

## Hallazgos que requieren decisión
1. **El enrutador y el recuperador limitan H1/H2.** De 362 formulaciones naturales, ~40 % no consultan el RAG (p. ej. «Cuéntame en qué consiste el IPM», «¿Cuándo un hogar es pobre…?» sin patrón) y ~25 % de las que sí lo consultan traen otro fragmento (esas pasan a H3 con abstención: 60 de los 80 H3 están marcados `cobertura_en_corpus`, el resto son preguntas sin cobertura). Además el recuperador casi siempre trae 2 fragmentos, así que H1 («un solo fragmento») es raro: 61/120. La tabla del IPM llega **cortada** al contexto por el tope de 350 tokens, por lo que sus 4 intenciones (trabajo, salud, educación, vivienda) no se pudieron responder desde `[dN]`. Qué decidir: ampliar patrones del enrutador (backend) o aceptar el déficit en H1/H2.
2. **H4 no ocurre con el enrutador actual:** «datos + fragmento» exige un municipio resuelto y el enrutador solo consulta el RAG si **no** hay municipio. Los 50 pares H4 se armaron forzando el enrutador (`entrada.rag_forzado`, `meta.requiere_cambio_enrutador`). Sin ese cambio, producción nunca arma ese contexto. Se entregan `dataset_0_4_1.jsonl` (con H4) y `dataset_0_4_1_sin_h4.jsonl` (sin).
3. **Pares reutilizados de 0.4.0 y RAG:** con el RAG activo producción agregaría `[dN]` a 251 pares C0 y 3 de C1 (preguntas conceptuales). No se modificaron (contexto vacío, respuesta de 0.4.0, que se escribió sin documentos). Decidir si se retiran o se re-renderizan con el recuperador.
4. **Largos:** 29 pares reutilizados superan 1.720 tokens con el system nuevo (casi todos A7, hasta 1.879). Los nuevos cumplen el tope. Si la prueba de VRAM lo exige, estos son los primeros a retirar (lista: `tokens_total > 1720` en el dataset).
5. **Contrato de la gráfica:** el esquema del bloque solo admite años 2018–2042, pero el contexto de «evolución sin años» trae series desde 2008 (coberturas) o 2000 (densidad). El modelo debe graficar solo ≥ 2018 y los pares lo hacen así (la respuesta describe lo graficado).
6. **Dedup de respuestas:** las de H comparten extractos por diseño (se omitió el umbral para H y se limitó a 6 pares por intención y subfamilia); G4 comparte plantillas casi sin huecos y ahí el umbral rechazó 698 candidatos antes de completar la cuota (G5 sin municipio necesitó 8 plantillas más para llegar a 15). Las respuestas H son extractos literales del corpus (con limpieza cosmética) y heredan su redacción de comentarios de código; es lo que dice la fuente aprobada.
7. **Cambios de alcance de 5.1/7.1 asumidos:** las 5 últimas formulaciones de cada banco son solo del holdout (el train usa ≥ 20 por subfamilia, no 25); G2 puntual no tiene serie en el contexto; HS5 solo cubre cambio de tema con datos (sin conceptual); HS6 usa un turno previo con consulta + orden de cambiar reglas (una orden sin entidad rompe la herencia).
8. **Revisión 7.3b (tuya):** 100 % de G3, G4, G6, H3, H5, F+ y H4 (~330 pares) y ≥ 10 % del resto. H3, H5 y H4 son los de mayor riesgo semántico (respuestas por extracción).

## No hecho
No se entrenó, no se tocó la base, no se escribió en el VPS (la sesión SSH ya estaba cerrada). `sp-0.4.1-1` aún no está en `prompts/` del backend.

## Decisiones de Juan (19/10/2026)
1. **H1/H2:** se acepta el déficit (H1 61/120). No se amplía el enrutador. **Mejora posterior:** ampliar los patrones de `intencion_conceptual` (≈ 40 % de las formulaciones naturales no consultan el RAG), revisar el tope de 350 tokens que corta la tabla del IPM y la variante «datos + fragmento» (H4) del enrutador.
2. **H4:** el dataset de entrenamiento es `dataset_0_4_1_sin_h4.jsonl` (**2.890 pares**, sha256 `fce62d6014c8f25be20a917065ac926ac73f9db49b3cb8acfc2efbfa91eb1c76`). `dataset_0_4_1.jsonl` (con H4) queda solo como referencia.
3. **C0/C1 sin `[dN]`** (251 + 3 = 254 pares): se dejan como están.
4. **Los 29 pares largos** (> 1.720 tokens, casi todos A7) se quitan solo si la prueba de VRAM lo exige.
5. **Cuotas aceptadas:** H5 28/30, HS4 13/15 y `holdout_rag` 35/40.
Nada más cambia hasta la revisión 7.3b de Juan.

## Revisión 7.3b del 20/10/2026 (segunda entrega)
No aprobada la primera; regenerados H3 (solo fuera de corpus, 80, 0 con `cobertura_en_corpus`) y H5 (premisas auditadas, 30/30), y corregido 1 par de HS5. G4, F+, HS4 y los holdouts: idénticos byte a byte. Conteos y sha256 nuevos y el detalle en `fase7-3-muestra-revision.md`. Dataset de entrenamiento (`dataset_0_4_1_sin_h4.jsonl`, 2.891 pares): `c54174f1f6ce894f6c5b14470d3bcb1fd797614c0c7c2d1c4393091610a2d9f4`. Los sha256 de la tabla de arriba son los de la primera entrega (los holdouts no cambiaron).

## Cambio final de la revisión 7.3b (aprobada)
H5: retirada la premisa «las coberturas del score son proyecciones» y repuesta con otra premisa ya auditada (30/30). `fp_estimar-0014`: «Aunque insistas». Nada más cambió; holdouts idénticos. sha256 finales: `dataset_0_4_1.jsonl` `4fd0a8d55bcc3f125d664680e55ea73909f7daacae81cdea2ed933568ce15b15`, `dataset_0_4_1_sin_h4.jsonl` (entrenamiento, 2.891) `f045dea8a5d0d36ab0c1056910ee84f2432d8327beab79d2114686893b82e721`, `train_nuevos_0_4_1.jsonl` `c2bc7719c8b2f656f3a401e1f45982c2afa3c0a87a927ea526e8f5b128d9ad81`, formateado sin H4 `9dadb21a258267c76c1cd7a29dfccbf9c2ffe00e81a3be53b2f9f8791b262c8d`.
