"""7.4: fusion del LoRA 0.4.1 (copia de empaquetar_v040.py) con Llama 3.2 3B Instruct (bf16, CPU), GGUF f16 y Q4_K_M. Todo FUERA del repo.

Version de llama.cpp: la del contenedor oficial `ghcr.io/ggml-org/llama.cpp:full` (trae `convert_hf_to_gguf.py` y `llama-quantize` de la MISMA
compilacion, y Windows App Control bloquea los .exe sin firma; el mismo recurso que usa fusionar_lora.py desde T-124). Se registra la version.

    python training/empaquetar_v040.py [--destino C:\\Users\\Eridanus_2\\modelos\\techo360-v0.4.1]

Pasos (cada uno se salta si su salida ya existe): 1) fusion  2) tokenizador original de la base  3) GGUF f16  4) Q4_K_M  5) info + sha256.
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
from pathlib import Path

try:
    import datasets  # noqa: F401
except Exception:  # noqa: BLE001
    _stub = types.ModuleType("datasets")
    _stub.__spec__, _stub.__version__ = importlib.machinery.ModuleSpec("datasets", None), "0.0-stub"
    sys.modules["datasets"] = _stub

RAIZ = Path(__file__).resolve().parents[1]
ADAPTADOR = RAIZ.parent / "trabajo-dataset-0.4.1" / "modelo-0.4.1" / "adaptador"  # fuera del repo; los pesos no se versionan
SHA_ADAPTADOR = "d5f01ec5548cb9d96b564db1ad50bd02d3a9e4ff30739c79c08f2c33ec52d333"
MODELO = "meta-llama/Llama-3.2-3B-Instruct"
IMAGEN = "ghcr.io/ggml-org/llama.cpp:full"
ARCHIVOS_TOKENIZADOR = ["tokenizer.json", "tokenizer_config.json", "special_tokens_map.json"]


def sha256(ruta) -> str:
    h = hashlib.sha256()
    with open(ruta, "rb") as f:
        for b in iter(lambda: f.read(1 << 24), b""):
            h.update(b)
    return h.hexdigest()


def docker(destino: Path, entrypoint: str, *args) -> str:
    r = subprocess.run(["docker", "run", "--rm", "-v", f"{destino}:/m", "--entrypoint", entrypoint, IMAGEN, *args], capture_output=True, text=True, encoding="utf-8")
    if r.returncode != 0:
        print((r.stdout + r.stderr)[-2000:])
        raise SystemExit(f"fallo {entrypoint}")
    return r.stdout + r.stderr


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--destino", type=Path, default=Path(os.path.expanduser("~")) / "modelos" / "techo360-v0.4.1")
    args = ap.parse_args()
    destino = args.destino
    hf = destino / "hf-fusionado"
    f16, q4 = destino / "techo360-v0.4.1-f16.gguf", destino / "techo360-v0.4.1-Q4_K_M.gguf"
    assert RAIZ not in destino.resolve().parents, "el destino debe estar fuera del repo"
    sha_ad = sha256(ADAPTADOR / "adapter_model.safetensors")
    assert sha_ad == SHA_ADAPTADOR, "sha256 del adaptador 0.4.1 distinto"
    destino.mkdir(parents=True, exist_ok=True)
    cfg = json.loads((ADAPTADOR / "adapter_config.json").read_text(encoding="utf-8"))
    assert cfg["base_model_name_or_path"] == MODELO

    if not (hf / "model.safetensors").exists() and not list(hf.glob("model*.safetensors")):
        import torch
        from peft import PeftModel
        from transformers import AutoModelForCausalLM, AutoTokenizer
        print("1) fusion bf16 (CPU)...", flush=True)
        base = AutoModelForCausalLM.from_pretrained(MODELO, dtype=torch.bfloat16, device_map={"": "cpu"})
        modelo = PeftModel.from_pretrained(base, str(ADAPTADOR)).merge_and_unload()
        modelo.save_pretrained(hf, safe_serialization=True)
        AutoTokenizer.from_pretrained(MODELO).save_pretrained(hf)
        from huggingface_hub import snapshot_download
        cache = snapshot_download(MODELO, allow_patterns=ARCHIVOS_TOKENIZADOR, local_files_only=True)
        for n in ARCHIVOS_TOKENIZADOR:  # transformers 5.x escribe tokenizer_class=TokenizersBackend, que el conversor (4.57.6) no conoce
            if os.path.exists(os.path.join(cache, n)):
                shutil.copyfile(os.path.join(cache, n), hf / n)
        # chat_template: el del adaptador (el de entrenamiento) debe ser igual al de la base
        print("   fusion lista", flush=True)
    version = docker(destino, "sh", "-c", "/app/llama-cli --version 2>&1 | tail -3; python3 -c 'import transformers;print(\"transformers\",transformers.__version__)'").strip()
    if not f16.exists():
        print("3) GGUF f16...", flush=True)
        salida = docker(destino, "python3", "/app/convert_hf_to_gguf.py", "/m/hf-fusionado", "--outfile", f"/m/{f16.name}", "--outtype", "f16")
        print(salida[-600:], flush=True)
    if not q4.exists():
        print("4) Q4_K_M...", flush=True)
        salida = docker(destino, "/app/llama-quantize", f"/m/{f16.name}", f"/m/{q4.name}", "Q4_K_M")
        print(salida[-400:], flush=True)
    info = {"adaptador": str(ADAPTADOR), "adaptador_sha256": sha_ad, "base": MODELO, "llama_cpp": version, "imagen": IMAGEN,
            "gguf_f16": {"ruta": str(f16), "bytes": f16.stat().st_size, "sha256": sha256(f16)},
            "gguf_q4_k_m": {"ruta": str(q4), "bytes": q4.stat().st_size, "sha256": sha256(q4)}}
    (destino / "empaquetado.json").write_text(json.dumps(info, indent=1), encoding="utf-8")
    print(json.dumps(info, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
