"""Compara la corrida de fidelidad de entrenar_lora.py (T-124) contra el log de v3.2. Solo lectura.

Tolerancia fijada en training/README.md ANTES de entrenar:
  - perdida dentro de +-10 % relativo de la registrada en el log de v3.2, en los steps comparables;
  - mismos parametros entrenables (mismas matrices LoRA: nombres y formas) y misma configuracion que adapters/techo360-v3.2/adapter_config.json.

Uso: python training/comparar_fidelidad.py <entrenamiento_log.json de la corrida corta> [--adaptador-v3-2 training/adapters/techo360-v3.2]
Sale con codigo 1 si no se cumple.
"""
import argparse
import json
import os
import statistics
import struct
import sys

TOLERANCIA = 0.10
CONFIG_ESPERADA = {"r": 16, "lora_alpha": 32, "lora_dropout": 0.05, "bias": "none", "task_type": "CAUSAL_LM", "use_dora": False, "use_rslora": False}
CAPAS = {"q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"}


def tensores_safetensors(ruta: str) -> dict:
    """Lee solo la cabecera de un .safetensors: {nombre: forma}."""
    with open(ruta, "rb") as f:
        n = struct.unpack("<Q", f.read(8))[0]
        cab = json.loads(f.read(n))
    return {k: tuple(v["shape"]) for k, v in cab.items() if k != "__metadata__"}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("log_corto")
    ap.add_argument("--adaptador-v3-2", default=os.path.join(os.path.dirname(os.path.abspath(__file__)), "adapters", "techo360-v3.2"))
    ap.add_argument("--adaptador-nuevo", default="", help="carpeta con adapter_model.safetensors del reentrenamiento (opcional, para comparar parametros)")
    args = ap.parse_args()
    fallos: list[str] = []

    ref = json.load(open(os.path.join(args.adaptador_v3_2, "entrenamiento_log.json"), encoding="utf-8"))
    cor = json.load(open(args.log_corto, encoding="utf-8"))
    l_ref = {h["step"]: h["loss"] for h in ref["log_history"] if "loss" in h and "step" in h}
    l_cor = {h["step"]: h["loss"] for h in cor["log_history"] if "loss" in h and "step" in h}
    comunes = sorted(set(l_ref) & set(l_cor))
    print(f"steps comparables: {len(comunes)} (corrida corta: {len(l_cor)} steps; v3.2: {len(l_ref)})")
    difs = [(s, l_cor[s], l_ref[s], (l_cor[s] - l_ref[s]) / l_ref[s]) for s in comunes]
    print("  step  v3.3-rep   v3.2    dif rel")
    for s, a, b, d in difs:
        print(f"  {s:4}  {a:8.4f}  {b:7.4f}  {d:+7.1%}{'   <-- fuera de tolerancia' if abs(d) > TOLERANCIA else ''}")
    fuera = [s for s, _, _, d in difs if abs(d) > TOLERANCIA]
    media_cor = statistics.mean(a for _, a, _, _ in difs)
    media_ref = statistics.mean(b for _, _, b, _ in difs)
    print(f"media sobre los steps comparables: {media_cor:.4f} vs {media_ref:.4f} ({(media_cor - media_ref) / media_ref:+.1%}) | max |dif| por step: {max(abs(d) for *_, d in difs):.1%}")
    if not comunes:
        fallos.append("no hay steps comparables")
    if fuera:
        fallos.append(f"{len(fuera)} step(s) fuera de +-{TOLERANCIA:.0%}: {fuera}")

    cfg = json.load(open(os.path.join(args.adaptador_v3_2, "adapter_config.json"), encoding="utf-8"))
    for k, v in CONFIG_ESPERADA.items():
        if cfg.get(k) != v:
            fallos.append(f"adapter_config.json de v3.2: {k}={cfg.get(k)!r} (se esperaba {v!r})")
    if set(cfg["target_modules"]) != CAPAS:
        fallos.append("adapter_config.json de v3.2: target_modules distintos de las 7 capas esperadas")
    print(f"adapter_config.json de v3.2: r={cfg['r']} alpha={cfg['lora_alpha']} dropout={cfg['lora_dropout']} capas={sorted(cfg['target_modules'])}")

    t_ref = tensores_safetensors(os.path.join(args.adaptador_v3_2, "adapter_model.safetensors"))
    n_ref = sum(__import__("math").prod(s) for s in t_ref.values())
    print(f"v3.2: {len(t_ref)} tensores LoRA, {n_ref:,} parametros entrenables")
    if cor.get("parametros_entrenables") is not None:
        ok = cor["parametros_entrenables"] == n_ref
        print(f"corrida corta: {cor['parametros_entrenables']:,} parametros entrenables -> {'IGUALES' if ok else 'DISTINTOS'}")
        if not ok:
            fallos.append("el numero de parametros entrenables difiere del adaptador de v3.2")
    if args.adaptador_nuevo:
        t_new = tensores_safetensors(os.path.join(args.adaptador_nuevo, "adapter_model.safetensors"))
        iguales = t_new == t_ref
        print(f"adaptador nuevo: mismos nombres y formas de tensores LoRA que v3.2: {iguales}")
        if not iguales:
            fallos.append("nombres o formas de los tensores LoRA distintos de los de v3.2")

    print("\nVEREDICTO:", "CUMPLE la tolerancia de fidelidad" if not fallos else "NO CUMPLE")
    for f in fallos:
        print("  -", f)
    return 1 if fallos else 0


if __name__ == "__main__":
    sys.exit(main())
