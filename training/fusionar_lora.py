"""Fusion LoRA + base, conversion a GGUF f16 y cuantizacion Q4_K_M (T-95, paso 1-3), RECONSTRUIDO en T-124.

Pasos (como en training/README.md, T-95):
  1. carga la base en bfloat16 en CPU (no en 4-bit: fusionar sobre una base cuantizada degradaria precision), aplica el adaptador y `merge_and_unload()`
  2. sustituye los archivos del tokenizador por los originales de meta-llama/Llama-3.2-3B-Instruct (transformers 5.x escribe `tokenizer_class: TokenizersBackend`,
     que no existe en transformers 4.57.6, el que exige el conversor de llama.cpp)
  3. convierte a GGUF f16 con `convert_hf_to_gguf.py` (entorno aislado `gguf-tools`)
  4. cuantiza a Q4_K_M con `llama-quantize.exe` (release precompilado b11056). Desde oct-2026 Windows App Control bloquea los .exe sin firma de
     `llama-cpp-bin`, asi que, si el .exe local no arranca, se usa el MISMO cuantizador dentro del contenedor oficial `ghcr.io/ggml-org/llama.cpp:full`
     (Docker Desktop; compilacion 11459 en T-124). Paso de validacion en training/README.md (T-124): v3.2 re-cuantizado asi se compara tensor por tensor.
No se versiona nada de lo que genera (modelo fusionado y GGUF son de GBs; ver .gitignore).

Uso:
    python training/fusionar_lora.py --adaptador training/adapters/techo360-v3.3 --nombre techo360-v3.3
"""
import argparse
import hashlib
import importlib.machinery
import json
import os
import shutil
import subprocess
import sys
import types

try:
    import datasets  # noqa: F401
except Exception:  # noqa: BLE001  (pyarrow bloqueado por Windows App Control en este equipo; peft no necesita `datasets`)
    _stub = types.ModuleType("datasets")
    _stub.__spec__, _stub.__version__ = importlib.machinery.ModuleSpec("datasets", None), "0.0-stub"
    sys.modules["datasets"] = _stub

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TECHO360 = os.path.dirname(RAIZ)
MODELO = "meta-llama/Llama-3.2-3B-Instruct"
PY_GGUF = os.path.expanduser(r"~\entornos\gguf-tools\Scripts\python.exe")
IMAGEN_LLAMACPP = "ghcr.io/ggml-org/llama.cpp:full"
CONVERSOR = os.path.join(TECHO360, "llama.cpp-tools", "convert_hf_to_gguf.py")
CUANTIZADOR = os.path.join(TECHO360, "llama-cpp-bin", "llama-quantize.exe")
ARCHIVOS_TOKENIZADOR = ["tokenizer.json", "tokenizer_config.json", "special_tokens_map.json"]


def sha256(ruta: str) -> str:
    h = hashlib.sha256()
    with open(ruta, "rb") as f:
        for bloque in iter(lambda: f.read(1 << 24), b""):
            h.update(bloque)
    return h.hexdigest()


def cuantizar(f16: str, q4: str) -> str:
    """Q4_K_M con el .exe local; si Windows App Control lo bloquea, con el contenedor oficial de llama.cpp. Devuelve el metodo usado."""
    try:
        subprocess.run([CUANTIZADOR, f16, q4, "Q4_K_M"], check=True)
        return "llama-quantize.exe b11056 (local)"
    except (OSError, subprocess.CalledProcessError) as exc:
        print(f"llama-quantize.exe local no disponible ({exc.__class__.__name__}); se usa el contenedor {IMAGEN_LLAMACPP}")
    carpeta = os.path.dirname(os.path.abspath(f16))
    subprocess.run(["docker", "run", "--rm", "-v", f"{carpeta}:/m", "--entrypoint", "/app/llama-quantize", IMAGEN_LLAMACPP,
                    "/m/" + os.path.basename(f16), "/m/" + os.path.basename(q4), "Q4_K_M"], check=True)
    return f"llama-quantize en contenedor {IMAGEN_LLAMACPP}"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--adaptador", required=True)
    ap.add_argument("--nombre", required=True, help="p. ej. techo360-v3.3")
    ap.add_argument("--fusionado", default=os.path.join(RAIZ, "training", "modelo_fusionado"))
    ap.add_argument("--gguf", default=os.path.join(RAIZ, "training", "modelo_gguf"))
    args = ap.parse_args()
    carpeta = os.path.join(args.fusionado, args.nombre + "-merged")
    f16 = os.path.join(args.gguf, args.nombre + "-f16.gguf")
    q4 = os.path.join(args.gguf, args.nombre + "-Q4_K_M.gguf")
    for ruta in (CONVERSOR, PY_GGUF):
        assert os.path.exists(ruta), f"no existe {ruta}"
    for ruta in (carpeta, f16, q4):
        assert not os.path.exists(ruta), f"ya existe {ruta}: no se sobrescribe nada"
    os.makedirs(args.gguf, exist_ok=True)

    import torch
    from peft import PeftModel
    from transformers import AutoModelForCausalLM, AutoTokenizer
    print("1) fusion en bf16 (CPU)...")
    base = AutoModelForCausalLM.from_pretrained(MODELO, dtype=torch.bfloat16, device_map={"": "cpu"})
    modelo = PeftModel.from_pretrained(base, args.adaptador).merge_and_unload()
    modelo.save_pretrained(carpeta, safe_serialization=True)
    AutoTokenizer.from_pretrained(MODELO).save_pretrained(carpeta)

    print("2) tokenizador original de la base...")
    from huggingface_hub import snapshot_download
    cache = snapshot_download(MODELO, allow_patterns=ARCHIVOS_TOKENIZADOR, local_files_only=True)
    for nombre in ARCHIVOS_TOKENIZADOR:
        if os.path.exists(os.path.join(cache, nombre)):
            shutil.copyfile(os.path.join(cache, nombre), os.path.join(carpeta, nombre))

    print("3) GGUF f16...")
    subprocess.run([PY_GGUF, CONVERSOR, carpeta, "--outfile", f16, "--outtype", "f16"], check=True)
    print("4) Q4_K_M...")
    metodo = cuantizar(f16, q4)

    info = {"nombre": args.nombre, "adaptador": args.adaptador,
            "gguf_f16": {"ruta": f16, "bytes": os.path.getsize(f16)},
            "cuantizador": metodo, "gguf_q4_k_m": {"ruta": q4, "bytes": os.path.getsize(q4), "sha256": sha256(q4)}}
    with open(os.path.join(args.gguf, args.nombre + "-empaquetado.json"), "w", encoding="utf-8") as f:
        json.dump(info, f, indent=1)
    print(json.dumps(info, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
