# Fine-tuning local — Llama 3.2 (LoRA/QLoRA)

Este directorio documenta el proceso de fine-tuning del chatbot, que corre
**localmente** en la máquina de desarrollo (RTX 3050), no en el VPS ni en
ningún pipeline de este repo. El dataset de entrenamiento vive en
[`../dataset/`](../dataset/) — ver ese README para el detalle de los pares
instrucción/respuesta.

## T-71 — Entorno de entrenamiento local (completada 2026-09-15)

Se configuró desde cero un entorno virtual dedicado para fine-tuning
LoRA/QLoRA de Llama 3.2, en la máquina local de Juan David (GPU RTX 3050).

**Verificación de GPU/drivers**
- `nvidia-smi`: RTX 3050 detectada correctamente, driver 616.92, CUDA
  soportado por el driver hasta la versión 13.4.

**Entorno virtual**
- Herramienta: `venv` (Python 3.13.14).
- Ubicación: `C:\Users\Eridanus_2\entornos\techo360-finetuning` (local a la
  máquina, fuera de este repo — no se versiona).

**PyTorch con CUDA**
- Al momento de instalar, la matriz oficial de PyTorch no publicaba builds
  estables más allá de `cu128` (CUDA 12.8), aun con un driver que soporta
  hasta CUDA 13.4 — se usó `cu128` por compatibilidad hacia adelante:
  ```bash
  pip install torch --index-url https://download.pytorch.org/whl/cu128
  ```
- Instalado: **torch 2.11.0+cu128**.
- Verificado: `torch.cuda.is_available()` → `True`,
  `torch.cuda.get_device_name(0)` → `"NVIDIA GeForce RTX 3050 6GB Laptop GPU"`.

**Librerías de fine-tuning instaladas**
- `transformers` 5.17.0
- `peft` 0.21.0
- `bitsandbytes` 0.50.2 (rueda nativa de Windows, sin workarounds)
- `accelerate` 1.15.0
- `datasets` 5.0.1

Versiones exactas de todo el entorno (para reproducibilidad) en
[`requirements-finetuning.txt`](requirements-finetuning.txt).

**Problemas encontrados**: ninguno bloqueante. Dos warnings inofensivos al
importar (numpy ausente antes de instalar `transformers`; `triton not
found` — no se necesita triton para este flujo de trabajo).

**Estado**: entorno listo y verificado. Pendiente **T-72** (prueba de carga
del modelo Llama 3.2 en este entorno) — no se ejecutó en el alcance de T-71.

## T-72 — Prueba de humo: carga de Llama-3.2-1B-Instruct en 4-bit (completada 2026-09-16)

Objetivo: confirmar que un modelo Llama 3.2 carga correctamente en 4-bit
(QLoRA) en la RTX 3050 antes de comprometer tiempo en entrenamiento real.

**Modelo y decisión base vs. Instruct**: se usó `meta-llama/Llama-3.2-1B-Instruct`,
no la variante base. Esta decisión no estaba explícita en ningún documento
previo del proyecto — se tomó porque el dataset de `../dataset/` es
formato instrucción/respuesta, y porque el `docker-compose.yml` de
`techo360-infra` ya referencia la variante Instruct de Ollama
(`llama3.2:3b`) como precedente para el chatbot en producción.

**Acceso al modelo**: `meta-llama/Llama-3.2-1B-Instruct` está *gated*
(`gated: manual` en Hugging Face) — requiere solicitar acceso a la
licencia de Meta en la página del modelo y autenticar con un token
(`hf auth login`). El acceso fue aprobado y el login se hizo con la
cuenta `JuanTellezG` (org `upbcolombia`). El token se guardó únicamente
en la caché de Hugging Face del usuario
(`C:\Users\Eridanus_2\.cache\huggingface\token`), fuera de este repo —
nunca se escribió en ningún archivo versionado.

**Configuración de carga**: `BitsAndBytesConfig(load_in_4bit=True,
bnb_4bit_quant_type="nf4", bnb_4bit_compute_dtype=torch.bfloat16)` — se
usó `bfloat16` y no `float16` porque la RTX 3050 sí soporta bf16
(`torch.cuda.is_bf16_supported() == True`).

**Resultados**

| Métrica | Valor |
|---|---|
| Tiempo de carga (con descarga desde HF) | 56.4s |
| Tiempo de carga (caché local, corridas posteriores) | 5.3s |
| VRAM en reposo tras cargar el modelo | 1024 MB allocated / 1060 MB reserved |
| VRAM durante inferencia de prueba | 1032 MB allocated / 1068 MB reserved (pico 1049.5 MB) |
| Margen libre (de 6144 MB nominales) | ~5.1 GB |
| Tiempo de generación (prompt corto, 80 tokens) | 4.9s |

**Inferencia de prueba**: el modelo generó texto fluido y gramaticalmente
correcto en español (estructura con encabezados, oraciones bien formadas)
ante el prompt "¿Qué es el Score de Privación en Techo 360?" — confirma
que el modelo carga y genera correctamente en 4-bit, no solo que carga.
Como es esperable **antes** del fine-tuning, el contenido específico
sobre Techo 360 fue alucinado (inventó una definición sin relación con
el Score de Privación real); eso es precisamente lo que el entrenamiento
con el dataset debe corregir, no un fallo de esta prueba.

**Errores/warnings**: ninguno bloqueante. Warning de Hugging Face sobre
symlinks no soportados en Windows sin modo desarrollador (solo afecta
eficiencia de caché en disco), warning ya conocido de `triton not
found`, y un warning cosmético de `clean_up_tokenization_spaces` del
tokenizer BPE. Nota aparte: la consola de Windows mostró los acentos con
codificación incorrecta al imprimir el texto generado — es un problema
de code page de la terminal, no del modelo ni del texto real.

**Estado**: prueba de humo exitosa con margen amplio de VRAM (~5.1 GB
libres con el modelo de 1B). No se avanzó a entrenamiento real ni se
tocó el dataset — alcance limitado a carga + una inferencia de
verificación, según lo definido para T-72.

## T-73 — Prueba de estrés: viabilidad de Llama-3.2-3B-Instruct para entrenamiento real (completada 2026-09-16)

Objetivo: a diferencia de T-72 (solo carga + una inferencia), esta prueba
simula condiciones sostenidas de entrenamiento real — 4-bit NF4 + LoRA
aplicado sobre las 7 capas lineales del modelo (`q_proj`, `k_proj`,
`v_proj`, `o_proj`, `gate_proj`, `up_proj`, `down_proj`, `r=16,
lora_alpha=32`), corriendo steps reales (forward + backward +
optimizer.step()) con batches del dataset real de 600 pares, no solo
carga o inferencia.

**Configuración A — `batch_size=4` real, 40 steps: inestable, descartada**

| Métrica | Valor |
|---|---|
| VRAM tras cargar modelo base (4-bit) | 2139 MB allocated / 2188 MB reserved |
| VRAM tras aplicar LoRA | 2985 MB allocated / 3784 MB reserved |
| VRAM primer step | 3600 MB allocated / **5734 MB reserved** |
| VRAM steps 30-40 | 3600-3631 MB allocated / **10 474 MB reserved** |
| Tiempo por step | de 5.3s (inicio) a **211.9s** (step 31) — errático, sin estabilizarse |

La memoria reservada por PyTorch **superó los 6144 MB físicos de la
tarjeta** (llegó a 10 474 MB) sin lanzar un error de OOM explícito —
Windows y/o el paginado propio del optimizador `PagedAdamW8bit` absorben
el excedente vía memoria compartida del sistema en vez de crashear, pero
el costo es un colapso de rendimiento (10-40x más lento en los últimos
steps). Conclusión: **`batch_size=4` real no truena, pero tampoco sirve
para entrenar en la práctica** con 3B en esta GPU.

**Configuración B — `batch_size=1` real, 30 steps: estable**

| Métrica | Valor |
|---|---|
| VRAM durante los 30 steps | estable en **3920 MB reserved**, sin crecer |
| Tiempo por step | 1.42s – 3.44s, promedio 2.608s |
| Margen libre | ~2.2 GB |
| Tiempo estimado por época (600 pares) | 1564.7s ≈ 26.1 min |

**Configuración C — `batch_size=1` × `gradient_accumulation_steps=8`
(batch efectivo=8), 40 micro-steps: verificación puntual, estable — CONFIGURACIÓN RECOMENDADA**

Verificación adicional para confirmar que la acumulación de gradiente no
reproduce el problema de memoria creciente de la configuración A.

| Métrica | Valor |
|---|---|
| VRAM reserved durante los 40 micro-steps | plana en 3888-3918 MB, sin tendencia de crecimiento |
| VRAM peak | 3725.5 MB de 6144 MB nominales (margen libre ~2.4 GB) |
| Tiempo por micro-step | 0.98s – 2.25s, promedio 1.172s |
| Tendencia 1a vs. 2a mitad | 1.218s → 1.127s (mejoró levemente, **no degradó**) |
| `optimizer.step()` | ocurrió exactamente cada 8 micro-steps, como se esperaba |
| Tiempo estimado por época (600 pares) | 703.3s ≈ **11.7 min** |

Se comportó como la configuración B (plana), no como la A (creciente) —
confirma que la causa raíz del problema en la configuración A era
procesar 4 ejemplos simultáneamente en una sola pasada hacia adelante
(activaciones más grandes), no algo relacionado con el optimizador
`PagedAdamW8bit` en sí ni con acumulación de estado entre steps. No se
probó `gradient_accumulation_steps=4` por separado, dado que 8 ya resultó
estable y con mejor tiempo de época que `batch_size=1` puro.

**Temperatura / clocks / throttling** (igual en las tres configuraciones)

- Temperatura: 44-58°C en todo momento — nunca cerca de zona de
  throttling térmico, incluso durante los steps de 200+ segundos de la
  configuración A (confirma que esa lentitud fue por memoria, no por
  temperatura).
- Clocks: sostenidos en boost alto (1732-1762 MHz SM, 5501 MHz memoria)
  en las tres configuraciones — sin downclocking en ningún momento.
- Fan speed / power limit: `nvidia-smi` reportó `[N/A]` para ambos —
  típico en GPUs de laptop, donde el ventilador lo controla el firmware
  del fabricante y no se expone vía NVML con este comando.
- Throttle reasons: bitmask `0x400` constante durante entrenamiento
  (vs. `0x1`=GpuIdle en reposo) — no corresponde a ninguna razón
  estándar de throttling térmico/de potencia de NVML (esas llegan hasta
  `0x100`), consistente con ser un flag propio de gestión de energía de
  GPU de laptop y no una señal de alarma real, coherente con que los
  clocks nunca bajaron.

**Comparación 1B (T-72) vs. 3B (T-73)**

| | Llama-3.2-1B | Llama-3.2-3B |
|---|---|---|
| VRAM en reposo (4-bit) | ~1024 MB | ~2139 MB (base) / ~2985 MB (+LoRA) |
| Carga con descarga | 56.4s | 149s |
| Carga desde caché | 5.3s | 13-22s |
| Entrenamiento real | no probado en T-72 | 1.17s/micro-step estable (bs=1×accum=8) |

**Configuración recomendada para el entrenamiento real de T-74**:
`batch_size=1`, `gradient_accumulation_steps=8` (batch efectivo=8), LoRA
sobre las 7 capas lineales, 4-bit NF4 + bf16. Estimado: ~11.7 min/época,
~35 min para 3 épocas sobre los 600 pares — viable dentro del alcance
del proyecto.

**Estado**: viabilidad de Llama-3.2-3B confirmada para entrenamiento real
en esta GPU, con la configuración C. No se avanzó a entrenamiento real ni
se tocó el dataset en ninguna de las pruebas de T-73.

## T-70 — Conversión del dataset al formato de prompt de instrucción (completada 2026-09-19)

Nota de orden: pese al número más bajo, esta tarea se ejecutó después de
T-71/T-72/T-73 — el entorno y la viabilidad del modelo se validaron
primero; T-70 convierte el dataset real (`../dataset/entrenamiento.jsonl`,
582 pares) al formato que ese entrenamiento va a consumir. Script:
[`convertir_dataset.py`](convertir_dataset.py). No se entrenó nada en el
alcance de esta tarea — es puro formateo, el entrenamiento real es T-92.

**Formato de entrada**: cada línea de `entrenamiento.jsonl` es
`{"instruction": "...", "response": "...", "source": "..."}` (`source`
ausente en los pares de categoría (b), ver
[`../dataset/README.md`](../dataset/README.md)). Cada par se convierte a
la estructura de mensajes de chat:

```python
[
    {"role": "system", "content": SYSTEM_PROMPT},
    {"role": "user", "content": par["instruction"]},
    {"role": "assistant", "content": par["response"]},
]
```

y de ahí se aplica `tokenizer.apply_chat_template(mensajes, tokenize=False,
add_generation_prompt=False)` usando el tokenizer real de
`meta-llama/Llama-3.2-3B-Instruct` (el mismo modelo validado en T-73) —
**no** una plantilla de prompt manual, para que el formato coincida
exactamente con el que espera el modelo base.

**Decisión: system prompt fijo, igual en los 582 pares**. Se agregó uno
(constante `SYSTEM_PROMPT` en el script) porque las tres categorías del
dataset (a: política pública general, b: Techo 360 sin fuente, c:
híbrida — ver `../dataset/README.md`) comparten un mismo rol de fondo: el
asistente conversacional de Techo 360. Fijar el mismo system prompt en
los 582 pares ancla ese rol de forma consistente durante el
fine-tuning, en vez de dejar que el modelo infiera el rol solo a partir
del contenido variable de cada pregunta. **Importante para T-92 y para
producción**: hoy `app/main.py` no define ningún system prompt (es un
stub, ver el `TODO` de los endpoints reales) — cuando ese endpoint real
exista, debe usar textualmente el mismo `SYSTEM_PROMPT` de
`convertir_dataset.py`, porque un system prompt distinto en inferencia
invalidaría parte de lo aprendido en este fine-tuning (el modelo
aprendió a responder *bajo ese contexto de sistema específico*, no en
abstracto).

**El campo `source` no se filtra al prompt**: `construir_mensajes()` en
el script solo lee `instruction` y `response` de cada par — `source`
nunca se pasa a `apply_chat_template()`. Se verificó explícitamente que
ningún string exacto de `source` aparece por casualidad dentro del texto
generado salvo cuando ya formaba parte natural de la propia `response`
(9 casos, todos nombres de leyes que la respuesta ya citaba por su
cuenta — ej. "Ley 388 de 1997" — confirmado comparando contra el
`response` original de cada par, no introducido por la conversión).

**Fecha fija en el template**: el chat template oficial de Llama 3.2
inserta una fecha dinámica (`Today Date: ...`, vía `strftime_now`) en el
bloque de system por defecto. Se fijó explícitamente
(`date_string="18 Sep 2026"` al llamar `apply_chat_template`) para que
volver a correr el script sin cambios en el dataset produzca exactamente
el mismo archivo de salida — si no se fija, cada corrida en un día
distinto reescribiría las 582 líneas solo por la fecha, ensuciando diffs
de git sin ningún cambio real de contenido.

**Formato de salida — decisión técnica**: se guardó texto ya formateado
(chat template aplicado), **no** tensores pre-tokenizados
(`input_ids`/`attention_mask` con `datasets.save_to_disk()`). Archivo:
[`../dataset/entrenamiento_formateado/train.jsonl`](../dataset/entrenamiento_formateado/train.jsonl),
582 líneas, un único campo `{"text": "<prompt completo>"}`, cargable
directo con:

```python
from datasets import load_dataset
ds = load_dataset("json", data_files="dataset/entrenamiento_formateado/train.jsonl", split="train")
```

Razón para no pre-tokenizar: `max_length`, padding (fijo vs. dinámico) y
truncamiento son decisiones que le pertenecen al script de entrenamiento
real (T-92), no a esta conversión — pre-tokenizar aquí congelaría esa
decisión de antemano y obligaría a regenerar el artefacto completo ante
cualquier cambio de esos hiperparámetros. Guardar texto plano mantiene el
dataset formateado independiente de esa decisión, sigue siendo 100%
fiel al chat template oficial (la tokenización real en sí es
determinística: mismo texto + mismo tokenizer = mismos `input_ids`,
sin importar cuándo ocurra esa tokenización), y evita versionar un
artefacto binario grande (Arrow) en git que habría que regenerar de
todas formas.

**Verificación**: `datasets.load_dataset()` carga el archivo sin errores
(582 filas, columna única `text`). Longitud en tokens de los 582
ejemplos: mínimo 230, máximo 406, promedio 320.3 — bien por debajo de
cualquier `max_length` razonable para Llama 3.2 (contexto de 128k, y muy
por debajo incluso de un límite conservador de 1024-2048 para
fine-tuning). Se imprimieron 3 ejemplos completos para inspección visual
(el primero del archivo, con fuente; uno sin fuente; y el último del
archivo) — confirmado visualmente que el prompt trae los tokens
especiales correctos (`<|begin_of_text|>`, `<|start_header_id|>system/
user/assistant<|end_header_id|>`, `<|eot_id|>`), el system prompt fijo,
y ninguna mención de `source`.

**Nota sobre encoding en consola**: al imprimir los ejemplos en la
terminal de Windows, las tildes/eñes se ven corruptas (`�`) — es el
mismo problema de code page ya documentado en T-72, no un problema del
texto real. Se verificó por separado, leyendo el archivo con
`encoding="utf-8"` explícito y comparando bytes, que el UTF-8 en disco
es correcto (`¿`, `ó`, etc. presentes tal cual).

**Relación con T-92**: `dataset/entrenamiento_formateado/train.jsonl` es
el artefacto que el script de entrenamiento real de T-92 debe cargar
directamente vía `load_dataset("json", data_files=...)` — T-92 no
necesita releer `entrenamiento.jsonl` ni volver a aplicar el chat
template, solo tokenizar el campo `text` ya formateado (con el
`max_length`/padding/truncamiento y el collator que decida en ese
momento) y entrenar con la configuración ya validada en T-73
(`batch_size=1`, `gradient_accumulation_steps=8`, LoRA en las 7 capas
lineales, 4-bit NF4 + bf16). Si el dataset fuente
(`../dataset/entrenamiento.jsonl`) cambia en una ronda futura, este
script (`convertir_dataset.py`) debe volver a correrse antes de repetir
T-92 para regenerar `train.jsonl`.

**Estado**: conversión completada y verificada (carga con
`datasets.load_dataset`, tokenización correcta según el template oficial,
sin fuga de `source`, sin ejemplos fuera de un rango de tokens
razonable). No se avanzó a entrenamiento real — alcance limitado a la
conversión de formato, según lo definido para T-70.

## T-92 — Fine-tuning LoRA real (completada 2026-09-19)

Entrenamiento real sobre `dataset/entrenamiento_formateado/train.jsonl`
(T-70, 582 pares), con la configuración validada en T-73. Script:
[`entrenar_lora.py`](entrenar_lora.py). No se evaluó contra el holdout
(eso es T-93) — solo se entrenó y se verificó que el loss desciende de
forma razonable.

**Config exacta usada**: `meta-llama/Llama-3.2-3B-Instruct` en 4-bit NF4
(`bnb_4bit_compute_dtype=bfloat16`), LoRA `r=16, lora_alpha=32,
lora_dropout=0.05` sobre las 7 capas lineales (`q_proj, k_proj, v_proj,
o_proj, gate_proj, up_proj, down_proj`), `bias="none"`,
`batch_size=1 × gradient_accumulation_steps=8` (batch efectivo 8),
`learning_rate=2e-4`, `PagedAdamW8bit`, 3 épocas, `max_length=512` (margen
sobre el máximo real de 406 tokens medido en T-70). `lora_dropout=0.05`
es el único valor no fijado explícitamente en T-73 (esa prueba no
mencionaba dropout) — se agregó como regularización estándar dado que
582 ejemplos es un dataset pequeño para 3 épocas completas.

**Learning rate — decisión**: `2e-4`, el extremo superior del rango
1e-4 a 2e-4 sugerido. Con solo 3 épocas y ~219 steps de optimizador
totales (582 ejemplos ÷ batch efectivo 8 × 3 épocas), un LR más
conservador (1e-4) arriesgaba no converger lo suficiente en tan pocos
steps; LoRA (con muchos menos parámetros entrenables que el modelo
completo: 24.3M de 3.24B, 0.75%) tolera bien LRs más altos que un
fine-tuning completo. El resultado (ver más abajo) confirma que fue una
elección razonable: el loss bajó de forma sostenida y monótona por
época, sin señales de divergencia (`grad_norm` se mantuvo entre 0.7 y
2.3 durante toda la corrida, sin picos).

**Enmascarado de prompt (decisión no pedida explícitamente, pero
necesaria para un SFT correcto)**: las labels de las posiciones de
system+user+header del assistant se fijan a `-100` (ignoradas por la
loss de `CrossEntropyLoss`) — el modelo solo aprende a predecir la
respuesta del assistant, no a "memorizar" la pregunta que ya se le dio.
Se implementó ubicando el marcador literal
`<|start_header_id|>assistant<|end_header_id|>\n\n` en el texto ya
formateado por T-70 y tokenizando el prefijo por separado para calcar el
punto de corte exacto en `input_ids`. **Verificado antes de gastar
tiempo de GPU**: `verificar_enmascarado()` decodifica la parte
enmascarada y la no enmascarada de 2 ejemplos y confirma por asserción
que el corte coincide exactamente con el header del assistant (ver
salida real más abajo).

### Problema encontrado durante el smoke test: colapso de rendimiento por presión de VRAM

Antes de comprometer los ~35-40 min de la corrida completa, se corrió
`entrenar_lora.py --smoke-test --smoke-steps 20` (igual que la práctica
de T-72→T-73 de probar antes de escalar). **Resultado del primer
intento**: los primeros ~10 steps corrieron a ~11s/step (igual que la
config C de T-73), pero desde el step ~13 el tiempo por step se disparó
a **100-117 segundos** (~10x más lento), con VRAM reserved estabilizada
en 5018 MB — sin crashear, pero inutilizable para entrenar en la
práctica. Es el mismo patrón que T-73 documentó para su "Configuración A"
descartada: memoria casi agotada (5018 MB reserved + ~850 MB de
uso base del sistema, dejando solo ~250-300 MB libres de los 6144 MB
físicos) fuerza al optimizador paginado (`PagedAdamW8bit`) a hacer swap
activo a RAM del sistema en cada `optimizer.step()`.

**Causa raíz identificada**: el dataset de T-70 (con el chat template
completo de Llama 3.2 + el system prompt fijo) produce secuencias más
largas — promedio 320 tokens, máximo 406 — que las que probó T-73 (pares
crudos instruction/response, sin los tokens especiales ni el bloque de
system del chat template oficial). Esa diferencia de longitud eleva el
pico de memoria de activaciones lo suficiente como para cruzar el umbral
donde el optimizador empieza a paginar. `prepare_model_for_kbit_training()`
ya activa gradient checkpointing por defecto, pero con la variante
`reentrant=True` (menos eficiente en memoria; visible en el warning de
PyTorch en los logs) — no bastaba.

**Fix aplicado**: `gradient_checkpointing=True` explícito en
`TrainingArguments` con `gradient_checkpointing_kwargs={"use_reentrant":
False}`, forzando la variante no-reentrante del checkpointing (más
eficiente en memoria). Se probó también `PYTORCH_CUDA_ALLOC_CONF=
expandable_segments:True`, pero esa opción del allocador de PyTorch **no
está soportada en Windows** (warning explícito en el log) — no tuvo
efecto, se dejó de usar para la corrida real.

**Resultado tras el fix** (segundo smoke test, 20 steps): tiempo por
step estable en 10.5-12.5s durante los 20 steps completos, sin ningún
step por encima de 13s. VRAM reserved plateó en 5018 MB (mismo
high-water mark que antes — es el punto donde PyTorch cachea memoria
para el ejemplo más largo visto hasta ese momento, y no la libera) pero
esta vez **sin** disparar el paginado del optimizador. Confirma que la
variante non-reentrant del checkpointing reduce lo suficiente el pico de
memoria *activa* durante el backward, aunque la memoria *reservada* por
el allocator de PyTorch se mantenga en el mismo nivel.

### Resultado de la corrida real completa (3 épocas, 582 pares)

| Métrica | Valor |
|---|---|
| Tiempo total | **40.30 min** (2417.9s) — vs. ~35 min estimados en T-73 (+~15%, atribuible al gradient checkpointing non-reentrant necesario, ver arriba) |
| Steps de optimizador totales | 219 (72 + 73 + 74 por época, batch efectivo 8) |
| Tiempo por step | min 8.10s, max 13.07s, promedio 11.04s, mediana 11.01s — **0 steps por encima de 30s** en toda la corrida (vs. el colapso a 100+s del primer intento) |
| VRAM reserved | estable entre 4798-5020 MB durante toda la corrida (min-max) |
| VRAM pico | 5020.0 MB reserved / 4731.1 MB allocated (margen ~1.1 GB de los 6144 MB físicos) |
| Temperatura GPU | 61°C sostenido — sin acercarse a throttling térmico (igual que T-73) |
| Loss inicial (step 1) | 2.2472 |
| Loss final (step 219) | 0.7986 |
| Loss promedio por época | Época 1: **1.6093** (n=72) · Época 2: **1.1417** (n=73) · Época 3: **0.8022** (n=74) |
| `grad_norm` | entre 0.7 y 2.3 durante toda la corrida, sin picos ni señales de divergencia |

**¿Bajó el loss de forma razonable?** Sí, de forma monótona y sin
ruido excesivo: la pérdida promedio cae ~29% de la época 1 a la 2, y
otro ~30% de la 2 a la 3, sin meseta ni rebote — con 3 épocas sobre 582
ejemplos no hay señal de haber llegado a un punto de sobreajuste
evidente (el `grad_norm` estable, sin picks, es consistente con esto),
aunque **esto no reemplaza la evaluación real contra el holdout de
T-93** — un loss de entrenamiento bajo no garantiza por sí solo que el
modelo generalice a las 18 preguntas de `holdout.jsonl` que nunca vio.

**Anomalías**: ninguna en la corrida real, una vez aplicado el fix de
checkpointing (ver arriba, encontrada y resuelta en el smoke test antes
de la corrida real). Aparte de eso: el mismo warning cosmético de
`clean_up_tokenization_spaces` ya visto en T-72, y un detalle de
monitoreo (no del entrenamiento en sí) documentado abajo.

**Verificación visual del enmascarado** (previa a la corrida real, sobre
2 ejemplos reales del dataset):

```
Ejemplo 0: 163 tokens enmascarados de 316 totales
  Ultimos 40 chars del prompt enmascarado: '...eader_id|>assistant<|end_header_id|>\n\n'
  Primeros 60 chars de la respuesta (con loss): 'Según el DANE, en 2024 la incidencia de pobreza multidimensi'
```

**Detalle de monitoreo (no afecta el entrenamiento)**: al redirigir la
salida a un archivo (`> log.txt`), Python bufferea `stdout` en bloques
en vez de línea por línea (a diferencia de una terminal interactiva) —
las líneas de `{'loss': ...}` de `Trainer` quedaron en el buffer y no
aparecieron en el log hasta que el proceso terminó y flusheó todo de
una vez, aunque `tqdm` (que escribe a `stderr`, con flush más agresivo)
sí mostraba el progreso en vivo. No afectó el entrenamiento — todo el
historial de loss se recuperó completo de `entrenamiento_log.json` al
terminar. Para una próxima corrida, usar `python -u` evitaría este
retraso de visibilidad.

**Adaptadores guardados**: `training/adapters/techo360-v1/` —
`adapter_model.safetensors` (~97 MB), `adapter_config.json`, tokenizer.
**No se versionan en git** (agregado a `.gitignore`): son un artefacto
binario de ~110 MB generado localmente, igual que el entorno virtual de
T-71 y la caché del modelo base de Hugging Face — se regeneran corriendo
`python training/entrenar_lora.py` (sin `--smoke-test`) sobre el mismo
`dataset/entrenamiento_formateado/train.jsonl`. El log completo de la
corrida (loss por step, VRAM por step, config usada) queda junto a los
adaptadores en `entrenamiento_log.json`.

**Relación con T-70**: consumió directamente el artefacto de T-70
(`dataset/entrenamiento_formateado/train.jsonl`) sin releer
`entrenamiento.jsonl` ni volver a aplicar el chat template — tal como
T-70 anticipó. El `max_length`, el padding (dinámico, sin desperdicio
porque `batch_size=1` no necesita rellenar contra otros ejemplos del
mismo micro-batch) y el collator fueron, como estaba previsto, decisión
de este script.

**Relación con T-93**: los adaptadores de `training/adapters/techo360-v1/`
son el artefacto que T-93 debe cargar (vía `PeftModel.from_pretrained`)
sobre el modelo base para generar respuestas a los 18 pares de
`dataset/holdout.jsonl` y evaluar si el modelo aprendió el contenido
central o solo memorizó el fraseo de entrenamiento. **No se ejecutó
ninguna evaluación contra el holdout en el alcance de T-92** — el loss
de entrenamiento bajando es una señal necesaria pero no suficiente,
T-93 es quien debe confirmar generalización real.

**Estado**: entrenamiento real completado y estable (219/219 steps,
sin anomalías tras el fix), loss desciende de forma monótona y
sustancial (2.2472 → 0.7986), adaptadores guardados y verificados en
disco. No se avanzó a T-93 — alcance limitado al entrenamiento y su
verificación básica, según lo definido para T-92.

## T-93 — Evaluación contra el holdout (completada 2026-09-19)

Evalúa `training/adapters/techo360-v1/` (T-92) contra los 18 pares de
`dataset/holdout.jsonl` — nunca vistos en entrenamiento. Scripts:
[`evaluar_holdout.py`](evaluar_holdout.py) (genera las respuestas),
[`metrica_rouge_l.py`](metrica_rouge_l.py) (métrica automática),
[`rubrica_manual.py`](rubrica_manual.py) (rúbrica 1-5). No se modificó
el modelo ni se reentrenó — solo medición.

**Modelos comparados — solo 2 de los 3 pedidos**: (1) Llama-3.2-3B-Instruct
base sin LoRA, (2) base + adaptadores de T-92, ambos con el mismo system
prompt fijado en T-70 para que la comparación sea justa (se activa/desactiva
el adaptador sobre el mismo objeto `PeftModel` vía `disable_adapter()`,
sin recargar pesos, así que "base" y "fine-tuneado" comparten exactamente
el mismo contexto de generación). **El tercer modelo — una API externa de
referencia (Claude u otro) — no se usó**: se verificó explícitamente que
este entorno no tiene ninguna `ANTHROPIC_API_KEY` ni credencial de otro
proveedor configurada (ni en variables de entorno ni en ningún `.env` del
repo) — por instrucción explícita de la tarea, se omite en vez de
improvisar un sustituto (por ejemplo, no se usó a Claude-el-asistente-que-
ejecuta-esta-tarea de forma informal como "modelo de referencia", porque
eso sería exactamente el tipo de alternativa improvisada que la tarea
pide evitar).

**Generación**: `do_sample=False` (greedy, determinística — reproducible
entre corridas), `max_new_tokens=350` (holgado sobre el promedio real de
~106 palabras/respuesta del holdout).

### Métrica automática: ROUGE-L (F1)

Se eligió ROUGE-L (implementación propia vía LCS, sin dependencias
nuevas) en vez de similitud por embeddings — la tarea ofrecía ambas
opciones y ROUGE-L es la que no requiere instalar nada nuevo en el
entorno de fine-tuning (`sentence-transformers` o `rouge-score` no
están en `requirements-finetuning.txt`). **Limitación reconocida**:
ROUGE-L mide solape léxico en orden común, no corrección semántica —
una respuesta con vocabulario distinto pero igual de correcta puntuaría
bajo, y una respuesta con vocabulario similar pero factualmente
incorrecta puede puntuar más alto de lo que merece (ver el caso del
par 11 más abajo, donde tuvo el mayor delta de ROUGE-L de los 18 pares
pero una rúbrica manual solo moderada). Por eso se complementa con la
rúbrica manual, no se usa sola.

| | Base | Fine-tuneado | Delta |
|---|---|---|---|
| General (18 pares) | 0.1899 | 0.2426 | +0.0527 |
| Con fuente (9 pares) | 0.1991 | 0.2466 | +0.0475 |
| Sin fuente (9 pares) | 0.1807 | 0.2386 | +0.0579 |

**Los 18 pares mejoraron sin excepción** (delta positivo en el 18/18,
mínimo +0.0028 en el par 7, máximo +0.1219 en el par 11) — ninguna
regresión en esta métrica.

### Rúbrica manual (1-5) — auto-evaluación de IA, no rúbrica humana

**Aviso explícito pedido por la tarea**: no hay un evaluador humano en
este flujo. Los puntajes de exactitud factual y relevancia a Techo 360
para cada uno de los 18×2=36 respuestas fueron asignados por Claude (el
asistente que ejecutó T-93), leyendo cada respuesta generada contra la
`response` real del holdout, y en varios casos contra el propio
`dataset/entrenamiento.jsonl` para verificar si un error ya estaba en
los datos de entrenamiento o es una alucinación nueva del modelo (ver
casos concretos más abajo). Es una auto-evaluación de IA — no reemplaza
un juicio experto humano, y se documenta como tal en vez de presentarse
como una rúbrica objetiva. Se aplicó con criterio estricto, tal como
pidió la tarea: una respuesta que "suena bien" pero inventa hechos
puntúa bajo en exactitud aunque esté bien escrita.

| | Base exactitud | Base relevancia | FT exactitud | FT relevancia |
|---|---|---|---|---|
| General (18 pares) | 1.167 | 1.722 | 2.944 | 3.944 |
| Con fuente (9 pares) | 1.222 | 1.889 | 2.778 | 3.556 |
| **Sin fuente (9 pares)** | **1.111** | **1.556** | **3.111** | **4.333** |

**Esto es lo que más importa medir, según la tarea**: en los 9 pares
sin fuente (categoría b, específicos de Techo 360, que el modelo base
no puede saber de antemano), la ganancia es la más grande de las dos
categorías tanto en exactitud (+2.0, de 1.111 a 3.111) como en
relevancia (+2.78, de 1.556 a 4.333) — más grande que la ganancia en
los pares con fuente (exactitud +1.56, relevancia +1.67). Esto es
consistente con la hipótesis de la tarea: el fine-tuning aporta más
donde el conocimiento no puede venir del preentrenamiento general del
modelo base, solo del propio dataset de Techo 360.

El detalle completo de las 18 justificaciones (una por par, explicando
qué evaluó y por qué) está en `eval_holdout_rubrica.json`, campo `nota`
de `por_par`.

### 3 ejemplos donde el fine-tuneado supera claramente al base (categoría b)

**Par 10 — "¿Cómo se estructura la autenticación de usuarios en Techo
360?"**: el modelo **base** responde honestamente *"Lo siento, pero no
tengo información específica..."* y especula de forma genérica
(verificación por correo, 2FA) — no alucina con confianza, pero tampoco
responde. El **fine-tuneado** identifica correctamente el mecanismo real
(JWT, verificación de existencia de usuario, token con correo/rol y
expiración) — sustancialmente correcto y específico, aunque dice
"cookie" en vez de header `Authorization`/almacenamiento en el
navegador (detalle impreciso) y no menciona el hash `bcrypt`.
Exactitud 2→4, relevancia 2→5.

**Par 13 — "¿Qué significa que el Score de Privación sea nulo?"**: el
**base** invierte el concepto por completo — interpreta "nulo" como
"score en cero = sin pobreza", e inventa una lista de lo que implicaría
un score bajo (buena cobertura de agua, baja desigualdad, etc.), un
error conceptual grave. El **fine-tuneado** identifica correctamente que
nulo significa *dato faltante* (no hay fila para ese municipio/año, o
falta una variable), coincidiendo con el mecanismo real documentado en
el holdout. Exactitud 1→4, relevancia 2→5.

**Par 15 — "¿Qué papel cumple el servicio de proyección?"**: el **base**
reemplaza el propósito real por una narrativa genérica de "modelos
estadísticos y análisis espacial" con una lista de indicadores
inventados. El **fine-tuneado** coincide de forma precisa con la
referencia: genera estimaciones estadísticas *solo cuando falta el dato
real*, y distingue explícitamente esas estimaciones de los datos
observados — exactamente el propósito real del servicio. Exactitud
1→5, relevancia 2→5 (el mejor resultado de exactitud de los 18 pares
sin fuente).

### Casos preocupantes — reportados sin suavizar

**No hubo ningún par donde el puntaje de rúbrica del fine-tuneado fuera
numéricamente peor que el del base** (en el peor caso, empatan en 1 —
pares 2 y 3). Pero hay dos patrones honestos que vale la pena señalar,
porque el fine-tuning no los corrigió y en un caso podría decirse que
lo empeoró **en carácter**, aunque no en puntaje:

- **Alucinaciones con formato de cita más convincente (pares 2 y 3,
  cobertura de acueducto/alcantarillado nacional)**: ambos modelos
  inventan cifras que no coinciden con la referencia real (acueducto:
  referencia 86,4%, base 98,4%, fine-tuneado 99,1%; alcantarillado:
  referencia 76,6%, base 93,4%, fine-tuneado 73,1%). El base lo hace con
  un formato obviamente improvisado (listas sueltas de departamentos sin
  fuente clara). El **fine-tuneado inventa con el mismo formato que usa
  para citar hechos reales** ("Según el DANE, ... en 2024, lo que
  representa un incremento de X puntos porcentuales frente a...") —
  aprendió el *estilo* de cita confiable del dataset de entrenamiento
  (que sí tiene cifras reales verificadas, ver `dataset/README.md`) pero
  lo aplica también a datos que no vio y que inventa. Es un riesgo real
  de producción: una alucinación con ese formato es más difícil de
  detectar a simple vista que una lista genérica sin fuente.

- **Nombres de repositorio inventados a pesar de aparecer decenas de
  veces en el entrenamiento (par 9)**: el fine-tuneado responde
  `data`, `models`, `services`, `routes`, `utils` como los cinco
  repositorios de Techo 360 — ninguno es real (los reales son `backend`,
  `frontend`, `chatbot`, `proyeccion`, `infra`). Se verificó
  explícitamente contra `dataset/entrenamiento.jsonl` que los nombres
  reales aparecen mencionados correctamente en al menos 7 pares de
  entrenamiento distintos — esto **no** es un caso de dato de
  entrenamiento ambiguo o faltante, es una alucinación genuina del
  modelo fine-tuneado sobre contenido que sí estaba bien representado en
  sus propios datos de entrenamiento. Los nombres inventados
  (`data/models/services/routes/utils`) parecen una estructura interna
  típica de un proyecto FastAPI genérico, no específica de Techo 360 —
  sugiere que el modelo generaliza hacia un patrón de proyecto Python
  plausible en vez de recordar el hecho específico.

- **Variable extra inexistente en el Score de Privación (pares 5 y
  12)**: el fine-tuneado afirma en 2 de 3 menciones relevantes que el
  Score de Privación tiene **cuatro** variables (agregando "incidencia
  de pobreza multidimensional" o una cuarta genérica), cuando el dataset
  de entrenamiento menciona "tres variables/indicadores" 23 veces y
  nunca "cuatro" (verificado por conteo exacto). No es una alucinación
  aleatoria sin patrón — es un error específico y parcialmente
  recurrente que un despliegue real debería seguir vigilando.

### Estado

T-93 completada: generación de respuestas, métrica automática (ROUGE-L)
y rúbrica manual (auto-evaluación de IA, documentada como tal)
ejecutadas y reportadas para los 18 pares del holdout, separadas por
categoría. El fine-tuning muestra una mejora clara y consistente en
ambas métricas, más grande específicamente en los pares sin fuente
(categoría b) — la señal que la tarea identificó como la más importante
de confirmar. También quedan documentados, sin suavizar, los patrones de
alucinación que persisten tras el fine-tuning (cifras inventadas con
formato de cita convincente, nombres de repositorio incorrectos pese a
estar bien representados en el dataset, y una variable extra inexistente
en el Score de Privación) — relevante para decidir si el modelo está
listo para producción o si necesita otra ronda de datos/entrenamiento
antes de eso. No se modificó el modelo ni se reentrenó en el alcance de
T-93.

## T-94 — Sincronización del system prompt con `app/main.py` (completada 2026-09-19)

Sincroniza el system prompt real del servicio (`techo360-chatbot/app/main.py`)
con el usado para entrenar el modelo (T-70/T-92). Solo sincronización —
no se implementó el endpoint de chat real ni se conectó el adaptador
LoRA, según el alcance definido para T-94.

**System prompt localizado**: `SYSTEM_PROMPT` en
[`convertir_dataset.py`](convertir_dataset.py) (T-70), 399 caracteres.

**Estado previo de `app/main.py` confirmado**: exactamente lo
documentado — un stub con un único endpoint (`GET /health`) y un
comentario `TODO` describiendo el endpoint real (`POST /chatbot/send`)
como pendiente. Sin `SYSTEM_PROMPT`, sin llamada a Ollama, sin RAG, sin
ninguna referencia al adaptador LoRA.

**Cambio realizado**: se agregó la constante `SYSTEM_PROMPT` a
`app/main.py`, verificada programáticamente (no solo por inspección
visual) como idéntica carácter por carácter a la de
`convertir_dataset.py` (399 caracteres, comparación exacta de string en
Python). Se dejó documentada con un comentario que explica que debe
mantenerse sincronizada entre ambos archivos, y que **todavía no la
consume ningún endpoint** — no existe `POST /chatbot/send` aún, así que
no hay dónde inyectarla en una llamada real todavía. Se dejó lista,
en el lugar correcto, para cuando ese endpoint se implemente.

**Diferencia identificada y evaluada — la fecha del chat template**: el
`SYSTEM_PROMPT` en sí **no contiene ninguna fecha ni contenido
dinámico** — es un string estático idéntico en ambos archivos, sin
variación necesaria. La única pieza relacionada con fechas es distinta:
el chat template oficial de Llama 3.2 inserta por separado un bloque
`Cutting Knowledge Date: December 2023 / Today Date: {fecha}` (ver T-70)
mediante el parámetro `date_string` de `apply_chat_template()` — **no**
es parte de la variable `SYSTEM_PROMPT`. T-70 fijó esa fecha
(`"18 Sep 2026"`) únicamente para que regenerar el dataset de
entrenamiento sin cambios produjera el mismo archivo byte a byte (evitar
diffs de git por fecha). **En el endpoint real, esa fecha debe ser la
fecha real del momento de la llamada (dinámica), no la fecha fija del
dataset de entrenamiento** — se documentó esto directamente en el
comentario del `TODO` en `app/main.py`.

**¿Es seguro usar una fecha distinta a la del entrenamiento?** Sí. Se
evaluó explícitamente: ninguna de las 582 respuestas de entrenamiento
depende del valor literal de esa fecha — es texto de relleno (boilerplate)
que el propio chat template de Meta inserta automáticamente, no contenido
sustantivo del par instruction/response. El modelo no aprendió ningún
hecho condicionado a "18 Sep 2026"; usar la fecha real en inferencia no
genera ninguna inconsistencia relevante con lo aprendido en el
fine-tuning. Distinto sería si alguna respuesta de entrenamiento hiciera
referencia relativa a "hoy" o citara esa fecha como dato — no es el caso
en este dataset.

**Nota adicional, fuera del alcance de T-94 pero relevante para cuando el
endpoint exista**: si la inferencia real termina corriendo sobre Ollama
(ver hallazgo de arquitectura más abajo) en vez de
`tokenizer.apply_chat_template()` directamente, el mecanismo de inserción
de fecha podría ser distinto (o inexistente) según cómo se defina la
plantilla en el `Modelfile` de Ollama — es una decisión que le
corresponde a quien implemente esa integración, no a esta tarea.

### Qué falta para integrar el adaptador LoRA de T-92 a `app/main.py` — reportado, no implementado

Se investigó la arquitectura de despliegue real (`techo360-infra/docker-compose.yml`,
`techo360-chatbot/requirements.txt`, `techo360-chatbot/Dockerfile`) para
responder esto con precisión, no en abstracto. Hallazgo central: **la
integración real es más grande de lo que "conectar el adaptador" sugiere,
porque el entrenamiento (T-92) y el despliegue de producción usan stacks
técnicos incompatibles entre sí**:

- **T-92 entrena y evalúa** con `transformers` + `peft` +
  `bitsandbytes`, el adaptador LoRA en formato PEFT
  (`adapter_model.safetensors`), cargado en 4-bit sobre GPU
  (RTX 3050 local).
- **Producción real** (`techo360-infra/docker-compose.yml`) corre el LLM
  en un contenedor **Ollama**, en un **VPS sin GPU** (3072 MB de RAM
  asignados al contenedor de Ollama, 1 CPU) — el servicio `chatbot`
  (FastAPI) le habla por HTTP (`OLLAMA_URL`), nunca carga el modelo en su
  propio proceso. `requirements.txt` del chatbot confirma esto: no tiene
  `torch`, `transformers`, `peft` ni `bitsandbytes` — solo `httpx`,
  `sentence-transformers` (para embeddings/RAG), `pgvector`, `sqlalchemy`,
  `pika`.
- Ollama sirve modelos en formato **GGUF** cuantizado, no
  safetensors + bitsandbytes. El adaptador de T-92 **no es compatible
  directamente** con Ollama tal cual está guardado.

**Pasos concretos que faltan** (ninguno implementado, solo reportado
según lo pedido):

1. **Fusionar el adaptador LoRA con el modelo base** (`PeftModel.merge_and_unload()`)
   para obtener un modelo Llama-3.2-3B-Instruct completo con los pesos
   ajustados — Ollama no soporta cargar un adaptador PEFT crudo por
   separado del modelo base de esta forma.
2. **Convertir el modelo fusionado a GGUF** (vía las herramientas de
   `llama.cpp`, ej. `convert_hf_to_gguf.py`) y **cuantizarlo** a un
   tamaño viable para CPU + 3072 MB de RAM (el `docker-compose.yml` ya
   advierte explícitamente sobre este límite y recomienda modelos
   pequeños de 1-3B — un Q4/Q5 del 3B debería entrar, pero no se ha
   medido).
3. **Crear un `Modelfile` de Ollama** para el modelo convertido,
   definiendo cómo se inyecta el system prompt (vía directiva `SYSTEM`
   del Modelfile, o pasando `"system"` en cada llamada a la API de chat
   de Ollama) — hoy no existe ningún `Modelfile` en ninguno de los
   repos, se verificó explícitamente.
4. **Registrar el modelo en Ollama** (`ollama create techo360-chatbot -f Modelfile`)
   y actualizar la referencia al modelo — hoy `docker-compose.yml` y
   `techo360-infra/README.md` solo mencionan, a modo de ejemplo/placeholder
   en comentarios y en el script `setup-server.sh`, hacer
   `ollama pull llama3.2:3b` (el modelo **base sin ningún fine-tuning**);
   no hay ninguna variable de entorno `OLLAMA_MODEL` ni configuración que
   apunte a un modelo propio.
5. **Implementar el endpoint real** `POST /chatbot/send` en `app/main.py`
   (hoy no existe ningún endpoint de chat, solo `/health`) — debe
   construir el mensaje con `SYSTEM_PROMPT` (ya sincronizado en esta
   tarea) + la pregunta del usuario, llamar a Ollama vía `httpx` con el
   modelo fine-tuneado (una vez creado en el paso 4), y manejar la
   respuesta.
6. **RAG contra pgvector** (mencionado en el propio `TODO` del código y
   en `requirements.txt` vía `sentence-transformers`) no está
   relacionado con el LoRA en sí, pero es parte del mismo endpoint
   pendiente — no se investigó en profundidad en el alcance de T-94 por
   no ser parte de la pregunta específica sobre el adaptador.

Ninguno de estos 6 pasos se implementó en T-94 — se reportan tal como
pidió la tarea, para que quede claro que "sincronizar el system prompt"
es un paso pequeño y ya completado dentro de una integración bastante
más grande que sigue pendiente en su totalidad.

### Verificación de que no se rompió nada

Se importó `app/main.py` y se llamó a `health()` directamente,
confirmando la respuesta exacta sin cambios
(`{"status": "ok", "service": "chatbot", "version": "ci-cd-test-1"}`).
Adicionalmente se levantó el servicio real con `uvicorn` y se probó por
HTTP: `GET /health` respondió igual, y `GET /docs` (Swagger, autogenerado
por FastAPI) respondió `200` sin errores — agregar la constante
`SYSTEM_PROMPT` no rompió la carga del módulo ni el único endpoint
existente.

**Estado**: system prompt sincronizado y verificado carácter por
carácter entre `training/convertir_dataset.py` y `app/main.py`. Diferencia
de fecha del chat template identificada, documentada y evaluada como
segura. Gap de integración real (LoRA → GGUF → Ollama → endpoint)
investigado a fondo y reportado en detalle, sin implementarse — según lo
definido para T-94. No se avanzó a T-95.

## T-95 (primer frente) — Ampliación dirigida del dataset para mitigar alucinaciones de T-93 (completada 2026-09-19)

Primer frente de T-95: ataca los dos patrones de alucinación
reproducibles que encontró T-93 agregando pares de entrenamiento
dirigidos específicamente a cada uno, en vez de generar contenido nuevo
sin foco. **Solo ampliación de dataset — no se reconvirtió (T-70) ni se
reentrenó (T-92) con el dataset ampliado**, según el alcance definido
para este frente.

**28 pares nuevos agregados a `dataset/entrenamiento.jsonl`** (582 → 610):

- **18 pares (a/c), cobertura de acueducto/alcantarillado por
  municipio** — contra el patrón de "cifras inventadas con cita
  convincente" (pares 2 y 3 del holdout en T-93). Fuente primaria: el
  *Informe Nacional de Coberturas AAA 2020* de la SSPD, leído en PDF vía
  `pdftotext` (el fetch automático de la URL no devolvía texto legible).
  Verificado contra una segunda fuente independiente (artículo de
  Semana citando cifras de la misma Superintendencia). Ninguna cifra
  municipal se inventó — todas son las que el propio informe de la SSPD
  destaca como casos atípicos o extremos (San Andrés, Istmina, La Tola,
  Bolívar, Norte de Santander, Meta, entre otros).
- **10 pares (b), nombres reales de los cinco repositorios** — contra
  el patrón de "repos inventados pese a estar bien representados en el
  dataset" (par 9 del holdout en T-93). Se revisaron los 8 pares
  existentes sobre repositorios (ninguno pide una enumeración directa
  de los nombres, todos son del tipo "por qué"/"qué ventaja") y se
  agregaron 10 formulaciones distintas que sí refuerzan el nombre
  exacto de cada uno (`techo360-backend`, `techo360-frontend`,
  `techo360-chatbot`, `techo360-proyeccion`, `techo360-infra`).

Detalle completo de los 28 pares, la verificación de fuentes aplicada, y
la verificación de no-duplicados (0 coincidencias exactas, internas, o
por similitud >0,75 contra los 582+18 pares existentes) en
`dataset/README.md`, sección "Cuarta ronda — mitigación de
alucinaciones detectadas en T-93".

**Composición resultante**: 610 pares totales, 379 con fuente (62,1%),
231 sin fuente (37,9%); (a) 263, (b) 231, (c) 116.

**Qué falta para saber si esto realmente mitigó las alucinaciones**:
agregar los pares no es la mitigación en sí, solo el insumo. Falta (1)
decidir si se repite T-70 sobre los 610 pares para regenerar
`dataset/entrenamiento_formateado/train.jsonl`, (2) decidir si se repite
T-92 (reentrenamiento real, misma configuración validada) sobre el
dataset ampliado, y (3) repetir T-93 contra el mismo holdout de 18 pares
para confirmar si los dos patrones de alucinación específicos
efectivamente desaparecieron o se redujeron, no solo asumir que
agregar pares los corrige. Ninguno de estos tres pasos se ejecutó en
este frente — se reportan los 28 pares para revisión antes de decidir
si se avanza a ellos.

**Estado**: ampliación completada, verificada (sin duplicados) y
documentada. Pendiente de decisión externa: repetir T-70 y T-92 con el
dataset ampliado, y solo después repetir T-93 para confirmar el efecto
real de esta ronda.

## T-95 (segundo frente) — Adaptador de T-92 a producción vía Ollama (completada 2026-09-19)

Implementa los 6 pasos de integración que T-94 dejó reportados sin
implementar: lleva el adaptador LoRA de T-92 (entrenado sobre el
dataset **sin** los 28 pares del primer frente — ver nota al final) a
un modelo servible por Ollama, y conecta el endpoint real. Probado
**solo localmente** (máquina de desarrollo, CPU) — no se desplegó al
VPS, según lo pedido.

### Paso 1 — Fusión LoRA + base

Script: [`fusionar_lora.py`](fusionar_lora.py). Carga el modelo base en
`bfloat16` (no en 4-bit — fusionar sobre una base ya cuantizada
degradaría precisión antes de la cuantización GGUF real) en CPU, aplica
`PeftModel.merge_and_unload()`, y guarda un modelo standalone.

- **Salida**: `training/modelo_fusionado/techo360-v1-merged/`, 6,1 GB en
  safetensors bf16. No se versiona (agregado a `.gitignore`, mismo
  criterio que los adaptadores).

**Problema encontrado y resuelto**: `tokenizer.save_pretrained()` con
transformers 5.17.0 (el que usa el entorno de fine-tuning) escribe
`"tokenizer_class": "TokenizersBackend"` en `tokenizer_config.json` —
una clase nueva de transformers 5.x que no existe en transformers
4.57.6 (la versión que exige el conversor de llama.cpp, paso 2). Esto
rompía la conversión con `ValueError: Tokenizer class TokenizersBackend
does not exist`. Solución: el vocabulario no cambió en ningún momento
del fine-tuning, así que se reemplazaron `tokenizer_config.json`,
`special_tokens_map.json` y `tokenizer.json` del modelo fusionado por
los originales de `meta-llama/Llama-3.2-3B-Instruct` (ya en caché
local), que usan el `tokenizer_class` clásico (`PreTrainedTokenizerFast`)
compatible con ambas versiones de transformers.

### Paso 2 — Conversión a GGUF

Se clonó `ggml-org/llama.cpp` (shallow clone, fuera de cualquier repo
del proyecto) para usar `convert_hf_to_gguf.py`. Se creó un entorno
virtual **separado** del de fine-tuning
(`C:\Users\Eridanus_2\entornos\gguf-tools`), con las versiones exactas
que ese script requiere (`transformers==4.57.6`, `numpy~=2.2.6`,
`gguf`, `sentencepiece`, `torch` CPU) — deliberadamente aislado para no
arriesgar la reproducibilidad del entorno de T-71/T-92 (que usa
transformers 5.17.0) tocándolo con una versión distinta.

```
python convert_hf_to_gguf.py <modelo_fusionado> --outfile techo360-v1-f16.gguf --outtype f16
```

- **Salida**: `training/modelo_gguf/techo360-v1-f16.gguf`, 6,43 GB
  (F16, sin cuantizar todavía). No se versiona.

### Paso 3 — Cuantización Q4_K_M

Se usó el binario `llama-quantize` de un release precompilado de
llama.cpp para Windows x64 CPU (`b11056`, descargado directo del
release de GitHub — no se compiló desde fuente, para ahorrar tiempo y
evitar depender de un toolchain de compilación C++ instalado).

**Por qué Q4_K_M**: es el nivel de cuantización que la propia
documentación de llama.cpp recomienda como el mejor punto de partida
"calidad razonable / tamaño razonable" para modelos pequeños (1-8B) —
usa 4 bits para la mayoría de las capas pero preserva mayor precisión
(6 bits, `q6_K`) en las capas más sensibles a la pérdida de calidad
(`attn.v` y `ffn_down` de cada bloque, visible en el log de
cuantización). Es también el nivel de referencia que ya usaban T-72/T-73
para las pruebas de carga en GPU (aunque ahí en 4-bit vía
`bitsandbytes`, no GGUF) — mantener el mismo nivel de agresividad de
cuantización entre ambos frentes de prueba permite comparar resultados
sin agregar una segunda variable.

```
llama-quantize.exe techo360-v1-f16.gguf techo360-v1-Q4_K_M.gguf Q4_K_M
```

| | Tamaño | Bits por peso |
|---|---|---|
| Original bf16 fusionado | 6,13 GB (6128 MiB) | 16.00 BPW |
| **Q4_K_M cuantizado** | **1,92 GB (1918 MiB)** | **5.01 BPW** |

Reducción de ~3,2x sobre el modelo fusionado bf16. No se probó ningún
nivel de cuantización más agresivo (Q4_K_S, Q3_K_M) en el alcance de
esta tarea — si 1,92 GB resulta demasiado ajustado en la práctica
contra el límite real de 3072 MB del contenedor de Ollama en el VPS
(ver nota de RAM más abajo), sería el siguiente paso a probar antes de
desplegar.

### Paso 4 — Modelfile de Ollama

[`training/ollama/Modelfile`](ollama/Modelfile) — sí se versiona (es
texto, documenta la configuración real, a diferencia de los binarios de
los pasos 1-3).

- **System prompt**: verificado programáticamente como idéntico
  carácter por carácter (399 caracteres) entre `training/ollama/Modelfile`,
  `training/convertir_dataset.py` (T-70) y `app/main.py` (T-94) — los
  tres deben mantenerse sincronizados.
- **Parámetros de inferencia, conservadores para un chatbot informativo
  (no creativo)**:

| Parámetro | Valor | Razón |
|---|---|---|
| `temperature` | 0.3 | Respuestas deterministas, menos propensas a divagar — relevante dado los patrones de alucinación que T-93 ya documentó en este mismo modelo |
| `top_p` | 0.9 | Filtra la cola de tokens de baja probabilidad sin ser tan restrictivo como para volver el texto robótico |
| `repeat_penalty` | 1.15 | Por encima del default de Ollama (1.1) — mitiga los bucles de repetición que a veces aparecen justamente a temperaturas bajas |
| `num_ctx` | 2048 | Las respuestas de entrenamiento (T-70) miden como máximo 406 tokens; un contexto más grande solo consumiría RAM de KV cache sin beneficio real para este caso de uso de un solo turno, y el VPS de producción tiene apenas 3072 MB asignados a todo el contenedor de Ollama |

### Paso 5 — Registro y prueba local en Ollama

```
ollama create techo360-chatbot -f training/ollama/Modelfile
```

Resultado: `success`, modelo registrado (`ollama list` → `techo360-chatbot:latest`, 2,0 GB).

**Prueba de inferencia** (`POST http://localhost:11434/api/chat`, vía `curl` directo a Ollama, sin pasar todavía por `app/main.py`):

| | Primera llamada (carga en frío) | Segunda llamada (modelo ya cargado) |
|---|---|---|
| `total_duration` | 78,07 s | 4,97 s |
| `load_duration` | 44,02 s | 0,003 s |
| `prompt_eval_duration` | 29,41 s (160 tokens) | 0,18 s (159 tokens, 139 en caché) |
| `eval_duration` (generación) | 4,59 s (228 tokens) | 4,71 s (236 tokens) |

La generación en sí (una vez cargado el modelo) toma ~4,6-4,7s por
respuesta completa en CPU — la latencia real que importa para un
chatbot ya "tibio" es la de la segunda fila, ~5s totales. La carga en
frío (~44s) solo ocurre una vez por arranque/reinicio del contenedor de
Ollama, no por cada pregunta.

**Verificación de que la cuantización no degradó el comportamiento
aprendido más allá de lo esperado**: se repitió una de las preguntas
del holdout que el modelo de T-92/T-93 ya respondía bien
("¿Qué significa que el Score de Privación de Techo 360 sea nulo?").
La respuesta del modelo GGUF cuantizado sigue capturando correctamente
el concepto central (nulo = dato faltante, no "score en cero = sin
pobreza", el error que sí comete el modelo base) — consistente con la
evaluación de T-93. También reprodujo, sin sorpresas, el mismo patrón
de alucinación ya documentado en T-93 sobre "cuatro variables" del
Score de Privación (debería ser tres) al preguntarle directamente por
el cálculo — **es el mismo modelo de T-92**, servido por una vía
distinta, así que hereda exactamente los mismos aciertos y los mismos
errores conocidos. La cuantización a Q4_K_M no parece haber introducido
degradación nueva y perceptible en una prueba cualitativa puntual (no
se corrió la batería completa de T-93 contra este modelo GGUF — sería
necesario para una comparación rigurosa, no se hizo en el alcance de
esta tarea).

### Paso 6 — Endpoint `POST /chatbot/send`

Implementado en `app/main.py`. Recibe `{"message": "..."}`, arma la
solicitud a Ollama con el `SYSTEM_PROMPT` sincronizado (pasado
explícitamente en cada llamada, no solo confiando en el `SYSTEM` ya
horneado en el Modelfile — así un cambio futuro de modelo/tag en Ollama
sin el Modelfile correcto no serviría silenciosamente con un system
prompt distinto al entrenado) y el mensaje del usuario, llama a
`POST {OLLAMA_URL}/api/chat` vía `httpx` async, y devuelve
`{"response": "..."}`. `OLLAMA_URL` y `OLLAMA_MODEL` se leen de
variables de entorno (`OLLAMA_URL` ya está definida en
`docker-compose.yml` de producción; el default `localhost:11434` es
solo para pruebas fuera de Docker, como se hizo aquí).

**Deliberadamente omitido, según el alcance pedido para esta tarea**:

- **RAG contra pgvector**: el mensaje del usuario se envía tal cual a
  Ollama, sin recuperar contexto adicional de la base vectorial. El
  `TODO` original del código lo mencionaba, pero no se pidió
  implementarlo en esta tarea.
- **Historial de conversación multi-turno**: cada llamada a
  `POST /chatbot/send` es independiente — no se guarda ni se envía el
  historial de mensajes previos del usuario.

**Verificación end-to-end**: se levantó el servicio real con
`uvicorn app.main:app`, y se probó `POST /chatbot/send` con un mensaje
real contra el Ollama local (mismo que en el paso 5) — `HTTP 200` en
~6s, respuesta coherente en español. `GET /health` se verificó sin
cambios (ya lo tenía T-94).

### Consideración de RAM para el VPS (no verificada in situ — el VPS no se tocó)

El contenedor de Ollama en producción tiene 3072 MB asignados
(`techo360-infra/docker-compose.yml`). El modelo cuantizado pesa 1,92 GB;
sumando una estimación de KV cache para `num_ctx=2048` (del orden de
~200-250 MB para Llama 3.2 3B con GQA) y el overhead propio del runtime
de llama.cpp/Ollama, el uso total estimado ronda 2,3-2,6 GB —
dejaría un margen de varios cientos de MB, pero **esto es una
estimación, no una medición real en el VPS** (que además es CPU-only,
distinto a la máquina de desarrollo donde se hizo esta prueba, que
también corrió en CPU pero con más RAM disponible en general). Antes
de desplegar, valdría la pena medir el uso real de memoria del
contenedor de Ollama con este modelo cargado directamente en el VPS o
en un entorno que replique sus 3072 MB de límite.

### Qué falta para el despliegue real (no hecho, fuera del alcance de esta tarea)

1. Copiar `techo360-v1-Q4_K_M.gguf` y el `Modelfile` al VPS (o a un
   volumen que el contenedor de Ollama pueda leer) y correr
   `ollama create` ahí — hoy el modelo solo existe en el Ollama local
   de la máquina de desarrollo.
2. Definir `OLLAMA_MODEL=techo360-chatbot` en el `.env` de
   `techo360-infra` (hoy `docker-compose.yml` no fija ningún modelo
   propio, solo menciona `llama3.2:3b` base como ejemplo en comentarios
   y en `setup-server.sh`).
3. Medir el uso real de RAM en el VPS (ver nota arriba).
4. Decidir e implementar el RAG contra pgvector, si se quiere para esta
   primera versión del endpoint o para una siguiente iteración.

### Relación con el primer frente de T-95

**Importante**: el adaptador LoRA que se fusionó, convirtió y sirvió en
este segundo frente es el de **T-92**, entrenado *antes* de que el
primer frente de T-95 agregara los 28 pares nuevos a
`dataset/entrenamiento.jsonl`. Es decir, el modelo que ahora corre en
Ollama localmente **todavía tiene los mismos dos patrones de
alucinación que T-93 documentó** (cifras de cobertura inventadas con
cita convincente, y nombres de repositorio incorrectos) — de hecho, se
reprodujeron ambos en las pruebas de este segundo frente (ver paso 5 y
6). Este segundo frente resuelve la *tubería de despliegue*
(fusión → GGUF → cuantización → Ollama → endpoint), no el contenido del
modelo. Si se decide repetir T-70/T-92 con el dataset ampliado (610
pares), los pasos 1-5 de este documento tendrían que repetirse sobre el
adaptador nuevo para llevar la versión mitigada a Ollama.

**Estado**: los 6 pasos de integración completados y verificados
localmente (fusión, GGUF, cuantización Q4_K_M a 1,92 GB, Modelfile con
system prompt sincronizado, registro en Ollama, endpoint
`POST /chatbot/send` funcionando end-to-end). No se desplegó al VPS —
alcance limitado a la verificación local, según lo definido para este
frente. No se tocó el dataset ni se reentrenó (eso es el primer frente
de T-95, ya completado por separado).

## Ciclo completo con el dataset ampliado: T-70 → T-92 → T-93 → GGUF/Ollama (v2, completado 2026-09-19)

Repite el ciclo completo sobre los 610 pares (582 + 28 del primer
frente de T-95) para medir si la ampliación dirigida realmente mitigó
los dos patrones de alucinación de T-93. **Resultado adelantado: no,
no limpiamente** — ver el análisis honesto más abajo. v1 (el adaptador
de T-92 original) y v2 (este reentrenamiento) conviven en
`training/adapters/`, en Ollama (`techo360-chatbot:v1` /
`techo360-chatbot:v2`), y en los scripts de evaluación, para no perder
la comparación.

### T-70 repetido

`python training/convertir_dataset.py` sobre los 610 pares (antes 582).
Misma `SYSTEM_PROMPT`, misma `FECHA_FIJA_TEMPLATE`. Resultado: 610
líneas en `train.jsonl`, longitud en tokens min 222 / max 406 / promedio
319.0 (prácticamente igual al de 582 pares). Verificado de nuevo, igual
que la primera vez: 0 fugas del campo `source` al texto de entrenamiento
(chequeo exacto del string y chequeo de que cualquier coincidencia
proviene de la propia `response`, no del metadato).

### T-92 repetido (adaptador v2)

Mismo script (`entrenar_lora.py`, ahora con flag `--version` para no
pisar `techo360-v1`), misma config exacta: 4-bit NF4/bf16, LoRA
r=16/alpha=32 sobre las 7 capas, batch=1×accum=8,
`gradient_checkpointing` no-reentrant, enmascarado de prompt, 3 épocas,
LR=2e-4.

| | v1 (582 pares) | v2 (610 pares) |
|---|---|---|
| Tiempo total | 40,30 min | 43,68 min |
| Steps totales | 219 | 231 |
| Loss inicial | 2,2472 | 2,0979 |
| Loss final (último step) | 0,7986 | 0,7073 |
| Loss promedio por época | 1,609 → 1,142 → 0,802 | 1,605 → 1,143 → 0,803 |
| VRAM pico reserved/allocated | 5020,0 / 4731,1 MB | 5030,0 / 4731,6 MB |
| Tiempo por step (min/max/mediana) | — | 2,71s / 82,23s / 10,85s |

**La config de memoria se mantuvo estable** — VRAM prácticamente
idéntica a v1 en todo momento (4798-5030 MB durante toda la corrida,
mismo rango que v1). La curva de loss por época es, dentro de lo
esperable, casi idéntica a la de v1 (582 y 610 pares comparten el 95%
del contenido) — señal de que el entrenamiento en sí fue sano y
reproducible.

**Anomalía puntual detectada y reportada sin suavizar**: un solo step
(step 198 de 231) tardó 82,23s frente a un promedio de 11,34s — un pico
aislado, ~7x el tiempo normal. Se investigó explícitamente si era el
mismo problema de saturación de VRAM de la primera corrida de T-92: **no
lo es** — la VRAM reserved se mantuvo exactamente en 5030 MB en los
steps inmediatamente anteriores, durante, y posteriores al pico, sin
ninguna señal de crecimiento de memoria que hubiera anticipado el
patrón de paginación ya conocido. Es más consistente con una
interrupción transitoria a nivel de sistema operativo (otro proceso,
I/O de disco, o similar) que con un problema de la configuración de
entrenamiento — no se repitió, y el resto de los 231 steps se mantuvo
en el rango normal (2,71-13s aprox).

### T-93 repetido — comparación honesta base / v1 / v2

Script: [`evaluar_holdout_v2.py`](evaluar_holdout_v2.py) — carga el
modelo base **una sola vez** y adjunta v1 y v2 como adaptadores PEFT
nombrados (`set_adapter("v1")` / `set_adapter("v2")` /
`disable_adapter()`), evitando cargar el modelo de 3B tres veces. Mismo
holdout de 18 pares, sin tocar. Métricas:
[`metrica_rouge_l_v2.py`](metrica_rouge_l_v2.py) (ROUGE-L, misma
implementación que la corrida anterior) y
[`rubrica_manual_v2.py`](rubrica_manual_v2.py) (auto-evaluación de IA,
mismos criterios estrictos — ver el aviso completo en
`rubrica_manual.py`, aplica igual aquí).

**ROUGE-L (F1)**:

| | Base | v1 | v2 | v2 vs v1 |
|---|---|---|---|---|
| General | 0,1899 | 0,2426 | **0,2348** | **-0,0078** |
| Con fuente | 0,1991 | 0,2466 | **0,2427** | **-0,0039** |
| Sin fuente | 0,1807 | 0,2386 | **0,2268** | **-0,0118** |

10 de 18 pares empeoraron de v1 a v2 en ROUGE-L (delta < -0,01), solo 5
mejoraron por encima de ese umbral.

**Rúbrica manual (1-5, auto-evaluación de IA)**:

| | Base ex. | v1 ex. | v2 ex. | Base rel. | v1 rel. | v2 rel. |
|---|---|---|---|---|---|---|
| General | 1,167 | 2,944 | **2,389** | 1,722 | 3,944 | **3,389** |
| Con fuente | 1,222 | 2,778 | **2,222** | 1,889 | 3,556 | **3,222** |
| **Sin fuente** | 1,111 | **3,111** | **2,556** | 1,556 | **4,333** | **3,556** |

De los 18 pares, en exactitud: **1 mejoró, 9 empeoraron, 8 quedaron
igual** entre v1 y v2 (verificado programáticamente, no a ojo).

**Esto es exactamente lo que la tarea pidió reportar sin suavizar: v2
retrocede respecto a v1 en ambas métricas, en ambas categorías, y
específicamente en la categoría sin_fuente — la que más importaba
mejorar.** No es un empate ni un matiz — es un retroceso neto y
consistente entre dos métricas independientes (una automática, una de
juicio).

**¿Mejoraron los dos patrones específicos que se atacaron?**

- **Nombres de los 5 repositorios (par 9)** — **sí mejoró, parcialmente**.
  v1 no acertaba ningún nombre real (`data/models/services/routes/utils`).
  v2 acierta 4 de 5 (`backend`, `frontend`, `chatbot`, `proyeccion`) y
  solo inventa el quinto (`chatbot-visualización` en la corrida vía
  transformers; `techo360-estaciones` en una corrida posterior vía
  Ollama con temperatura 0,3 — ver más abajo). Es la única mejora clara
  y directamente atribuible a los 10 pares nuevos sobre este tema.
  Exactitud 1→3, relevancia 3→4.

- **Cifras de cobertura de acueducto/alcantarillado con cita falsa
  (pares 2 y 3)** — **NO mejoró**. v2 sigue citando cifras nacionales
  inventadas con el mismo formato confiado ("Según el DANE...") que v1:
  acueducto 99,1% (real: 86,4%), alcantarillado 95,1% (real: 76,6%) —
  números distintos a los de v1, igual de incorrectos. Los 18 pares
  nuevos de cobertura sí acertaron a que v2 use fechas más plausibles
  (2020, el año del informe SSPD usado como fuente) en vez de años
  arbitrarios como 2024/2025 que usaba v1, pero **no corrigieron la
  cifra en sí** — el patrón de alucinación con cita convincente persiste
  intacto.

**Regresiones nuevas, no presentes en v1, reportadas sin suavizar**:

- **Par 4 ("¿Qué es Techo 360?")**: v1 daba una respuesta muy precisa
  (las 3 variables reales del Score). v2 la reemplaza por una versión
  menos precisa que además inventa alcance falso ("cobertura de
  internet", "acceso a servicios de salud") que Techo 360 no mide.
  Exactitud 4→2.
- **Par 6 (VIS)**: v2 introduce una cita legal específica y **errónea**
  (Ley 142 de 1994, la ley de servicios públicos) donde v1 no citaba
  ninguna ley incorrecta. Ley 142/1994 es exactamente la que aparece en
  los pares nuevos de "soluciones alternativas de acueducto" del primer
  frente de T-95 — es plausible que sea contaminación cruzada entre
  temas distintos introducidos en la misma ronda de datos.
- **Par 7 (15 indicadores del IPM)**: v1 acertaba los 5 nombres reales
  de las dimensiones aunque fallaba los indicadores exactos. v2 inventa
  nombres de dimensión completamente distintos a los reales y se
  contradice a sí mismo sobre cuántas dimensiones hay.
- **Par 10 (autenticación)**: v1 identificaba correctamente JWT como el
  mecanismo real. v2 lo reemplaza por un esquema inventado (HMAC SHA256,
  verificación de IP) que no aparece en ningún dato de entrenamiento.
- **Par 11 (7 variables del panel)**: v1 acertaba 2 de 7 nombres reales.
  v2 inventa una estructura de "3 bloques de 3" (9 ítems, no 7) sin
  ninguna coincidencia con las 7 variables reales — peor que v1.
- **Par 16 (Score vs. IPM oficial)**: v2 le atribuye a Techo 360 un
  "umbral de corte del 33,3%" que la propia referencia del holdout dice
  explícitamente que Techo 360 **no** tiene (ese umbral es exclusivo del
  IPM/Alkire-Foster) — v1 no cometía este error.

**Interpretación**: la hipótesis más plausible es interferencia entre
tareas dentro de un adaptador LoRA de capacidad limitada (r=16): los 28
pares nuevos son solo ~4,6% del dataset, pero 3 épocas completas de
gradiente sobre el conjunto ampliado parecen haber reajustado pesos
compartidos de forma que mejoraron el tema reforzado explícitamente
(nombres de repos) a costa de perturbar negativamente respuestas
cercanas pero distintas que v1 ya tenía bien aprendidas. No se investigó
más a fondo (comparar con menos épocas, mayor rank de LoRA, o agregar
los pares nuevos con un peso de muestreo distinto) — quedaría como
trabajo futuro si se decide seguir esta línea.

**Nota metodológica**: ROUGE-L (léxico) y la rúbrica (semántica) están
de acuerdo en la dirección del resultado (ambas bajan de v1 a v2), lo
cual da más confianza en que el retroceso es real y no un artefacto de
una sola métrica — a diferencia del caso puntual del par 11 en la
corrida anterior, donde discreparon.

### GGUF/Ollama repetido con v2 (pasos 1-5)

Mismo procedimiento que la sección anterior, sin cambios metodológicos
(el objetivo era verificar que la tubería de despliegue funciona igual
de bien con cualquier adaptador, no solo con v1):

| | v1 | v2 |
|---|---|---|
| Modelo fusionado (bf16) | 6,13 GB | 6,13 GB (idéntico, misma arquitectura) |
| GGUF F16 | 6,43 GB | 6,43 GB |
| GGUF Q4_K_M | 1,92 GB (2 019 377 216 bytes) | **1,92 GB (2 019 377 216 bytes, byte a byte idéntico en tamaño)** |
| Modelfile | `training/ollama/Modelfile` | `training/ollama/Modelfile.v2` (mismo system prompt y parámetros, solo cambia `FROM`) |
| Tag en Ollama | `techo360-chatbot:v1` (retagueado desde `:latest`, que se dejó igual) | `techo360-chatbot:v2` |

Registro (`ollama create techo360-chatbot:v2 -f Modelfile.v2`): `success`.
Prueba de inferencia end-to-end contra `techo360-chatbot:v2`: HTTP
200, ~9,5s con el modelo ya cargado (4,5s de generación pura). La
respuesta reprodujo el mismo patrón cualitativo observado en la
evaluación vía transformers: acertó 4 de 5 nombres de repositorio
reales, inventó el quinto (`techo360-estaciones` esta vez, con
temperatura 0,3 del Modelfile en vez de greedy) — confirma que el
comportamiento del modelo se preserva de forma consistente entre el
pipeline de evaluación (transformers/PEFT) y el de producción
(GGUF/Ollama), lo cual da confianza en que la comparación v1-vs-v2 de
arriba es representativa de lo que realmente se serviría.

### Verificación de RAM — medición real, no simulada (sin Docker disponible)

Este entorno no tiene Docker instalado (verificado explícitamente,
`docker --version` no encontrado) — no se pudo crear un contenedor con
límite de memoria de 3 GB para replicar exactamente la restricción del
VPS. En su lugar, se hizo algo más fuerte que una estimación: **se
midió el uso real de memoria del proceso que efectivamente sirve el
modelo**, mientras atendía inferencias reales.

Ollama en Windows corre el modelo en un proceso hijo separado,
`llama-server.exe` (no en el proceso `ollama.exe` principal, que solo
orquesta) — se identificó por su línea de comandos
(`--model ...sha256-...` apuntando exactamente al blob de
`techo360-chatbot:v2`, `-c 2048` coincidiendo con el `num_ctx` del
Modelfile).

**Medido con Windows (`Get-Process`), tras varias inferencias reales
(no solo la primera)**:

| Métrica | Valor |
|---|---|
| Working Set (RAM física residente) | 885,3 MB, con pico de **961,3 MB** tras varias inferencias |
| Private Bytes (memoria privada comprometida) | 3 327,2 MB |
| Memoria virtual reservada | ~73,4 GB (incluye el mapeo del archivo GGUF vía mmap, no representa RAM física real) |

**Por qué hay dos números tan distintos, y por qué esto importa para el
VPS**: `llama.cpp` (que Ollama usa internamente) carga los pesos del
GGUF vía `mmap`, así que el sistema operativo no necesita mantener el
archivo completo en RAM física de una vez — las páginas se cargan bajo
demanda y pueden reciclarse. Eso explica el Working Set relativamente
bajo (~960 MB pico) frente al tamaño del archivo (1,92 GB). Sin
embargo, **en un contenedor Linux con límite de cgroup** (que es lo que
realmente restringe el contenedor de Ollama en el VPS, no el
"Working Set" al estilo Windows), las páginas de un archivo mapeado que
el proceso llega a tocar sí pueden contar contra el límite de memoria
del cgroup, dependiendo de la versión de cgroups y de la presión de
memoria del sistema — el comportamiento no es necesariamente idéntico
al de Windows. Si el conteo en el VPS terminara pareciéndose más al
`Private Bytes` medido aquí (3 327 MB) que al `Working Set` (961 MB),
**superaría el límite de 3072 MB del contenedor**.

**Conclusión honesta de esta verificación**: no es una medición directa
en el entorno real (Linux, cgroup, 3 GB), así que no se puede afirmar
con certeza que el modelo quepa cómodamente en el VPS. El escenario
optimista (Working Set ~960 MB + overhead) deja margen amplio; el
escenario pesimista (Private Bytes ~3,3 GB) **excedería** el límite.
Antes de desplegar, es indispensable medir esto directamente en un
contenedor Linux con `--memory=3g` (o en el VPS mismo) — no se puede
confiar en la extrapolación desde Windows para esta decisión
específica.

### Recomendación final

**v2 no está listo para reemplazar a v1 en un eventual despliegue.** La
ampliación del dataset (primer frente de T-95) fue rigurosa y bien
verificada en su fuente, y sí logró el efecto puntual buscado en el
tema de los nombres de repositorio (mejora real, aunque incompleta). Pero
el reentrenamiento completo (segundo ciclo) tuvo un efecto neto negativo
sobre la calidad general del modelo, medido de forma consistente por
dos métricas independientes, incluyendo regresiones nuevas en preguntas
que v1 ya respondía bien y que no tienen relación aparente con los
temas que se intentaron reforzar.

**Recomendación concreta**: mantener `techo360-chatbot:v1` como
candidato para cualquier despliegue futuro (sigue siendo el mejor
modelo disponible), y no promover v2 a producción tal como está. Si se
quiere capturar la mejora real de v2 en nombres de repositorio sin sus
regresiones, valdría la pena explorar, en una futura ronda: (a)
reentrenar solo con los 10 pares de repositorios agregados a los 582
originales (sin los 18 de cobertura, para aislar qué causó qué), (b)
usar un rank de LoRA mayor a 16 para darle más capacidad al adaptador
antes de agregar contenido nuevo, o (c) menos de 3 épocas para reducir
el riesgo de sobreajuste/interferencia sobre el conjunto ampliado. Ninguna
de estas alternativas se probó en el alcance de esta tarea.

La verificación de RAM quedó igualmente inconclusa (ver arriba) — sería
el segundo bloqueante para cualquier despliegue real, independientemente
de cuál adaptador se elija.

**Estado**: ciclo completo T-70→T-92→T-93→GGUF/Ollama ejecutado y
documentado para v2, con hallazgos honestos y sin suavizar en cada
paso. No se desplegó nada al VPS. No se tomó ninguna decisión de
promover v2 — se documenta la evidencia para que la decisión de seguir
o no con v2 se tome con esta información completa.

## Auditoría de calidad de datos — ¿la regresión de v2 es de hiperparámetros o de datos? (completada 2026-09-19)

Antes de decidir el próximo ajuste de entrenamiento, se auditó
`dataset/entrenamiento.jsonl` (610 pares) comparando programáticamente
los 582 pares originales contra los 28 nuevos del primer frente de
T-95, buscando específicamente causas de raíz en los datos (no solo en
hiperparámetros) para la regresión de 9/18 pares documentada arriba.
**Se encontraron tres problemas de datos reales y concretos**, y se
descartó/matizó la hipótesis original sobre VIS/Ley 142.

### 1. Hipótesis VIS/Ley 142 — parcialmente descartada, no confirmada como causa directa

La hipótesis original (documentada en la sección anterior) era que el
par nuevo sobre "soluciones alternativas de acueducto" (que menciona la
Ley 142 de 1994) contaminó la respuesta sobre VIS. **Auditoría**: se
buscaron todas las menciones de "Ley 142" en el dataset completo — **ya
había 3 pares preexistentes** (idx 44, 45, 71, todos sobre
estratificación socioeconómica y Empresas de Servicios Públicos) que
citaban esa misma ley, **antes** de que T-95 agregara un cuarto par.
Además, se confirmó que la cita legal correcta de VIS (Ley 388 de 1997,
artículo 91) **nunca estuvo en los 582 pares originales** — es
exclusiva del holdout, un vacío de entrenamiento preexistente, no
introducido por T-95. Los 17 pares de entrenamiento sobre VIS/VIP citan
otras fuentes (Findeter, Minvivienda, Decreto 1467/2019), nunca Ley 388.

**Conclusión**: no se puede confirmar que el par nuevo haya sido la
causa directa — Ley 142/1994 ya tenía una asociación establecida (3
pares) con el dominio de "servicios públicos domiciliarios" antes de
T-95, y el hueco real (falta de Ley 388 en el entrenamiento) es
anterior y ajeno a esta ronda. Lo más honesto es decir que el par nuevo
pudo haber reforzado marginalmente (de 3 a 4 menciones) una asociación
ya latente, no que la haya creado — evidencia insuficiente para
"confirmar", pero tampoco se descarta del todo sin un experimento de
ablación (reentrenar sin ese par específico).

### 2. Inconsistencia de estilo real y medible entre los 28 pares nuevos y los 582 viejos

- **Longitud**: los pares nuevos promedian 67 palabras de respuesta
  (mediana 68), un 27% más cortos que el promedio histórico de 92
  palabras (mediana 91) de los 582 pares originales.
- **Estructura**: 19 de 28 pares nuevos (68%) tienen exactamente 2
  párrafos; en los 582 viejos, la distribución es más variada (376 de 1
  párrafo, 195 de 2, 11 de 3).
- **Hallazgo más fuerte — apertura "Según [fuente]..."**: de los 361
  pares viejos con fuente, solo **6 (2%)** empiezan la respuesta
  literalmente con "Según...". De los 18 pares nuevos con fuente,
  **10 (56%)** empiezan así, y **12 de 18 (67%)** lo mencionan en algún
  punto — 8 de esas 10 aperturas citan específicamente "Según la SSPD".
  Esto es una anomalía de estilo real y grande, no una percepción: los
  pares nuevos sobre-representan por un factor de ~28x la plantilla
  "Según [FUENTE], [CIFRA]%..." frente a como se escribió el resto del
  corpus.

**Por qué esto importa para la regresión observada**: en T-93 se
documentó que v2 alucina cifras de cobertura usando exactamente ese
formato de cita confiada ("Según el DANE, la cobertura nacional...
99,1%..."), un patrón que v1 ya mostraba pero que en v2 se ve igual o
más consolidado. Es plausible que sobre-representar esa plantilla
específica en 18 pares (aunque solo sea el 3% del dataset) haya
reforzado desproporcionadamente la propensión del modelo a usar ese
molde de respuesta con confianza, incluso cuando no tiene el dato real
memorizado — sin necesariamente enseñarle la cifra correcta en sí.

### 3. Inconsistencia de nomenclatura real en los pares de repositorios (el subconjunto que sí mejoró)

Se compararon los 10 pares nuevos de repositorios contra los 8 pares
viejos que ya tocaban el tema:

| | Nombra los repos como | Longitud promedio |
|---|---|---|
| 8 pares viejos | `backend`, `frontend`, `repositorio de infraestructura` (**sin** prefijo) | 92 palabras (estilo ensayo, "por qué"/"qué ventaja") |
| 10 pares nuevos | `techo360-backend`, `techo360-frontend`, etc. (**con** prefijo, el nombre real de la carpeta/repo Git) | 42 palabras (estilo directo, factual) |

**100% de los pares viejos usan el nombre sin prefijo; 100% de los
nuevos usan el nombre con prefijo** — ambos se refieren al mismo repo
real, pero son dos formas de superficie distintas para el mismo hecho,
enseñadas en la misma ronda de entrenamiento sin armonizar las 8
menciones preexistentes. Esto es exactamente el tipo de "señal
contradictoria" que pidió revisar la auditoría: el modelo recibe 8
ejemplos que asocian el concepto "backend" a una respuesta discursiva
larga sin prefijo, y 10 ejemplos que asocian el mismo concepto a una
respuesta corta y directa con prefijo `techo360-`. Es consistente con
el resultado observado en T-93: v2 sí adoptó parcialmente la
nomenclatura con prefijo (mejora real), pero con inconsistencia
residual (inventa un quinto repositorio en vez de usar `infra`,
mezclando ambos estilos).

### 4. Redundancia conceptual no detectada por el chequeo de duplicados de T-95

El chequeo de duplicados de T-95 (comparación de similitud de texto de
`instruction`, `difflib` ratio > 0,75) no detecta redundancia
*conceptual* cuando la redacción es distinta. Auditoría manual encontró
que al menos 2 de los 18 pares nuevos de cobertura repiten, con
palabras distintas, una lección ya cubierta por pares preexistentes:

- Ya existía (viejo): *"¿Por qué la cifra de cobertura de acueducto que
  ve un usuario en Techo 360 para 2024 podría ser distinta a la que
  reporte oficialmente la SSPD...?"*
- Se agregó (nuevo, T-95): *"¿Por qué es importante distinguir la
  fuente exacta, Censo del DANE o REC de la SSPD, al citar una cifra de
  cobertura...?"*
- El propio holdout (nunca entrenado) pregunta esencialmente lo mismo:
  *"¿Cómo se compara la cobertura de acueducto que muestra Techo 360...
  con la que reporta oficialmente la SSPD...?"*

Además, el dataset **ya tenía 22 pares con fuente SSPD** antes de T-95
(cubriendo SUI, ESP, APS, micromedición, continuidad del servicio,
diferencias TerriData/SSPD) — un hallazgo que debió haberse revisado
**antes** de salir a buscar fuentes nuevas en la primera ronda de T-95,
y no se hizo. El efecto neto: una fracción real de los 18 pares nuevos
aporta menos señal genuinamente nueva de lo que parecía al momento de
redactarlos, mientras que **al mismo tiempo** el batch nuevo enseña dos
lecciones parcialmente contradictorias sobre el mismo tema exacto
(cobertura de acueducto/alcantarillado): "cita la cifra con confianza
citando la fuente" (18 pares, mayoría con plantilla "Según X, Y%") y
"las fuentes pueden no coincidir, verifica de forma independiente"
(los pares híbridos, viejos y nuevos, sobre discrepancias de fuente) —
dos señales en tensión sobre el mismo dominio, en la misma ronda de
entrenamiento.

### 5. Balance temático (repos + cobertura combinados en un solo entrenamiento)

Se evaluó la hipótesis de que combinar los 18 pares de cobertura y los
10 de repos en la misma corrida (en vez de por separado) haya diluido
el efecto de cada uno. **Análisis**: con barajado aleatorio estándar
por época, combinar ambos bloques en un solo archivo `entrenamiento.jsonl`
no cambia cuántas veces el modelo ve cada par a lo largo de las 3
épocas frente a entrenarlos por separado en la misma cantidad de
épocas — el mecanismo de "dilución por combinación" no tiene un canal
obvio para operar así. Lo que sí es real es que **cada bloque, por
separado, ya es una fracción pequeña del total** (18/610 = 3,0%, 10/610
= 1,6%) — la dilución más relevante no es "por estar juntos", sino por
ser, cada uno, una porción minoritaria frente a los 582 pares
preexistentes, combinada con las inconsistencias de estilo/nomenclatura
documentadas arriba dentro de cada bloque.

### Resumen de causas de raíz identificadas

| Causa | Evidencia | ¿Explica qué parte de la regresión? |
|---|---|---|
| Plantilla "Según X" sobre-representada (2%→56%) | Medido exactamente | Cifras de cobertura siguen alucinándose con el mismo formato confiado (no mejoró) |
| Nomenclatura de repos inconsistente (con/sin prefijo) | Medido exactamente (8 vs 10 pares, 100%/100%) | Mejora parcial pero incompleta en nombres de repos (el único caso que sí mejoró) |
| Señales contradictorias sobre citar vs. verificar fuentes | Identificado por lectura cruzada | Posible causa de las regresiones nuevas en preguntas no relacionadas con cobertura ni repos |
| Redundancia conceptual con pares preexistentes | Confirmado, 2-3 casos concretos | Reduce la señal nueva neta aportada, sin invalidar los pares |
| VIS/Ley 142 (hipótesis original) | Refutada como causa directa única, no descartada del todo | No se puede atribuir la regresión del par VIS a esto con confianza |
| Combinar repos+cobertura en un solo entrenamiento | Sin mecanismo claro de dilución identificado | Probablemente no es la causa principal |

## Análisis de las tres opciones de ajuste (sin ejecutar — para decisión externa)

### Opción A — Reentrenar solo con los 10 pares de repos (592 pares totales)

**Hipótesis que resuelve**: aísla el efecto de los pares de repos del
de los pares de cobertura, eliminando la señal contradictoria
"citar con confianza vs. verificar fuentes" que la auditoría identificó
específicamente en el bloque de cobertura. Si la mejora en nombres de
repos se mantiene igual de buena (o mejor) SIN las regresiones
colaterales en preguntas no relacionadas (VIS, autenticación,
dimensiones del IPM, 7 variables del panel), confirmaría que el bloque
de cobertura fue la fuente principal de la interferencia.

**Riesgo**: la auditoría encontró que el bloque de repos **tiene su
propio problema interno** (nomenclatura con/sin prefijo, 42 vs. 92
palabras de longitud) independiente del bloque de cobertura — aislar
los pares de repos no elimina ese problema, así que es razonable
esperar que la mejora en nombres de repos se repita de forma similar
(parcial, no perfecta) a menos que también se armonice la nomenclatura
de los 8 pares viejos antes de reentrenar.

**Lo que predice la auditoría**: la opción más probable de mostrar un
resultado **limpio y atribuible** — mejora en repos comparable o mejor
que v2, y con alta probabilidad, sin las regresiones nuevas en preguntas
no relacionadas con repos (VIS, autenticación, IPM, panel de 7
variables), porque esas preguntas no comparten vocabulario ni bloque de
origen con los pares de repos. Es la opción que la auditoría respalda
más directamente como primer experimento, **si además se corrige la
inconsistencia de nomenclatura de los 8 pares viejos** (agregar el
prefijo `techo360-` a esas 8 respuestas también, para no repetir la
señal contradictoria a menor escala).

### Opción B — Mismos 610 pares, menos épocas (2 en vez de 3)

**Hipótesis que resuelve**: que el problema sea sobreajuste/sobre-
optimización sobre el conjunto ampliado — menos pasos de gradiente,
menos oportunidad de que la plantilla "Según X" sobre-representada o la
nomenclatura contradictoria se consoliden con fuerza.

**Riesgo**: la auditoría no encontró evidencia de que el problema sea
"demasiado entrenamiento" — encontró problemas de **contenido y
consistencia de los datos mismos**, que no dependen de cuántas épocas
se entrene. Reducir épocas es más bien un instrumento contundente que
amortigua la magnitud de cualquier señal (buena o mala) por igual, sin
diagnosticar ni corregir la causa. Con 2 épocas en vez de 3, la curva
de loss de v2 se detendría alrededor de 1,14 de promedio (nivel de la
época 2) — es decir, un ajuste general más débil sobre **todo** el
dataset, no solo sobre las 28 líneas nuevas, con riesgo de sub-ajustar
también contenido que sí estaba bien.

**Lo que predice la auditoría**: probablemente reduzca tanto la
magnitud de las regresiones como la magnitud de la mejora en repos —
un resultado intermedio y menos informativo, porque no aísla ni
corrige ninguna de las causas de raíz identificadas. Es la opción
**menos diagnóstica** de las tres: si mejora, no se sabría si fue por
menos sobreajuste o simplemente por casualidad de dónde quedó el
checkpoint a las 2 épocas.

### Opción C — Mismos 610 pares, mayor rank de LoRA (r=32)

**Hipótesis que resuelve**: que la interferencia sea una limitación de
capacidad — un adaptador de r=16 no tiene suficientes parámetros libres
para representar simultáneamente los hechos reforzados (nombres de
repos) y preservar sin cruce las asociaciones que v1 ya tenía bien
aprendidas.

**Riesgo**: más capacidad puede dar al modelo "espacio" para representar
ambas convenciones de nombres (con y sin prefijo) sin que una desplace
a la otra, pero **no resuelve una señal genuinamente contradictoria**
como "cita con confianza" vs. "verifica la fuente" sobre el mismo tema
— más parámetros no le dicen al modelo *cuándo* aplicar cada
comportamiento si el dato de entrenamiento no distingue los casos.
Duplicar el rank (16→32) es barato en cómputo (pasa de 24,3M a ~48,6M
parámetros entrenables, siguen siendo <1,5% del modelo de 3B) y no
debería tensionar la VRAM de forma significativa dado el margen medido
en T-92 (~1,1 GB libre), pero es un cambio que no ataca directamente
ninguna de las causas de raíz que encontró esta auditoría.

**Lo que predice la auditoría**: podría **atenuar parcialmente** el
problema de nomenclatura de repos (más capacidad para sostener ambas
convenciones sin tanto cruce) pero **no debería resolver** las
regresiones causadas por la contradicción cita-confiada-vs-verificar
del bloque de cobertura, porque esa contradicción existe en los datos
mismos, no en la capacidad del modelo para representarlos. Es la
opción más razonable como **complemento** de una limpieza de datos, no
como sustituto de ella.

### Comparación directa

| Opción | Ataca la causa de raíz identificada por la auditoría | Riesgo principal | Qué tan informativo es el resultado |
|---|---|---|---|
| A — Solo repos, aislado | Sí, directamente (elimina la contradicción del bloque de cobertura) | Nomenclatura de repos sigue siendo inconsistente si no se corrige aparte | Alto — resultado limpio y atribuible |
| B — Menos épocas | No — no es un problema de sobreajuste según la evidencia | Sub-ajuste general, resultado intermedio difícil de interpretar | Bajo — no aísla ninguna causa |
| C — Mayor rank LoRA | Parcialmente — ayuda con capacidad, no con contradicción de datos | Ninguno serio (costo computacional bajo), pero puede no resolver el problema principal | Medio — útil como complemento, no como prueba aislada |

No se ejecutó ninguna de las tres opciones — este análisis es solo para
apoyar la decisión externa de qué probar primero, según lo pedido.

## Experimento aislado: Opción A ejecutada — v3 (completado 2026-09-19)

Se ejecutó la Opción A recomendada por la auditoría, con la corrección
previa necesaria. **Resultado: positivo y confirma la hipótesis de la
auditoría** — v3 recupera la mayoría de las regresiones de v2 y, en la
categoría que más importaba (sin_fuente), supera a v1.

### Paso 0 — Corrección de nomenclatura en los 8 pares viejos de repos

Antes de armar el dataset aislado, se corrigieron los 8 pares
preexistentes de `dataset/entrenamiento.jsonl` que nombraban los
repositorios sin el prefijo real (`backend` → `techo360-backend`,
`frontend` → `techo360-frontend`, `chatbot` → `techo360-chatbot`,
`repositorio de infraestructura` → `techo360-infra`), armonizando con
la convención de los 10 pares nuevos. Solo se tocó la nomenclatura, no
el resto del contenido de las respuestas.

**Hallazgo adicional durante la corrección**: se encontró que 4 de los
propios 10 pares nuevos de repos tenían una inconsistencia interna —
por ejemplo, el par sobre `techo360-infra` nombraba a los otros cuatro
repositorios ("backend, frontend, chatbot y proyeccion") **sin**
prefijo en la misma respuesta donde introducía `techo360-infra` **con**
prefijo. Se corrigieron también estos 4 casos. Verificado con un
barrido de todo el dataset (610 pares) que no queden menciones sin
prefijo en los 18 pares de arquitectura de repositorios (los ~90 usos
de "backend"/"frontend"/"chatbot" como sustantivo genérico en preguntas
técnicas no relacionadas con la enumeración de los 5 repos, ej. "¿qué
tecnologías componen el stack del backend?", se dejaron intactos —
fuera del alcance de esta corrección, que es específicamente sobre
nomenclatura de identificadores de repositorio, no sobre vocabulario
técnico general). El conteo total de `entrenamiento.jsonl` se mantiene
en 610 pares.

### Paso 1-2 — Dataset aislado experimental

`dataset/entrenamiento_v3_solo_repos.jsonl` — **592 pares**: los 582
originales (con la nomenclatura ya corregida) + los 10 nuevos de
repositorios, **sin** los 18 de cobertura de acueducto/alcantarillado.
Archivo explícitamente marcado como experimental en
`dataset/README.md` — no reemplaza el canónico de 610 pares.

### Paso 3 — T-70 + T-92 sobre el dataset aislado

`convertir_dataset.py` y `entrenar_lora.py` se parametrizaron
(`--entrada`/`--salida` y `--dataset`/`--version` respectivamente) para
poder correr sobre el dataset aislado sin tocar los artefactos
canónicos. Salida: `dataset/entrenamiento_formateado_v3/train.jsonl`
(592 líneas, 0 fugas de `source`, verificado igual que las corridas
anteriores) y `training/adapters/techo360-v3/`.

| | v1 (582) | v2 (610) | v3 (592, aislado) |
|---|---|---|---|
| Steps totales | 219 | 231 | 222 |
| Tiempo total | 40,30 min | 43,68 min | 44,60 min |
| Loss inicial | 2,2472 | 2,0979 | 1,9140 |
| Loss final (último step) | 0,7986 | 0,7073 | 0,8111 |
| Loss promedio (Trainer) | — | 1,1804 | 1,1813 |
| VRAM pico reserved/allocated | 5020,0 / 4731,1 MB | 5030,0 / 4731,6 MB | **5018,0 / 4731,1 MB** |

**La configuración de memoria se mantuvo estable**, prácticamente
idéntica a v1 y v2 en todo momento — ningún indicio del problema de
paginación de VRAM de la primera corrida de T-92, ni de la anomalía
puntual de v2 (no se observaron steps anómalos en esta corrida).

### Paso 4 — T-93 contra el holdout, base/v1/v2/v3

Script: [`evaluar_holdout_v3.py`](evaluar_holdout_v3.py) — un solo
modelo base cargado, tres adaptadores PEFT nombrados (v1/v2/v3)
alternados con `set_adapter()`. Métricas:
[`metrica_rouge_l_v3.py`](metrica_rouge_l_v3.py) y
[`rubrica_manual_v3.py`](rubrica_manual_v3.py).

**ROUGE-L (F1)** — v3 supera a v1 y a v2 en las tres categorías:

| | Base | v1 | v2 | **v3** |
|---|---|---|---|---|
| General | 0,1899 | 0,2426 | 0,2348 | **0,2567** |
| Con fuente | 0,1991 | 0,2466 | 0,2427 | **0,2574** |
| Sin fuente | 0,1807 | 0,2386 | 0,2268 | **0,2560** |

**Rúbrica manual (1-5, auto-evaluación de IA)**:

| | Base ex. | v1 ex. | v2 ex. | **v3 ex.** | Base rel. | v1 rel. | v2 rel. | **v3 rel.** |
|---|---|---|---|---|---|---|---|---|
| General | 1,167 | 2,944 | 2,389 | **2,944** | 1,722 | 3,944 | 3,389 | **3,722** |
| Con fuente | 1,222 | 2,778 | 2,222 | 2,444 | 1,889 | 3,556 | 3,222 | 3,333 |
| **Sin fuente** | 1,111 | 3,111 | 2,556 | **3,444** | 1,556 | 4,333 | 3,556 | **4,111** |

**v3 vs v1** (exactitud): empatan en el promedio general (2,944 = 2,944)
y **v3 supera a v1 en sin_fuente** (3,444 vs 3,111) — la categoría que
la tarea identificó como la que más importaba. 4 pares mejoraron, 5
empeoraron, 9 quedaron igual — mucho más equilibrado que el neto
negativo de v2 (1 mejoró, 9 empeoraron).

**v3 vs v2** (exactitud): **8 pares mejoraron, solo 1 empeoró**, 9
quedaron igual — confirma directamente la hipótesis de la auditoría:
aislar los pares de repos del bloque de cobertura (más corregir la
nomenclatura) recupera la mayor parte de lo que v2 había roto.

### ¿Se sostiene o mejora la corrección de nombres de repos?

**Sí, y es el mejor resultado de las tres versiones.** Progresión
completa en la pregunta del holdout (par 9):

| | v1 | v2 | v3 |
|---|---|---|---|
| Nombres reales acertados | 0 de 5 | 4 de 5 (inventa un 5º) | **4 de 5 (no inventa nada, solo omite el 5º)** |
| Exactitud (rúbrica) | 1 | 3 | **4** |

v3 nombra correctamente `techo360-backend`, `techo360-frontend`,
`techo360-chatbot` y `techo360-proyeccion` (con el prefijo correcto en
los 4 casos) y simplemente no completa la lista con un quinto, en vez
de inventar uno falso como hizo v2 (`chatbot-visualización` en la
evaluación vía transformers, `techo360-estaciones` en la prueba vía
Ollama). Un patrón de falla más seguro — omitir es preferible a
inventar con confianza.

### ¿Vuelven al nivel de v1 las preguntas que v2 hizo empeorar?

| Pregunta (par del holdout) | v1 | v2 | v3 | ¿Se recuperó? |
|---|---|---|---|---|
| VIS — cita legal | 3 | 2 (cita Ley 142/1994, incorrecta) | **3** (ya no cita ninguna ley incorrecta) | **Sí, totalmente** |
| Autenticación — JWT | 4 | 2 (inventa HMAC/verificación de IP) | **4** (vuelve a identificar JWT) | **Sí, totalmente** |
| 15 indicadores/dimensiones IPM | 2 | 1 (dimensiones inventadas) | **3** | **Sí, y mejor que v1** |
| 7 variables del panel | 2 | 1 (estructura fabricada) | **3** | **Sí, y mejor que v1** |
| Score, cálculo paso a paso | 3 | 3 | **4** (nombra las 3 variables reales exactas) | Mejoró más allá de v1 |
| Qué es Techo 360 | 4 | 2 (inventa alcance falso) | 3 | Parcial — no vuelve a la precisión completa de v1, pero ya no inventa alcance |
| Score vs. IPM oficial (umbral 33,3%) | 5 | 3 | 3 | **No se recuperó** |
| Comparación TerriData vs. SSPD | 4 | 3 | 3 | **No se recuperó** |

**6 de 8 regresiones identificadas se recuperaron total o parcialmente**
al aislar los pares de repos del bloque de cobertura — confirma que el
bloque de cobertura (con su plantilla "Según X" sobre-representada y su
señal contradictoria "cita con confianza vs. verifica la fuente") era,
en efecto, el principal responsable de esas regresiones específicas.

**2 no se recuperaron** (par 16, umbral 33,3%; par 17, TerriData vs.
SSPD) — ambas relacionadas con comparar el Score de Privación de Techo
360 contra el IPM/SSPD oficiales. Como estos dos pares **no** dependen
de los 18 pares de cobertura removidos en este experimento (v3 no los
incluye y el problema persiste igual), esto indica que esta regresión
específica tiene una causa distinta, no identificada todavía —
posiblemente ruido normal de reentrenar con cualquier composición
distinta de datos, o alguna interacción con otro contenido del dataset
no aislado en este experimento. Queda como hallazgo abierto para una
futura auditoría si se decide investigar más.

**Nueva anomalía puntual detectada** (no vista en v1 ni v2): en el par
sobre fuentes de datos de las 7 variables (par 14), v3 inventa una
variable inexistente, "cobertura de internet", que no aparece en
ningún par de entrenamiento ni en la referencia del holdout. Es un
punto aislado (1 de 18 pares) y no cambia la evaluación general, pero
se reporta sin suavizar, tal como se pidió.

### Conclusión del experimento

La auditoría de datos acertó: la causa principal de la regresión de v2
era el bloque de cobertura de servicios públicos (su plantilla de cita
sesgada y su señal contradictoria), no una limitación de capacidad del
LoRA ni un problema de número de épocas. Al aislarlo y corregir la
inconsistencia de nomenclatura de los repos, v3 recupera el terreno
perdido y, en el aspecto que más importaba (nombres de repositorio,
además de la categoría sin_fuente en general), **supera a v1**.

**No se avanzó a GGUF/Ollama con v3** — según lo pedido, se detiene
aquí hasta confirmar si este resultado en T-93 justifica seguir. El
adaptador `training/adapters/techo360-v3/` está listo si se decide
continuar.

**Pendiente, no tocado en este experimento**: el problema de la
plantilla de cita sesgada ("Según X...") de los 18 pares de cobertura
sigue sin resolverse — las cifras de cobertura nacional (pares 2 y 3
del holdout) siguen tan alucinadas en v3 como en v1 y v2, porque esos
pares nunca se re-entrenaron aquí. Esa es la "ronda separada" que
queda pendiente, como se acordó explícitamente no tocar en esta tarea.

## Investigación de las 2 regresiones no recuperadas (completada 2026-09-19)

Se investigó por qué los pares 16 (umbral 33,3%) y 17 (TerriData vs.
SSPD) no se recuperaron en v3 pese a que v3 no incluye los 18 pares de
cobertura removidos. **Conclusión honesta y matizada: no es una causa
única y limpia — la evidencia real es más compleja de lo que sugería la
comparación greedy-only de T-93, y hay que corregir la narrativa
inicial en ambos casos.**

### Paso 0 — Confirmación de que la corrección de nomenclatura no tocó nada más

`git diff` sobre `dataset/entrenamiento.jsonl` muestra exactamente 35
inserciones y 7 eliminaciones. Las 7 líneas eliminadas corresponden,
verificado una por una, a los 7 de los 8 pares de repos que sí
necesitaban edición (el octavo, sobre despliegue automático por rama,
no mencionaba ningún nombre sin prefijo y no se tocó). **Confirmado: la
corrección de nomenclatura no modificó ningún otro par del dataset.**

### Paso 1 — Pares del dataset base sobre estos dos temas

**Sobre el umbral 33,3%**: se encontraron 3 pares preexistentes (idx
22, 382, 383 — los tres en los 582 originales, compartidos
idénticamente por v1 y v3) que **enseñan explícita y repetidamente la
respuesta correcta**: *"el Score de Privación de Techo 360 NO utiliza
ningún umbral equivalente al 33,3% del IPM oficial"* (idx 382, cita
textual). Esto descarta un vacío de datos — el hecho correcto está
representado con fuerza en ambas versiones del dataset por igual.

**Sobre TerriData vs. SSPD/anexo censal**: se encontraron dos grupos de
pares preexistentes, ambos en los 582 originales:
- Un grupo (idx 18, 295, 364, entre otros — ~28 pares) que establece
  que **acueducto y alcantarillado vienen de TerriData**. El idx 364 en
  particular (*"¿Por qué Techo 360 usa datos de TerriData para la
  cobertura de acueducto y alcantarillado en lugar de usar directamente
  las cifras que publica la SSPD?"*) es casi una paráfrasis directa de
  la pregunta 17 del holdout.
- Un grupo distinto (idx 366, 371, 379, entre otros — 8 pares) que
  correctamente establece que **el déficit habitacional** (no el
  acueducto) viene del **anexo censal del DANE**.

v3 (y v2) confunden estos dos hechos, aplicando la fuente correcta del
déficit habitacional (anexo censal) a la pregunta sobre acueducto. Es
una confusión cruzada entre dos hechos similares en forma ("¿de qué
fuente oficial viene la variable X de Techo 360?") que **ya existía
como riesgo latente en los 582 pares originales**, compartidos
idénticamente por v1 y v3 — no algo introducido ni eliminado por T-95.

### Paso 2-3 — Comparación de texto completo + prueba de variabilidad real

Script: [`investigar_regresiones.py`](investigar_regresiones.py). Para
cada uno de los 3 pares (14, 16, 17), se generó la respuesta **3 veces
en modo greedy** (`do_sample=False`, para confirmar determinismo) y
**3 veces con muestreo** (`do_sample=True, temperature=0.3, top_p=0.9`
— los mismos parámetros que usa el Modelfile de Ollama en producción,
con semillas fijas 1/2/3 para reproducibilidad), para v1 y v3.

**Determinismo confirmado**: las 6 tandas de 3 corridas greedy (v1/v3 ×
3 preguntas) fueron **100% idénticas entre sí en las 6 tandas** — cero
no-determinismo de GPU/cuDNN. Cualquier diferencia entre versiones viene
de los pesos entrenados, no del muestreo aleatorio en la decodificación
greedy.

**Bajo muestreo real (temperature=0.3), el panorama cambia sustancialmente:**

| Par | v1 correcto (greedy + muestreo, de 6) | v3 correcto (greedy + muestreo, de 6) | ¿Regresión real o artefacto de greedy? |
|---|---|---|---|
| 16 — umbral 33,3% | 5/6 (falla 1/3 en muestreo: inventa un umbral de **50%**, un número *distinto* pero igual de falso) | 3/6 (falla 3/3 en greedy, pero **acierta 3/3 en muestreo** — nunca le atribuye el umbral a Techo 360 en ninguna de las 3 corridas muestreadas) | **Mayormente artefacto de greedy** — v1 tampoco es inmune a este error bajo muestreo, y v3 lo evita consistentemente bajo muestreo |
| 17 — TerriData vs. SSPD | 5/6 (acierta en las 3 greedy + 2/3 muestreo) | 1/6 (falla en las 3 greedy + 2/3 muestreo, acierta solo 1/3) | **Regresión real, aunque no absoluta** — diferencia sostenida en 6 corridas independientes, no solo en la corrida greedy única |

**Par 16 (umbral 33,3%) — la narrativa de "regresión" no se sostiene
tal como se planteó.** Bajo muestreo real, v1 también fabrica un umbral
falso para el Score de Privación (50%, en la corrida con seed=2) —
prueba directa de que v1 **tampoco tiene este hecho aprendido de forma
robusta**, y que su acierto en las 3 corridas greedy fue, en retrospectiva,
más una coincidencia de qué camino de decodificación resultó marginalmente
más probable en esa configuración exacta de pesos, no un dominio sólido
del hecho. v3, notablemente, **evita el error las 3 veces bajo muestreo**
pese a fallar consistentemente en greedy — el patrón contrario al que
sugería T-93. Con un tamaño de muestra de solo 3 corridas por condición
esto no permite estimar tasas de error precisas, pero sí alcanza para
descartar la lectura simple de "v1 lo sabe, v3 no": ambas versiones
comparten una incertidumbre real y no resuelta sobre este hecho
específico, y greedy simplemente expone puntos distintos de esa
incertidumbre compartida para cada una.

**Par 17 (TerriData vs. anexo censal) — esta sí parece una diferencia
real, aunque parcial, no solo un artefacto de greedy.** A diferencia
del par 16, aquí v1 acierta en 5 de 6 corridas (greedy + muestreo) y v3
solo en 1 de 6 — una diferencia sostenida a través de condiciones de
decodificación distintas, no explicable únicamente por qué camino
greedy resultó elegido. Esto sugiere que, para este hecho específico,
el reentrenamiento (en cualquiera de sus variantes, v2 o v3) sí
desplazó de forma más genuina el aprendizaje del modelo hacia la
asociación incorrecta (anexo censal) en detrimento de la correcta
(TerriData) — consistente con la hipótesis de "confusión entre dos
hechos similares preexistentes" del Paso 1, aunque **no se puede
confirmar con certeza total sin un experimento de ablación adicional**
(por ejemplo, entrenar sin el idx 364 en particular, o con más énfasis
en la distinción).

### Hallazgo de "cobertura de internet" (par 14) — reproducible en greedy, no en muestreo

La fabricación de una variable "cobertura de internet" inexistente
apareció **exactamente igual en las 3 corridas greedy de v3** (texto
idéntico carácter por carácter) — no fue un evento aislado de una sola
generación, es un comportamiento estable de la ruta de decodificación
greedy de v3 para este prompt específico. Sin embargo, **no apareció en
ninguna de las 3 corridas con muestreo** (temperature=0.3) de v3, ni en
ninguna de las 6 corridas (greedy + muestreo) de v1. Es un hallazgo
real y reproducible, pero acotado a la decodificación greedy
determinista — bajo el muestreo que efectivamente usa producción
(Ollama, `temperature=0.3`), este caso puntual no se manifestó en las 3
pruebas realizadas, aunque tampoco se puede descartar que ocurra con
otras semillas no probadas.

### Conclusión honesta

No se encontró una causa única, limpia y accionable para las 2
regresiones — y es importante no forzar una narrativa donde la
evidencia no la sostiene:

1. **El umbral 33,3% (par 16) no es, con la evidencia disponible, una
   regresión sólida de v3 sobre v1** — es más preciso describirlo como
   una **incertidumbre compartida por ambas versiones** sobre un hecho
   que, pese a estar bien representado en el dataset (3 pares
   explícitos), no llegó a aprenderse de forma robusta e inequívoca en
   ninguna de las dos corridas de entrenamiento. La comparación
   greedy-only de T-93 expuso puntos distintos de esa misma
   incertidumbre en cada versión, dando la apariencia de una regresión
   más clara de lo que realmente es.
2. **TerriData vs. SSPD (par 17) sí muestra una diferencia real y
   sostenida** entre v1 y v3 a través de 6 corridas independientes por
   versión, consistente con la hipótesis de que dos hechos similares
   preexistentes en el dataset base (acueducto→TerriData vs. déficit
   habitacional→anexo censal) generan una confusión cruzada sensible a
   la composición exacta del entrenamiento — pero esto tampoco se
   puede confirmar como causa definitiva sin un experimento de
   ablación adicional, que no se hizo en el alcance de esta
   investigación.
3. **"Cobertura de internet" es real y reproducible bajo greedy, pero
   no se manifestó bajo el muestreo que usaría producción** en las
   pruebas realizadas — un hallazgo acotado, no una alucinación
   dominante del modelo.

**Implicación práctica más amplia**: esta investigación revela que
comparar versiones del modelo usando **solo decodificación greedy**
(como hizo toda la evaluación de T-93 hasta este punto) puede
sobre-representar o sub-representar diferencias reales entre versiones,
porque greedy colapsa una distribución de probabilidad genuinamente
incierta a un solo punto determinista. Una evaluación de T-93 futura
que incluya múltiples muestreos por pregunta (no solo una corrida
greedy) daría una lectura más confiable de qué diferencias entre
versiones son reales y cuáles son artefactos de qué camino greedy
resultó elegido — no se rehace la evaluación completa de T-93 con este
método en el alcance de esta investigación puntual, pero queda
documentado como una limitación metodológica a tener en cuenta.

**Estado**: investigación diagnóstica completada — no se modificó el
dataset ni se reentrenó nada. Los datos completos de las 36
generaciones (6 corridas × 3 pares × 2 versiones) quedan en
`training/investigacion_regresiones.json` para revisión adicional si
se decide profundizar.

## T-93 rehecho con muestreo real (v1 vs v3, 180 generaciones)

Motivación: la investigación anterior mostró que comparar versiones
solo con decodificación greedy puede mal-representar diferencias
reales. Esta corrida rehace T-93 completo bajo las condiciones reales
de generación de producción: `temperature=0.3, top_p=0.9,
repetition_penalty=1.15` (equivalente exacto de `repeat_penalty` de
Ollama), los mismos parámetros que `training/ollama/Modelfile` y
`Modelfile.v2` — no valores nuevos elegidos para esta prueba.

Para los 18 pares del holdout, con v1 y con v3, se generaron 5
corridas por par (seeds 1-5), es decir 180 generaciones. No se
modificó el modelo ni el dataset — solo inferencia repetida. Script:
`training/evaluar_holdout_muestreo.py`. Duración real: **81.7
minutos** (estimación previa: ~66 min; el exceso se debe a una
generación anómala de v3 en el par 6/seed5 que tardó 453 s en vez de
los ~20 s habituales, aparentemente por un patrón repetitivo que
retrasó el criterio de parada, pero completó sin error).

### ROUGE-L (media ± desviación estándar de las 5 corridas)

| Categoría   | v1 (media) | v3 (media) |
|-------------|-----------:|-----------:|
| General     | 0.2248     | 0.2310     |
| Con fuente  | 0.2310     | 0.2330     |
| Sin fuente  | 0.2186     | 0.2291     |

Pares donde la diferencia de medias supera la desviación estándar
combinada (posible señal real, no solo ruido de muestreo): **par 9**
(delta +0.053, sin_fuente — los 5 repos), **par 14** (delta +0.035,
sin_fuente — fuentes de las 7 variables) y **par 15** (delta +0.071,
sin_fuente — rol del servicio de proyección). Los tres favorecen a v3.
Detalle completo por par en `training/eval_holdout_rouge_l_muestreo.json`.

### Rúbrica manual de exactitud (1-5) aplicada a cada una de las 5 corridas individuales

Auto-evaluación de IA (Claude leyendo cada una de las 180
generaciones), no rúbrica humana. Promedios de las medias por par:

| Categoría   | v1    | v3    |
|-------------|------:|------:|
| General     | 2.033 | 2.289 |
| Con fuente  | 2.067 | 2.111 |
| Sin fuente  | 2.000 | 2.467 |

**Diferencias consistentes bajo muestreo** (la mayoría o todas las 5
corridas de cada versión apuntan en la misma dirección — estas son las
únicas que cuentan para la recomendación final):

- **Par 9 — los 5 repositorios de Techo 360 (hallazgo más fuerte y más
  consistente de toda la corrida)**: v1 falla en las 5/5 corridas
  (nombres completamente inventados: `core/data/service/schema/
  infrastructure`, `database/models/services/api/infrastructure`,
  etc.). v3 acierta los 5 repos reales con el prefijo `techo360-`
  correcto en las **5/5 corridas**. El patrón que ya se había visto en
  greedy (v3 omite en vez de inventar) se confirma bajo muestreo real
  de forma total: exactitud v1 = 1.0/5.0, v3 = 4.0/5.0 en las 5
  corridas, sin una sola excepción en ninguna dirección.
  - Efecto secundario nuevo (no visto antes): **4/5 corridas de v3**
    (no 5/5 como se reportó inicialmente — corregido tras releer el
    texto completo; seed 2 dice algo distinto pero igual de falso:
    "un chatbot simple sin inteligencia artificial avanzada") describen
    el chatbot como construido en **"Dialogflow"**, framework que no se
    usa realmente (Techo 360 usa un LLM propio fine-tuneado servido por
    Ollama). Investigación puntual de esta alucinación en
    `training/investigar_dialogflow.py`:
    - "Dialogflow"/"Rasa"/"Botpress" tienen **0 apariciones** en los
      592 ni en los 610 pares del dataset — es alucinación pura del
      conocimiento pre-entrenado, no algo aprendido del fine-tuning.
    - "Ollama" sí está bien cubierto (8 pares, con detalle de RAM, RAG,
      pgvector, justificación de por qué modelo local), pero **ninguno
      de los 8 pares que enseñan los 5 nombres exactos de repos**
      menciona Ollama — son dos clusters de pares que nunca se cruzan
      en una misma respuesta de entrenamiento.
    - 5 corridas nuevas de v1 para el mismo par confirman que v1
      **nunca** alucina un framework, pero no porque lo resista mejor:
      v1 nunca llega a identificar "chatbot" como su propio
      repositorio con descripción de tecnología en primer lugar (solo
      aparece como mención de paso en 2/5 corridas, dentro de un repo
      con nombre inventado). No tiene la oportunidad estructural de
      cometer ese error específico.
    - **Conclusión**: es un hueco de contenido real (el dataset nunca
      combina "los 5 repos + qué tecnología usa cada uno" en un mismo
      par), no un efecto secundario negativo del refuerzo de
      nomenclatura en sí — el refuerzo simplemente expone el hueco al
      permitir que v3 complete la estructura de la respuesta hasta el
      punto donde antes nadie llegaba. Corregible en una ronda futura
      de datos con 1-2 pares que unan ambos temas explícitamente.
- **Par 14 — fuentes de las 7 variables (TerriData)**: v3 atribuye
  correctamente acueducto y alcantarillado a TerriData en 4/5
  corridas; v1 solo en 1/5 (las demás lo atribuyen erróneamente a
  DANE/SSPD/ECOV). Mejora consistente de v3.
- **Par 17 — TerriData vs SSPD (regresión de v3, confirmada bajo
  muestra más grande)**: v1 nombra TerriData correctamente en 2/5
  corridas (media 2.8); v3 solo en 1/5 (media 2.0). Esto **confirma en
  una muestra 5x mayor** lo que ya había sugerido la investigación
  diagnóstica anterior — es una regresión real, aunque modesta, no un
  artefacto de greedy.
- **Par 5 — número de variables del Score de Privación (hallazgo
  nuevo, no visto en la evaluación greedy anterior)**: v1 acierta las
  3 variables reales (acueducto, alcantarillado, déficit habitacional)
  en 1/5 corridas; v3 nunca lo hace y en **4/5 corridas afirma
  explícitamente "cuatro variables"**, agregando una espuria (pobreza
  multidimensional, educación o trabajo informal, según la corrida).
  Es más consistente en v3 (4/5) que cualquier acierto de v1. Posible
  regresión adicional de v3 que la evaluación greedy no había
  detectado, porque en la corrida greedy original v1 había acertado
  las 3 variables exactas y v3 no — bajo muestreo se ve que v1 tampoco
  es fiable aquí (solo 1/5), pero v3 es consistentemente peor.

**Diferencias inestables** (mezcladas en ambas versiones, dentro del
ruido de muestreo — no deberían pesar en la recomendación):

- Par 0 (definición de IPM): v3 mejor en promedio, pero ninguna
  versión es fiable (ninguna corrida de v1 acierta la atribución
  DNP/DANE ni el umbral).
- Par 1 (déficit cuantitativo/cualitativo), par 4 (¿Qué es Techo
  360?), par 6 (VIS), par 10 (JWT), par 11, par 12, par 13, par 15:
  diferencias pequeñas (±0.2 a ±0.6 en la media de 5) sin patrón
  sistemático claro en ninguna dirección.
- Par 6 (VIS) — dato aislado a vigilar: v3 seed4 fabrica una cita
  legal nueva y falsa ("Ley 142 de 1994, modificada por la Ley 1448 de
  2011") que no aparece en las otras 4 corridas de v3 ni en ninguna de
  v1. Es 1/5, no sistemático, pero reintroduce el patrón de cita legal
  fabricada que T-95/v3 había corregido en otra pregunta del holdout.

**Confirmaciones de hallazgos previos bajo esta muestra más grande**:

- **Par 8 (umbral 33,3% del IPM)**: ninguna de las 10 corridas (5 v1 +
  5 v3) declara correctamente el umbral vigente. Esto **confirma
  definitivamente** la conclusión de la investigación diagnóstica
  anterior: no es una regresión de v2/v3, es una limitación compartida
  y preexistente que ni v1 ni v3 resuelven, visible ahora con 5x más
  evidencia.
- **"Cobertura de internet" (par 11)**: la alucinación aparece en
  **ambas** versiones bajo muestreo (v1 seed5, v3 seed4), cada una
  1/5. Esto refuta la hipótesis de que fuera exclusiva o nueva de v3 —
  es una alucinación compartida y preexistente, expuesta por el
  muestreo en ambos modelos por igual.
- **Par 16 (Score de Privación ≠ IPM oficial)**: empate total, las 10
  corridas (5+5) responden correctamente "no son lo mismo" — confirma
  que este par nunca fue un área de regresión real.
- **Pares 2, 3, 7, 12 (cifras nacionales de cobertura, 15 indicadores
  exactos, procedimiento de cálculo del score)**: ambas versiones
  fallan sistemáticamente y por igual en las 5 corridas — huecos de
  cobertura compartidos y deliberadamente fuera del alcance de este
  experimento, no diferenciadores entre v1 y v3.

Detalle completo, con la nota cualitativa de cada uno de los 18 pares,
en `training/eval_holdout_rubrica_muestreo.json` (generado por
`training/rubrica_manual_muestreo.py`).

### Recomendación final actualizada

**v3 sigue siendo preferible a v1**, pero con matices más finos que
los que arrojaba la comparación greedy:

1. El hallazgo más importante y más sólido de todo T-95 — que v3
   nombra los 5 repositorios reales de Techo 360 con el prefijo
   correcto, mientras v1 los inventa por completo — **se sostiene al
   100% bajo muestreo real** (5/5 vs 0/5), el resultado más consistente
   de las 18 preguntas. Este era el objetivo original del experimento
   aislado y queda confirmado de la forma más sólida posible.
2. La ventaja general de v3 en ROUGE-L y en la rúbrica de exactitud
   (especialmente en `sin_fuente`, 2.47 vs 2.00) se mantiene bajo
   muestreo, impulsada principalmente por el par de los repositorios.
   Sin ese único par, la ventaja de v3 en `sin_fuente` sería mucho más
   modesta.
3. Sin embargo, el muestreo también **confirma** que v3 pierde algo de
   precisión en la pregunta específica de TerriData vs SSPD (par 17,
   regresión ya sospechada) y **revela un hallazgo nuevo**: v3 es más
   consistente que v1 en fabricar una cuarta variable espuria del
   Score de Privación (par 5), algo que la evaluación greedy anterior
   no había detectado porque v1 había acertado esa pregunta por
   casualidad en su única corrida greedy.
4. La alucinación "Dialogflow" (5/5 en v3, siempre junto con el
   acierto de los repos) y la cita legal falsa aislada de VIS (1/5 en
   v3) son datos a vigilar en una eventual siguiente ronda de datos de
   entrenamiento, aunque no cambian la recomendación general.
5. En los huecos de cobertura compartidos y ya conocidos (cifras
   nacionales de servicios públicos, los 15 indicadores exactos del
   IPM, el procedimiento exacto de cálculo del score, el umbral del
   33,3%), **ninguna cantidad de muestreo mejora el resultado** — v1 y
   v3 fallan por igual porque el dataset de entrenamiento nunca cubrió
   esos datos con la precisión necesaria. Esto no es un problema de
   decodificación; es un problema de cobertura de datos pendiente para
   una ronda futura, ya identificado antes y fuera del alcance de este
   experimento.

**Estado**: T-93 rehecho con muestreo completado — no se modificó el
dataset ni se reentrenó nada. GGUF/Ollama para v3 sigue pendiente de
decisión explícita del usuario, ahora con esta evaluación más rigurosa
como base. Scripts: `training/evaluar_holdout_muestreo.py`,
`training/metrica_rouge_l_muestreo.py`,
`training/rubrica_manual_muestreo.py`. Datos crudos de las 180
generaciones en `training/eval_holdout_muestreo.json`.

## Evaluación de alucinación fuera de dominio: v2 vs v3 vs v3.2 (completado 2026-09-24)

Ronda separada de las anteriores — en vez de medir contra el holdout de
18 pares del dominio de Techo 360, mide si el fine-tuning degradó la
capacidad del modelo de responder **preguntas ajenas al proyecto**
(ciencia, historia, geografía, matemáticas, cultura, tecnología, salud,
deportes, lengua). Metodología, rúbrica de 4 categorías, y todos los
datos crudos viven en `training/evaluacion_alucinacion/` (ver su
propio README) — aquí solo el resumen ejecutivo.

**GGUF/Ollama para v3**, pendiente desde T-95 (arriba), se completó
específicamente para poder correr esta prueba por el servicio real:
`training/ollama/Modelfile.v3`, tag `techo360-chatbot:v3`.

**Resultado v2 vs v3** (100 preguntas, 95 puntuables): v2 alucinaba
42,1%, por encima del umbral del 40% acordado como señal de overfitting
probable; v3 bajó a 28,4%. Pero el diagnóstico importante no fue la
cifra sino el patrón: v3 no acertaba más (45 → 43 correctas de 95), sino
que las alucinaciones se convertían en errores de "confusión" — el
modelo se equivocaba casi igual de seguido, pero fabricaba menos datos
con apariencia de fuente.

**Causa raíz, confirmada con evidencia, no por inferencia**
(`training/evaluacion_alucinacion/analizar_dataset.py`): de los 592
pares del dataset aislado de v3, **0 son de conocimiento general
puro** — el 100% tiene vocabulario del dominio de Techo 360. Además, la
longitud de respuesta tiene mediana de 91 palabras, sin un solo ejemplo
de respuesta corta — el modelo nunca vio el patrón "responder en una
línea y parar", lo que explica el patrón dominante de fallo: acertar el
núcleo y rellenar con justificación inventada (ej. "15×4 son sesenta"
seguido de una explicación aritmética falsa).

### v3.2 — mismos hiperparámetros que v3, dataset con conocimiento general

Se generaron 200 pares nuevos de conocimiento general puro (verificados
uno por uno: respuestas de 1-3 frases, cero mención al proyecto,
disjuntos de las 100 preguntas de evaluación), de los cuales 11 (uno o
dos por categoría, todos de confianza alta) se apartaron a
`dataset/holdout.jsonl` (18 → 29 líneas) y 189 se sumaron a los 592
pares aislados de v3 para formar `dataset/entrenamiento_v3_2.jsonl`
(**781 pares**, no los ~792 estimados originalmente — la diferencia son
los 11 apartados al holdout, reportada aquí sin suavizar).

**Config LoRA idéntica a v3, deliberadamente sin tocar ningún
hiperparámetro** — el objetivo era aislar el efecto del cambio de
dataset:

| | r | alpha | dropout | épocas | lr | batch | grad_accum |
|---|---|---|---|---|---|---|---|
| v3 y v3.2 | 16 | 32 | 0,05 | 3 | 2e-4 | 1 | 8 |

| | v3 (592 pares) | v3.2 (781 pares) |
|---|---|---|
| Steps totales | 222 | 294 (+33%, esperado — mismas épocas, más datos) |
| Tiempo total | 44,60 min | 52,38 min |
| Loss final (Trainer) | 1,1813 | 1,1335 |
| VRAM pico reserved | 5018,0 MB | 5034,0 MB |

Empaquetado idéntico al de v3 (fusión → GGUF f16 → cuantización
Q4_K_M → `ollama create`), tag propio `techo360-chatbot:v3.2` (ver
`training/ollama/Modelfile.v3.2`), **sin tocar** `v1`, `v2`, `v3` ni
`latest` (sigue apuntando a v1).

### Resultado v3.2 — confirma la hipótesis

| | v2 | v3 | **v3.2** |
|---|---|---|---|
| Alucinación (95 puntuables) | 42,1% | 28,4% | **3,2%** |
| Correctas | 47,4% | 45,3% | **88,4%** |
| Mediana palabras/respuesta | — | 59,5 | **2,0** |

v3.2 no solo bajó la alucinación a una novena parte de v3 — las
respuestas correctas **casi se duplicaron** (43 → 84 de 95), y la caída
de longitud es transversal a las 9 categorías (incluidas las que
proporcionalmente recibieron menos pares nuevos), lo que descarta
memorización pura de los 189 pares. Confirmado además contra un
**holdout de 11 pares nunca vistos en entrenamiento**: 0 alucinaciones,
8/11 correctas — el modelo generalizó el *comportamiento* de responder
corto y sin inventar, no memorizó los pares específicos.

**Único hallazgo sin mejorar**: la categoría `salud` se mantiene en
12,5% de alucinación en v3 y en v3.2 (mismo patrón: inventa un término
técnico no estándar — "hemociana"/"hemocitina" — para el glóbulo rojo).
No bloquea a v3.2 como modelo de referencia; queda anotado como
candidato a una v3.3 si se decide abrir una ronda más.

**Límite metodológico** (igual que en T-93 y en toda esta carpeta):
quien generó las 100 preguntas y quien clasificó las respuestas es el
mismo evaluador (Claude) — no es una evaluación independiente de
terceros. Detalle completo, tabla por categoría, ejemplos de
alucinación corregida/persistente/nueva, y la nota de nomenclatura de
archivos (`v3_2` con guion bajo en vez de `v3.2` con punto, por una
limitación de import de Python) en
`training/evaluacion_alucinacion/README.md`.

**Estado**: v3.2 queda como modelo de referencia de esta ronda. No hay
cambios de dataset ni de hiperparámetros pendientes salvo que se decida
abrir v3.3 para el caso de salud. `latest` sigue sin tocarse (v1).
