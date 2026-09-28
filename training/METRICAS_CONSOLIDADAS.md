# Métricas consolidadas — v1 / v2 / v3 / v3.2 (para el documento de Fase IA)

Consolidado el 27-sep-2026. Todos los números vienen de archivos reales
en este repo (`training/eval_holdout_*.json`, `training/evaluacion_alucinacion/*`),
excepto los 5 puntos marcados **[registrado, sin respaldo crudo]** — ver
nota de pérdida de datos al final.

## ⚠️ Aviso de alcance por versión (leer antes de la tabla)

- **v1, v2, v3**: evaluados contra el holdout de 18 pares del dominio
  Techo 360 (`dataset/holdout.jsonl`, líneas 1-18), con **decodificación
  greedy** (determinística, `do_sample=False`).
- **v1 vs v3** además se **rehizo con muestreo real** (`temperature=0.3,
  top_p=0.9, repeat_penalty=1.15` — los parámetros reales de producción
  en Ollama), 5 corridas/par. **v2 nunca se re-evaluó con muestreo** —
  solo existe su comparación greedy.
- **v3.2 NO tiene evaluación contra el holdout de 18 pares del dominio**
  (ni greedy ni muestreo) — el archivo no existe. Lo que sí tiene es la
  evaluación de **alucinación fuera de dominio** (100 preguntas ajenas a
  Techo 360) y un holdout aparte de 11 pares de conocimiento general.
  **No hay ROUGE-L/rúbrica de v3.2 contra las preguntas de Techo 360.**

## 1. ROUGE-L (F1) — holdout de dominio, 18 pares

### Greedy (v1, v2, v3 — comparable entre sí)

| Categoría | Base | v1 | v2 | v3 |
|---|---:|---:|---:|---:|
| General | 0.1899 | 0.2426 | 0.2348 | **0.2567** |
| Con fuente | 0.1991 | 0.2466 | 0.2427 | **0.2574** |
| Sin fuente | 0.1807 | 0.2386 | 0.2268 | **0.2560** |

Fuente: `eval_holdout_rouge_l.json`, `_v2.json`, `_v3.json`.

### Muestreo real (v1 vs v3 — la que aplica a producción)

| Categoría | v1 (media 5 corridas) | v3 (media 5 corridas) |
|---|---:|---:|
| General | **0.2248** [registrado] | **0.2310** [registrado] |
| Con fuente | 0.2310 | 0.2330 |
| Sin fuente | 0.2186 | 0.2291 |

Fuente original: `eval_holdout_rouge_l_muestreo.json` — **perdido**, ver
nota final. Números generales tomados de lo ya registrado en esta
conversación; con/sin fuente sí siguen en `training/README.md`.

## 2. Rúbrica manual de exactitud/relevancia (1-5, auto-evaluación de IA)

### Greedy (v1, v2, v3)

**Exactitud**

| Categoría | Base | v1 | v2 | v3 |
|---|---:|---:|---:|---:|
| General | 1.167 | 2.944 | 2.389 | 2.944 |
| Con fuente | 1.222 | 2.778 | 2.222 | 2.444 |
| Sin fuente | 1.111 | 3.111 | 2.556 | **3.444** |

**Relevancia**

| Categoría | Base | v1 | v2 | v3 |
|---|---:|---:|---:|---:|
| General | 1.722 | 3.944 | 3.389 | 3.722 |
| Con fuente | 1.889 | 3.556 | 3.222 | 3.333 |
| Sin fuente | 1.556 | 4.333 | 3.556 | 4.111 |

Fuente: `eval_holdout_rubrica.json`, `_v2.json`, `_v3.json`.

### Muestreo real (v1 vs v3, por corrida individual — la que aplica a producción)

| Categoría | v1 | v3 |
|---|---:|---:|
| General | **2.033** [registrado] | **2.289** [registrado] |
| Con fuente | 2.067 | 2.111 |
| **Sin fuente** | **2.00** [registrado] | **2.47** [registrado] |

Fuente original: `eval_holdout_rubrica_muestreo.json` — **perdido**, ver
nota final. Con/sin fuente siguen en `training/README.md`; general
tomado de lo ya registrado en esta conversación.

## 3. Alucinación fuera de dominio (100 preguntas ajenas a Techo 360, 95 puntuables)

| | v2 | v3 | **v3.2** |
|---|---:|---:|---:|
| Correcta | 45 (47.4%) | 43 (45.3%) | **84 (88.4%)** |
| Incorrecta | 10 (10.5%) | 25 (26.3%) | 8 (8.4%) |
| **Alucinación** | **40 (42.1%)** | **27 (28.4%)** | **3 (3.2%)** |
| Se negó | 0 | 0 | 0 |

Verificado directo contra `puntajes_v2.py` / `puntajes_v3.py` /
`puntajes_v3_2.py` (conteo real de C/I/A/M) — coincide exacto con
`evaluacion_alucinacion/README.md`.

**Holdout ampliado v3.2 (11 pares de conocimiento general nunca vistos en entrenamiento)**:
correcta 8/11, incorrecta 3/11, **alucinación 0/11**. Fuente: `evaluacion_alucinacion/README.md`.

## 4. Hallazgos puntuales confirmados

| Hallazgo | Confirmación | Fuente |
|---|---|---|
| Nombres de repos (par 9) | v1 falla **5/5**, v3 acierta **5/5** bajo muestreo | [registrado, sin respaldo crudo] |
| Regresión TerriData vs. SSPD (par 17) | v1 mejor que v3 bajo muestreo (regresión real, confirmada, no artefacto de greedy) | [registrado, sin respaldo crudo] |
| Regresión variables del Score (par 5) | v1 mejor que v3 bajo muestreo | [registrado, sin respaldo crudo] |
| "Cobertura de internet" (par 11) | Alucinación **compartida y preexistente** en ambas versiones (1/5 cada una), no exclusiva de v3 | [registrado, sin respaldo crudo] |
| Alucinación "Dialogflow" (v3, muestreo) | **4/5 corridas**, no 5/5 — hueco de contenido (el dataset nunca combina "los 5 repos" + "qué tecnología usa cada uno" en un mismo par), no efecto tóxico del refuerzo de nomenclatura | `training/README.md` línea 2040-2042 (corrección explícita del propio texto) |
| Mejora alucinación fuera de dominio v3→v3.2 | **28.4% → 3.2%** (novena parte), con correctas casi duplicadas (43→84) | `evaluacion_alucinacion/puntajes_v3.py` + `puntajes_v3_2.py` (conteo directo) |

### ⚠️ Inconsistencia real encontrada en `training/README.md` (no del chat)

La sección "Recomendación final actualizada" (línea 2157) dice **"5/5"**
para Dialogflow, pero el propio texto 100 líneas antes (línea 2040-2042)
ya se había **autocorregido a "4/5"** explícitamente ("no 5/5 como se
reportó inicialmente — corregido tras releer el texto completo"). El
4/5 es el valor correcto (más reciente, con la corrección documentada);
el 5/5 de la sección de recomendación quedó desactualizado y nunca se
corrigió ahí. Documentado aquí para que no se propague el número viejo
al documento de Fase IA.

## 5. Nota metodológica: pérdida de datos crudos de la corrida de muestreo

Durante la limpieza de artefactos de entrenamiento (27-sep-2026), se
borraron por error de clasificación 6 archivos que en realidad eran el
resultado metodológico corregido (T-93 rehecho con muestreo real,
`temperature=0.3`, la comparación que sí aplica a producción), no
artefactos exploratorios descartables como sugería su nombre:

- `eval_holdout_muestreo.json` (180 generaciones crudas)
- `eval_holdout_rouge_l_muestreo.json`
- `eval_holdout_rubrica_muestreo.json`
- `evaluar_holdout_muestreo.py`
- `metrica_rouge_l_muestreo.py`
- `rubrica_manual_muestreo.py`

No se recuperaron (borrado directo, fuera de la papelera de reciclaje
de Windows y ya sincronizado en OneDrive). **Los agregados que
sobreviven** (arriba, marcados "[registrado, sin respaldo crudo]") son
los que quedaron citados en `training/README.md` antes del borrado y
los que el usuario confirmó de memoria de esta conversación — **no hay
forma de re-auditar generación por generación** esa corrida específica.
Si se necesita el detalle línea por línea en el futuro, hay que
re-ejecutar `evaluar_holdout_muestreo.py` (perdido) reconstruyéndolo, o
aceptar los agregados aquí documentados como el registro final de esa
corrida.
