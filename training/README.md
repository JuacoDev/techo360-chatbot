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
