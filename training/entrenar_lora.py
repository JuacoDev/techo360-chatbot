"""Fine-tuning LoRA/QLoRA de Llama-3.2-3B-Instruct (T-92), RECONSTRUIDO en T-124.

El `entrenar_lora.py` original nunca estuvo en el repositorio ni en su historial. Este se reconstruyo a partir de `training/README.md` (T-73 y T-92),
del `adapters/techo360-v3.2/adapter_config.json` y del log de v3.2 (`entrenamiento_log.json`: 294 steps, lr lineal de 2e-4 a ~0 sin warmup,
loss en el step 1 = 1.9048). La fidelidad se comprueba con `comparar_fidelidad.py` ANTES de entrenar v3.3.

Config (identica a v3.2, sin cambios de hiperparametros):
  - base meta-llama/Llama-3.2-3B-Instruct en 4-bit NF4, compute bf16; prepare_model_for_kbit_training (gradient checkpointing no reentrante)
  - LoRA r=16, alpha=32, dropout=0.05, bias none, las 7 capas lineales (q,k,v,o,gate,up,down)
  - batch 1 x gradient_accumulation_steps 8, lr 2e-4 lineal sin warmup, PagedAdamW8bit, 3 epocas, max_length 512
  - enmascarado del prompt: labels = -100 desde el inicio hasta el header del assistant (inclusive); la respuesta y <|eot_id|> si aprenden
  - semilla 42 (la de HF Trainer; el README original no documenta otra)

Uso:
    python -u training/entrenar_lora.py --dataset dataset/entrenamiento_formateado_v3_3/train.jsonl --salida training/adapters/techo360-v3.3
    python -u training/entrenar_lora.py --dataset dataset/entrenamiento_formateado_v3_2/train.jsonl --salida <tmp> --max-pasos 30   # corrida de fidelidad
`--max-pasos N` corta el entrenamiento tras N steps de optimizador SIN cambiar el calendario de lr (sigue siendo el de las 3 epocas completas).
Se detiene solo (y lo marca en el log) si un step tarda mas de 30 s o la VRAM reservada supera --limite-vram-mb.
"""
import argparse
import importlib.machinery
import json
import os
import sys
import time
import types

# En este equipo Windows App Control bloquea una DLL de pyarrow (`_json`), asi que `import datasets` falla y arrastra a `transformers.Trainer`.
# Este script no usa `datasets` (trae su propio Dataset de PyTorch y `remove_unused_columns=False`), asi que se registra un modulo vacio.
try:
    import datasets  # noqa: F401
except Exception:  # noqa: BLE001
    _stub = types.ModuleType("datasets")
    _stub.Dataset, _stub.IterableDataset = type("Dataset", (), {}), type("IterableDataset", (), {})
    _stub.__spec__, _stub.__version__ = importlib.machinery.ModuleSpec("datasets", None), "0.0-stub"
    sys.modules["datasets"] = _stub

import torch
from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training
from transformers import (AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig, Trainer, TrainerCallback,
                          TrainingArguments)

MODELO = "meta-llama/Llama-3.2-3B-Instruct"
MARCADOR_ASSISTANT = "<|start_header_id|>assistant<|end_header_id|>\n\n"
MAX_LENGTH = 512
CAPAS = ["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"]
SEMILLA = 42
SEGUNDOS_MAX_POR_STEP = 30.0


def cargar_textos(ruta: str) -> list[str]:
    with open(ruta, encoding="utf-8") as f:
        return [json.loads(linea)["text"] for linea in f if linea.strip()]


def tokenizar_con_mascara(texto: str, tokenizer) -> dict:
    """El texto ya trae el chat template (T-70). Se tokeniza SIN agregar tokens especiales y el prefijo (system+user+header del assistant)
    se tokeniza aparte para calcar el punto de corte exacto del enmascarado."""
    ids = tokenizer(texto, add_special_tokens=False, truncation=True, max_length=MAX_LENGTH)["input_ids"]
    corte_texto = texto.rindex(MARCADOR_ASSISTANT) + len(MARCADOR_ASSISTANT)
    prefijo = tokenizer(texto[:corte_texto], add_special_tokens=False)["input_ids"]
    assert ids[: len(prefijo)] == prefijo, "el prefijo tokenizado por separado no coincide con el inicio del texto completo"
    n = len(prefijo)
    return {"input_ids": ids, "attention_mask": [1] * len(ids), "labels": [-100] * n + ids[n:]}


class DatasetSFT(torch.utils.data.Dataset):
    def __init__(self, textos, tokenizer):
        self.items = [tokenizar_con_mascara(t, tokenizer) for t in textos]

    def __len__(self):
        return len(self.items)

    def __getitem__(self, i):
        return self.items[i]


def collator(lote, pad_id):
    n = max(len(x["input_ids"]) for x in lote)
    pad = lambda v, rel: v + [rel] * (n - len(v))  # noqa: E731
    return {
        "input_ids": torch.tensor([pad(x["input_ids"], pad_id) for x in lote]),
        "attention_mask": torch.tensor([pad(x["attention_mask"], 0) for x in lote]),
        "labels": torch.tensor([pad(x["labels"], -100) for x in lote]),
    }


def verificar_enmascarado(ds: DatasetSFT, tokenizer, textos: list[str]) -> None:
    """Comprueba por asercion el corte en 2 ejemplos (el primero y el ultimo), como en T-92."""
    for i in (0, len(ds) - 1):
        it = ds[i]
        enmascarado = [t for t, l in zip(it["input_ids"], it["labels"]) if l == -100]
        aprendido = [t for t, l in zip(it["input_ids"], it["labels"]) if l != -100]
        m, a = tokenizer.decode(enmascarado), tokenizer.decode(aprendido)
        assert m.endswith(MARCADOR_ASSISTANT), f"ejemplo {i}: el prefijo enmascarado no termina en el header del assistant"
        assert not a.startswith("<|start_header_id|>"), f"ejemplo {i}: la parte aprendida empieza en un header"
        assert a.rstrip().endswith("<|eot_id|>"), f"ejemplo {i}: la respuesta aprendida no termina en <|eot_id|>"
        print(f"  ejemplo {i}: {len(enmascarado)} tokens enmascarados de {len(it['input_ids'])} | respuesta: {a[:60]!r}")


class Monitor(TrainerCallback):
    def __init__(self, max_pasos, limite_vram_mb):
        self.max_pasos, self.limite_vram_mb = max_pasos, limite_vram_mb
        self.filas, self.t_step, self.motivo_parada = [], None, None

    def on_step_begin(self, args, state, control, **kw):
        self.t_step = time.time()

    def on_step_end(self, args, state, control, **kw):
        seg = time.time() - self.t_step
        res = torch.cuda.memory_reserved() / 2**20
        self.filas.append({"step": state.global_step, "epoch": round(state.epoch, 4), "segundos_step": round(seg, 3),
                           "vram_allocated_mb": round(torch.cuda.memory_allocated() / 2**20, 1), "vram_reserved_mb": round(res, 1)})
        if seg > SEGUNDOS_MAX_POR_STEP:
            self.motivo_parada = f"step {state.global_step} tardo {seg:.1f}s (> {SEGUNDOS_MAX_POR_STEP}s): presion de VRAM"
        elif res > self.limite_vram_mb:
            self.motivo_parada = f"VRAM reservada {res:.0f} MB supera el limite de {self.limite_vram_mb} MB"
        elif self.max_pasos and state.global_step >= self.max_pasos:
            self.motivo_parada = f"max-pasos={self.max_pasos} alcanzado (corrida corta, no es una parada por problema)"
        if self.motivo_parada:
            control.should_training_stop = True


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dataset", required=True)
    ap.add_argument("--salida", required=True)
    ap.add_argument("--max-pasos", type=int, default=0)
    ap.add_argument("--limite-vram-mb", type=int, default=5700)
    ap.add_argument("--semilla", type=int, default=SEMILLA)
    args = ap.parse_args()

    t0 = time.time()
    tokenizer = AutoTokenizer.from_pretrained(MODELO)
    tokenizer.pad_token = tokenizer.pad_token or tokenizer.eos_token
    textos = cargar_textos(args.dataset)
    ds = DatasetSFT(textos, tokenizer)
    print(f"{len(ds)} ejemplos; tokens max {max(len(x['input_ids']) for x in ds.items)}; verificacion del enmascarado:")
    verificar_enmascarado(ds, tokenizer, textos)

    bnb = BitsAndBytesConfig(load_in_4bit=True, bnb_4bit_quant_type="nf4", bnb_4bit_compute_dtype=torch.bfloat16)
    model = AutoModelForCausalLM.from_pretrained(MODELO, quantization_config=bnb, device_map={"": 0}, dtype=torch.bfloat16)
    model.config.use_cache = False
    model = prepare_model_for_kbit_training(model, use_gradient_checkpointing=True, gradient_checkpointing_kwargs={"use_reentrant": False})
    lora = LoraConfig(r=16, lora_alpha=32, lora_dropout=0.05, target_modules=CAPAS, bias="none", task_type="CAUSAL_LM")
    model = get_peft_model(model, lora)
    n_train = sum(p.numel() for p in model.parameters() if p.requires_grad)
    n_total = sum(p.numel() for p in model.parameters())
    print(f"parametros entrenables: {n_train:,} de {n_total:,} ({100 * n_train / n_total:.2f} %)")

    targs = TrainingArguments(
        output_dir=os.path.join(args.salida, "_tmp"), per_device_train_batch_size=1, gradient_accumulation_steps=8,
        num_train_epochs=3, learning_rate=2e-4, lr_scheduler_type="linear", warmup_steps=0, optim="paged_adamw_8bit",
        bf16=True, logging_steps=1, save_strategy="no", report_to="none", seed=args.semilla, remove_unused_columns=False,
        gradient_checkpointing=True, gradient_checkpointing_kwargs={"use_reentrant": False}, dataloader_num_workers=0,
    )
    monitor = Monitor(args.max_pasos, args.limite_vram_mb)
    trainer = Trainer(model=model, args=targs, train_dataset=ds, data_collator=lambda l: collator(l, tokenizer.pad_token_id), callbacks=[monitor])
    torch.cuda.reset_peak_memory_stats()
    t_ent = time.time()
    trainer.train()
    seg = time.time() - t_ent

    hist = trainer.state.log_history
    losses = [h["loss"] for h in hist if "loss" in h]
    log = {
        "smoke_test": bool(args.max_pasos), "tiempo_total_segundos": round(seg, 1), "tiempo_total_minutos": round(seg / 60, 2),
        "vram_pico_reserved_mb": round(torch.cuda.max_memory_reserved() / 2**20, 1), "vram_pico_allocated_mb": round(torch.cuda.max_memory_allocated() / 2**20, 1),
        "loss_inicial": losses[0] if losses else None, "loss_final": losses[-1] if losses else None,
        "num_ejemplos": len(ds), "num_epocas": 3, "learning_rate": 2e-4, "dataset": args.dataset, "semilla": args.semilla,
        "parametros_entrenables": n_train, "motivo_parada": monitor.motivo_parada, "steps_completados": trainer.state.global_step,
        "versiones": {"torch": torch.__version__, "transformers": __import__("transformers").__version__, "peft": __import__("peft").__version__,
                      "bitsandbytes": __import__("bitsandbytes").__version__},
        "log_history": hist, "monitor_recursos": monitor.filas,
    }
    os.makedirs(args.salida, exist_ok=True)
    with open(os.path.join(args.salida, "entrenamiento_log.json"), "w", encoding="utf-8") as f:
        json.dump(log, f, ensure_ascii=False, indent=1)
    if not args.max_pasos:
        model.save_pretrained(args.salida)
        tokenizer.save_pretrained(args.salida)
    print(f"\nterminado en {(time.time() - t0) / 60:.1f} min | steps {trainer.state.global_step} | loss {log['loss_inicial']:.4f} -> {log['loss_final']:.4f} | "
          f"VRAM pico reservada {log['vram_pico_reserved_mb']} MB | parada: {monitor.motivo_parada}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
