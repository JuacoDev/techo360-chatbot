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
