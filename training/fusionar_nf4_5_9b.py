"""5.9b T2: fusiona el LoRA 0.4.0 sobre la base NF4 DEQUANTIZADA (contra la que se entreno con QLoRA), no sobre la bf16.

W_fusionado = dequant_NF4(W_base) + (alpha / r) * B @ A, para cada Linear cuantizada; el resto de tensores (embeddings, normas) se toman del fusionado bf16 de 5.9
(el LoRA no los toca). Escribe un directorio HF listo para `convert_hf_to_gguf.py`. Todo fuera del repo.

    python training/fusionar_nf4_5_9b.py [--origen ~/modelos/techo360-v0.4.0/hf-fusionado] [--destino ~/modelos/techo360-v0.4.0-nf4/hf-fusionado]
"""
import argparse
import os
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "evaluacion"))
import evaluar_v040 as ev  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--origen", type=Path, default=Path.home() / "modelos" / "techo360-v0.4.0" / "hf-fusionado")
    ap.add_argument("--destino", type=Path, default=Path.home() / "modelos" / "techo360-v0.4.0-nf4" / "hf-fusionado")
    a = ap.parse_args()
    assert ev.sha256_archivo(ev.ADAPTADORES["0.4.0"] / "adapter_model.safetensors") == ev.SHA_ADAPTADOR_040
    import bitsandbytes as bnb
    import torch
    from safetensors.torch import load_file, save_file
    _, _, modelo = ev.cargar_modelo(ev.ADAPTADORES["0.4.0"])
    estado = load_file(str(a.origen / "model.safetensors"))
    n_lora = n_solo = 0
    with torch.no_grad():
        for nombre, m in modelo.named_modules():
            base = getattr(m, "base_layer", None)
            if base is not None and hasattr(m, "lora_A") and "default" in m.lora_A:
                w4 = base.weight
                w = bnb.functional.dequantize_4bit(w4.data, w4.quant_state).to(torch.float32)
                delta = (m.lora_B["default"].weight.float() @ m.lora_A["default"].weight.float()) * m.scaling["default"]
                final = (w + delta).to(torch.bfloat16).cpu()
                n_lora += 1
            elif m.__class__.__name__ == "Linear4bit" and ".base_layer" not in nombre:
                w4 = m.weight
                final = bnb.functional.dequantize_4bit(w4.data, w4.quant_state).to(torch.bfloat16).cpu()
                n_solo += 1
            else:
                continue
            clave = nombre.replace("base_model.model.", "", 1).replace(".base_layer", "") + ".weight"
            assert clave in estado and estado[clave].shape == final.shape, clave
            estado[clave] = final.contiguous()
    print(f"lineales con LoRA: {n_lora}; lineales NF4 sin LoRA: {n_solo}", flush=True)
    a.destino.mkdir(parents=True, exist_ok=True)
    save_file(estado, str(a.destino / "model.safetensors"), metadata={"format": "pt"})
    for f in os.listdir(a.origen):
        if f != "model.safetensors":
            shutil.copyfile(a.origen / f, a.destino / f)
    print("listo", a.destino, flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
