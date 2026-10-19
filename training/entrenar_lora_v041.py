"""Fine-tuning LoRA/QLoRA de Llama-3.2-3B-Instruct para techo360 0.4.1 (paso 7.4 del plan).

Copia de `entrenar_lora_v040.py` (0.4.0), que no se modifica: mismos hiperparametros, misma perdida recortada. Cambios de 0.4.1:
  - SHA256_DATASET = el de `formateado-sin-h4/train_tokenizado.jsonl` (2.891 pares, sin H4, revision 7.3b aprobada: dataset sha256 f045dea8...; multi-turno con perdida solo sobre la ULTIMA respuesta).
  - `--humo` hace 20 pasos (G0 de 7.4); `--excluir <archivo>` quita del entrenamiento los ids listados (los pares de mas de 1.720 tokens, solo
    si la prueba de VRAM lo exige) y registra el sha256 de la lista y cuantos ejemplos quedan.
  - La verificacion de `cargar_tokenizado` y del enmascarado sigue igual (el ultimo header de asistente marca el inicio de lo aprendido).

Texto heredado de 0.4.0:

Copia de `entrenar_lora.py` (v3.3, que no se modifica). Misma configuracion validada:
  - base meta-llama/Llama-3.2-3B-Instruct en 4-bit NF4, compute bf16; prepare_model_for_kbit_training (gradient checkpointing no reentrante)
  - LoRA r=16, alpha=32, dropout=0.05, bias none, las 7 capas lineales (q,k,v,o,gate,up,down)
  - micro-batch 1 x gradient_accumulation_steps 8 (batch efectivo 8), lr 2e-4 lineal sin warmup, PagedAdamW8bit, 3 epocas
  - enmascarado del prompt: labels = -100 hasta el header del assistant (inclusive); la respuesta y <|eot_id|> si se aprenden
  - semilla 42

Cambios respecto a v3.3 (los unicos permitidos en 5.5):
  - MAX_LENGTH = 2048 y SIN truncar: si algun ejemplo lo excede, el script aborta.
  - Lee `train_tokenizado.jsonl` (input_ids, attention_mask, labels ya calculados en 5.4); no re-tokeniza. Verifica su sha256 antes.
  - Micro-batch 1 con acumulacion 8: no hay padding ni agrupacion por longitud, el orden aleatorio efectivo es el del Trainer (semilla 42).
  - Registra todas las versiones (torch, transformers, peft, bitsandbytes, CUDA) y escribe el log de perdida por paso en CSV.
  - Perdida recortada (autorizada por Juan tras la prueba de humo, que no cabia en 6 GB): `lm_head` y la entropia cruzada solo se
    calculan sobre las posiciones con labels != -100 (con el desplazamiento de labels de siempre). Es la misma perdida que la estandar;
    `--equivalencia` lo demuestra en 5 ejemplos reales antes de entrenar.
  - `--humo`: 10 pasos de optimizador con el ejemplo mas largo repetido (no guarda adaptador).

Uso:
    python -u training/entrenar_lora_v040.py --dataset <train_tokenizado.jsonl> --salida training/adapters/techo360-v0.4.1
    python -u training/entrenar_lora_v040.py --dataset <train_tokenizado.jsonl> --salida <tmp> --humo
"""
import argparse
import csv
import hashlib
import importlib.machinery
import json
import os
import statistics
import subprocess
import sys
import time
import types

# En este equipo Windows App Control bloquea una DLL de pyarrow (`_json`), asi que `import datasets` falla y arrastra a `transformers.Trainer`.
# Este script no usa `datasets`, asi que se registra un modulo vacio (igual que en v3.3).
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
SHA256_DATASET = "9dadb21a258267c76c1cd7a29dfccbf9c2ffe00e81a3be53b2f9f8791b262c8d"
MAX_LENGTH = 2048
EOT_ID = 128009
CAPAS = ["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"]
SEMILLA = 42
EPOCAS = 3
LR = 2e-4
PASOS_HUMO = 20
ACUMULACION = 8


def sha256_archivo(ruta: str) -> str:
    h = hashlib.sha256()
    with open(ruta, "rb") as f:
        for bloque in iter(lambda: f.read(1 << 20), b""):
            h.update(bloque)
    return h.hexdigest()


def cargar_tokenizado(ruta: str) -> list[dict]:
    """Lee los ejemplos ya tokenizados y comprueba por asercion su estructura. No trunca: si alguno excede MAX_LENGTH, aborta."""
    items = []
    with open(ruta, encoding="utf-8") as f:
        for linea in f:
            if not linea.strip():
                continue
            r = json.loads(linea)
            n = len(r["input_ids"])
            assert len(r["attention_mask"]) == n and len(r["labels"]) == n, f"{r['id']}: longitudes de input_ids/attention_mask/labels distintas"
            assert n <= MAX_LENGTH, f"{r['id']}: {n} tokens exceden MAX_LENGTH={MAX_LENGTH}; se aborta (no se trunca)"
            assert all(m == 1 for m in r["attention_mask"]), f"{r['id']}: attention_mask con ceros"
            k = next((i for i, l in enumerate(r["labels"]) if l != -100), None)
            assert k is not None and k > 0, f"{r['id']}: sin tokens aprendidos o sin prefijo enmascarado"
            assert all(l == -100 for l in r["labels"][:k]), f"{r['id']}: hay -100 despues del primer token aprendido"
            assert r["labels"][k:] == r["input_ids"][k:], f"{r['id']}: labels aprendidos distintos de input_ids"
            assert r["labels"][-1] == EOT_ID, f"{r['id']}: el ultimo token aprendido no es <|eot_id|>"
            items.append({"input_ids": r["input_ids"], "attention_mask": r["attention_mask"], "labels": r["labels"], "id": r["id"]})
    return items


class DatasetSFT(torch.utils.data.Dataset):
    def __init__(self, items):
        self.items = items

    def __len__(self):
        return len(self.items)

    def __getitem__(self, i):
        return self.items[i]


def collator(lote, pad_id):
    """Con micro-batch 1 no hay padding efectivo; se deja el relleno (labels=-100) por si se cambiara el micro-batch."""
    n = max(len(x["input_ids"]) for x in lote)
    pad = lambda v, rel: v + [rel] * (n - len(v))  # noqa: E731
    return {
        "input_ids": torch.tensor([pad(x["input_ids"], pad_id) for x in lote]),
        "attention_mask": torch.tensor([pad(x["attention_mask"], 0) for x in lote]),
        "labels": torch.tensor([pad(x["labels"], -100) for x in lote]),
    }


def verificar_enmascarado(ds: DatasetSFT, tokenizer) -> None:
    marcador = "<|start_header_id|>assistant<|end_header_id|>\n\n"
    for i in (0, len(ds) - 1):
        it = ds[i]
        enmascarado = [t for t, l in zip(it["input_ids"], it["labels"]) if l == -100]
        aprendido = [t for t, l in zip(it["input_ids"], it["labels"]) if l != -100]
        m, a = tokenizer.decode(enmascarado), tokenizer.decode(aprendido)
        assert m.endswith(marcador), f"ejemplo {i}: el prefijo enmascarado no termina en el header del assistant"
        assert a.rstrip().endswith("<|eot_id|>"), f"ejemplo {i}: la respuesta aprendida no termina en <|eot_id|>"
        print(f"  {it['id']}: {len(enmascarado)} tokens enmascarados de {len(it['input_ids'])} | respuesta: {a[:60]!r}")


def perdida_recortada(modelo, input_ids, attention_mask, labels, num_items=None):
    """Misma perdida que `ForCausalLMLoss` de HF, pero aplicando `lm_head` solo a los hidden states de las posiciones aprendidas.
    Posicion t predice labels[t+1]: se descartan el ultimo hidden state y el primer label. Suma / num_items_in_batch si viene (como HF con
    acumulacion de gradiente); si no, media."""
    causal = modelo.base_model.model  # LlamaForCausalLM dentro del PeftModel
    h = causal.model(input_ids=input_ids, attention_mask=attention_mask, use_cache=False).last_hidden_state
    lab = labels[:, 1:]
    m = lab != -100
    logits = causal.lm_head(h[:, :-1][m]).float()
    suma = torch.nn.functional.cross_entropy(logits, lab[m], reduction="sum")
    return suma / (num_items if num_items is not None else m.sum())


class TrainerRecortado(Trainer):
    """Trainer con la perdida recortada. La normalizacion por num_items_in_batch y el escalado por acumulacion los sigue decidiendo el
    Trainer igual que con el modelo estandar (model_accepts_loss_kwargs)."""

    tokens_vistos = 0  # para normalizar los tiempos por paso (el largo de los lotes varia mucho)

    def compute_loss(self, model, inputs, return_outputs=False, num_items_in_batch=None, **kw):
        TrainerRecortado.tokens_vistos += int(inputs["input_ids"].numel())
        loss = perdida_recortada(model, inputs["input_ids"], inputs["attention_mask"], inputs["labels"], num_items_in_batch)
        return (loss, None) if return_outputs else loss


def demostrar_equivalencia(model, items, ruta_json) -> bool:
    """5 ejemplos reales (min, p25, mediana, p90, maximo): perdida estandar completa (model(..., labels=)) frente a la recortada, en eval y con
    LoRA B aleatorio (si no, B=0 y el adaptador no tendria efecto). Tolerancia 1e-4. Ademas compara gradientes LoRA en el ejemplo mas corto."""
    g = torch.Generator().manual_seed(SEMILLA)
    for n, p in model.named_parameters():
        if "lora_B" in n:
            p.data = (torch.randn(p.shape, generator=g) * 0.02).to(p.dtype).to(p.device)
    model.eval()
    orden = sorted(range(len(items)), key=lambda i: len(items[i]["input_ids"]))
    elegidos = [orden[0], orden[len(orden) // 4], orden[len(orden) // 2], orden[int(len(orden) * 0.9)], orden[-1]]
    filas, ok = [], True
    for i in elegidos:
        it = items[i]
        ids = torch.tensor([it["input_ids"]], device="cuda")
        am = torch.tensor([it["attention_mask"]], device="cuda")
        lb = torch.tensor([it["labels"]], device="cuda")
        with torch.no_grad(), torch.autocast("cuda", dtype=torch.bfloat16):
            completa = model(input_ids=ids, attention_mask=am, labels=lb).loss.item()
            torch.cuda.empty_cache()
            recortada = perdida_recortada(model, ids, am, lb).item()
        d = abs(completa - recortada)
        ok &= d < 1e-4
        filas.append({"id": it["id"], "tokens": len(it["input_ids"]), "aprendidos": int((lb != -100).sum()), "perdida_completa": completa,
                      "perdida_recortada": recortada, "diferencia_abs": d, "coincide_1e-4": d < 1e-4})
        print(f"  {it['id']:<14} {len(it['input_ids']):>5} tok | completa {completa:.6f} | recortada {recortada:.6f} | |dif| {d:.2e} | {'OK' if d < 1e-4 else 'FALLA'}", flush=True)
    # gradientes en el ejemplo mas corto
    it = items[elegidos[0]]
    ids, am, lb = (torch.tensor([it[k]], device="cuda") for k in ("input_ids", "attention_mask", "labels"))
    grads = []
    for usar_recortada in (False, True, False):
        model.zero_grad(set_to_none=True)
        with torch.autocast("cuda", dtype=torch.bfloat16):
            l = perdida_recortada(model, ids, am, lb) if usar_recortada else model(input_ids=ids, attention_mask=am, labels=lb).loss
        l.backward()
        grads.append(torch.cat([p.grad.flatten().float() for n, p in model.named_parameters() if p.requires_grad and p.grad is not None]))
    model.zero_grad(set_to_none=True)
    rel = ((grads[0] - grads[1]).norm() / grads[0].norm()).item()
    ruido = ((grads[0] - grads[2]).norm() / grads[0].norm()).item()  # piso de ruido: la misma perdida completa corrida dos veces
    print(f"  piso de ruido bf16 (completa vs completa, 2 corridas): error relativo {ruido:.2e}")
    print(f"  gradientes LoRA ({it['id']}): norma completa {grads[0].norm():.6f} | recortada {grads[1].norm():.6f} | error relativo {rel:.2e}")
    with open(ruta_json, "w", encoding="utf-8") as f:
        json.dump({"tolerancia": 1e-4, "todo_coincide": bool(ok), "ejemplos": filas, "grad_error_relativo": rel, "grad_piso_ruido_completa_vs_completa": ruido}, f, ensure_ascii=False, indent=1)
    return bool(ok)


def estado_gpu() -> dict:
    """Temperatura, reloj SM y potencia segun nvidia-smi; vacio si no esta disponible."""
    try:
        o = subprocess.run(["nvidia-smi", "--query-gpu=temperature.gpu,clocks.sm,clocks.max.sm,power.draw", "--format=csv,noheader,nounits"],
                           capture_output=True, text=True, timeout=10).stdout.strip().split(",")
        return {"gpu_temp_c": o[0].strip(), "gpu_reloj_sm_mhz": o[1].strip(), "gpu_reloj_max_mhz": o[2].strip(), "gpu_potencia_w": o[3].strip()}
    except Exception:  # noqa: BLE001
        return {"gpu_temp_c": "", "gpu_reloj_sm_mhz": "", "gpu_reloj_max_mhz": "", "gpu_potencia_w": ""}


class GuardarFinDeEpoca(TrainerCallback):
    def on_epoch_end(self, args, state, control, **kw):
        control.should_save = True


class Monitor(TrainerCallback):
    CAMPOS = ["step", "epoch", "perdida_media_10", "vram_reservada_mb", "segundos_por_paso_media_10", "tokens_por_s", "segundos_por_1000_tokens",
              "gpu_temp_c", "gpu_reloj_sm_mhz", "gpu_reloj_max_mhz", "gpu_potencia_w", "aviso"]

    def __init__(self, max_pasos, limite_vram_mb, segundos_max, ruta_csv=None):
        self.max_pasos, self.limite_vram_mb, self.segundos_max = max_pasos, limite_vram_mb, segundos_max
        self.filas, self.t_step, self.motivo_parada = [], None, None
        self.ruta_csv, self.t_ventana, self.tok_ventana, self.ventanas, self.seg_ventana, self.duplicados = ruta_csv, None, 0, [], [], 0
        if ruta_csv and not os.path.exists(ruta_csv):
            with open(ruta_csv, "w", encoding="utf-8", newline="") as f:
                csv.writer(f).writerow(self.CAMPOS)

    def _ventana(self, state):
        """Cada 10 pasos: pierde media, VRAM, s/paso, GPU. Aviso si el tiempo por 1000 tokens (normalizado por el largo de los lotes) supera
        el doble de la mediana de las 5 primeras ventanas durante 3 ventanas seguidas."""
        ahora, tok = time.time(), TrainerRecortado.tokens_vistos
        if self.t_ventana is None:
            self.t_ventana, self.tok_ventana = ahora, tok
            return
        seg, dtok = ahora - self.t_ventana, tok - self.tok_ventana
        self.t_ventana, self.tok_ventana = ahora, tok
        perd = [h["loss"] for h in state.log_history if "loss" in h][-10:]
        por_1000 = seg / (dtok / 1000) if dtok else 0.0
        self.ventanas.append(por_1000)
        aviso = ""
        if len(self.ventanas) > 5:
            base = statistics.median(self.ventanas[:5])
            self.duplicados = self.duplicados + 1 if por_1000 > 2 * base else 0
            if self.duplicados >= 3:
                aviso = f"TIEMPO DUPLICADO sostenido: {por_1000:.1f} s/1000 tok frente a {base:.1f} de base"
                print(aviso, flush=True)
        fila = {"step": state.global_step, "epoch": round(state.epoch, 3), "perdida_media_10": round(sum(perd) / len(perd), 5) if perd else "",
                "vram_reservada_mb": round(torch.cuda.memory_reserved() / 2**20, 1), "segundos_por_paso_media_10": round(seg / 10, 2),
                "tokens_por_s": round(dtok / seg, 1), "segundos_por_1000_tokens": round(por_1000, 2), **estado_gpu(), "aviso": aviso}
        if self.ruta_csv:
            with open(self.ruta_csv, "a", encoding="utf-8", newline="") as f:
                csv.writer(f).writerow([fila[c] for c in self.CAMPOS])
        print("MON", json.dumps(fila, ensure_ascii=False), flush=True)

    def on_step_begin(self, args, state, control, **kw):
        self.t_step = time.time()

    def on_step_end(self, args, state, control, **kw):
        seg = time.time() - self.t_step
        torch.cuda.empty_cache()  # libera la fragmentacion del asignador (la reservada llego a 6.576 MB con 5.050 MB asignados)
        res = torch.cuda.memory_reserved() / 2**20
        self.filas.append({"step": state.global_step, "epoch": round(state.epoch, 4), "segundos_step": round(seg, 3),
                           "vram_allocated_mb": round(torch.cuda.memory_allocated() / 2**20, 1), "vram_reserved_mb": round(res, 1),
                           "vram_pico_reserved_mb": round(torch.cuda.max_memory_reserved() / 2**20, 1)})
        if self.segundos_max and seg > self.segundos_max:
            self.motivo_parada = f"step {state.global_step} tardo {seg:.1f}s (> {self.segundos_max}s): presion de VRAM"
        elif res > self.limite_vram_mb:
            self.motivo_parada = f"VRAM reservada {res:.0f} MB supera el limite de {self.limite_vram_mb} MB"
        elif self.max_pasos and state.global_step >= self.max_pasos:
            self.motivo_parada = f"max-pasos={self.max_pasos} alcanzado (prueba de humo, no es una parada por problema)"
        if state.global_step % 10 == 0:
            self._ventana(state)
        if self.motivo_parada:
            control.should_training_stop = True


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dataset", required=True)
    ap.add_argument("--salida", required=True)
    ap.add_argument("--humo", action="store_true", help="20 pasos con el ejemplo mas largo repetido; no guarda adaptador")
    ap.add_argument("--excluir", help="archivo con un id por linea: esos ejemplos no se entrenan (se registra su sha256)")
    ap.add_argument("--guardar-cada", type=int, default=200)
    ap.add_argument("--reanudar", action="store_true", help="reanuda desde el ultimo checkpoint de <salida>/checkpoints")
    ap.add_argument("--equivalencia", action="store_true", help="demuestra perdida recortada == perdida estandar en 5 ejemplos y termina")
    ap.add_argument("--limite-vram-mb", type=int, default=5900)
    ap.add_argument("--segundos-max-step", type=float, default=120.0, help="0 = sin limite")
    args = ap.parse_args()

    t0 = time.time()
    sha = sha256_archivo(args.dataset)
    assert sha == SHA256_DATASET, f"sha256 del dataset distinto del esperado: {sha}"
    print(f"dataset sha256 OK: {sha}")
    tokenizer = AutoTokenizer.from_pretrained(MODELO)
    tokenizer.pad_token = tokenizer.pad_token or tokenizer.eos_token
    items = cargar_tokenizado(args.dataset)
    excluidos = {}
    if args.excluir:
        ids_fuera = {l.strip() for l in open(args.excluir, encoding="utf-8") if l.strip()}
        desconocidos = ids_fuera - {x["id"] for x in items}
        assert not desconocidos, f"--excluir trae ids que no estan en el dataset: {sorted(desconocidos)[:5]}"
        excluidos = {"archivo": os.path.basename(args.excluir), "sha256": sha256_archivo(args.excluir), "n": len(ids_fuera)}
        items = [x for x in items if x["id"] not in ids_fuera]
        print(f"--excluir: {len(ids_fuera)} ejemplos fuera ({excluidos['sha256'][:12]}...), quedan {len(items)}")
    ds = DatasetSFT(items)
    mas_largo = max(items, key=lambda x: len(x["input_ids"]))
    print(f"{len(ds)} ejemplos; tokens max {len(mas_largo['input_ids'])} ({mas_largo['id']}); max_length={MAX_LENGTH} sin truncar; verificacion del enmascarado:")
    verificar_enmascarado(ds, tokenizer)
    if args.humo:
        ds = DatasetSFT([mas_largo] * (PASOS_HUMO * ACUMULACION))
        print(f"PRUEBA DE HUMO: {len(ds)} copias de {mas_largo['id']} ({len(mas_largo['input_ids'])} tokens), {PASOS_HUMO} pasos")

    torch.manual_seed(SEMILLA)
    bnb = BitsAndBytesConfig(load_in_4bit=True, bnb_4bit_quant_type="nf4", bnb_4bit_compute_dtype=torch.bfloat16)
    model = AutoModelForCausalLM.from_pretrained(MODELO, quantization_config=bnb, device_map={"": 0}, dtype=torch.bfloat16)
    model.config.use_cache = False
    model = prepare_model_for_kbit_training(model, use_gradient_checkpointing=True, gradient_checkpointing_kwargs={"use_reentrant": False})
    lora = LoraConfig(r=16, lora_alpha=32, lora_dropout=0.05, target_modules=CAPAS, bias="none", task_type="CAUSAL_LM")
    model = get_peft_model(model, lora)
    n_train = sum(p.numel() for p in model.parameters() if p.requires_grad)
    n_total = sum(p.numel() for p in model.parameters())
    print(f"parametros entrenables: {n_train:,} de {n_total:,} ({100 * n_train / n_total:.2f} %)")

    if args.equivalencia:
        os.makedirs(args.salida, exist_ok=True)
        print("EQUIVALENCIA perdida recortada vs estandar (eval, LoRA B aleatorio):")
        return 0 if demostrar_equivalencia(model, items, os.path.join(args.salida, "equivalencia_perdida.json")) else 1

    targs = TrainingArguments(
        output_dir=os.path.join(args.salida, "checkpoints"), per_device_train_batch_size=1, gradient_accumulation_steps=ACUMULACION,
        num_train_epochs=EPOCAS, learning_rate=LR, lr_scheduler_type="linear", warmup_steps=0, optim="paged_adamw_8bit",
        bf16=True, logging_steps=1, save_strategy="no" if args.humo else "steps", save_steps=args.guardar_cada, save_total_limit=2, report_to="none", seed=SEMILLA, remove_unused_columns=False,
        gradient_checkpointing=True, gradient_checkpointing_kwargs={"use_reentrant": False}, dataloader_num_workers=0,
        max_steps=PASOS_HUMO if args.humo else -1,
    )
    os.makedirs(args.salida, exist_ok=True)
    monitor = Monitor(PASOS_HUMO if args.humo else 0, args.limite_vram_mb, args.segundos_max_step,
                      None if args.humo else os.path.join(args.salida, "monitoreo_cada_10_pasos.csv"))
    trainer = TrainerRecortado(model=model, args=targs, train_dataset=ds, data_collator=lambda l: collator(l, tokenizer.pad_token_id), callbacks=[monitor] + ([] if args.humo else [GuardarFinDeEpoca()]))
    torch.cuda.reset_peak_memory_stats()
    t_ent = time.time()
    trainer.train(resume_from_checkpoint=True if args.reanudar else None)
    seg = time.time() - t_ent

    hist = trainer.state.log_history
    losses = [h["loss"] for h in hist if "loss" in h]
    versiones = {"python": sys.version.split()[0], "torch": torch.__version__, "cuda": torch.version.cuda, "gpu": torch.cuda.get_device_name(0),
                 "transformers": __import__("transformers").__version__, "peft": __import__("peft").__version__,
                 "bitsandbytes": __import__("bitsandbytes").__version__, "accelerate": __import__("accelerate").__version__}
    log = {
        "prueba_de_humo": args.humo, "tiempo_total_segundos": round(seg, 1), "tiempo_total_minutos": round(seg / 60, 2),
        "vram_pico_reserved_mb": round(torch.cuda.max_memory_reserved() / 2**20, 1), "vram_pico_allocated_mb": round(torch.cuda.max_memory_allocated() / 2**20, 1),
        "loss_inicial": losses[0] if losses else None, "loss_final": losses[-1] if losses else None,
        "num_ejemplos": len(ds), "num_epocas": EPOCAS, "learning_rate": LR, "max_length": MAX_LENGTH, "micro_batch": 1, "acumulacion": ACUMULACION,
        "perdida": "recortada (lm_head solo en labels != -100)", "dataset": os.path.basename(args.dataset), "dataset_sha256": sha, "excluidos": excluidos, "semilla": SEMILLA, "parametros_entrenables": n_train,
        "motivo_parada": monitor.motivo_parada, "steps_completados": trainer.state.global_step, "versiones": versiones,
        "log_history": hist, "monitor_recursos": monitor.filas,
    }
    os.makedirs(args.salida, exist_ok=True)
    with open(os.path.join(args.salida, "entrenamiento_log.json"), "w", encoding="utf-8") as f:
        json.dump(log, f, ensure_ascii=False, indent=1)
    with open(os.path.join(args.salida, "perdida_por_paso.csv"), "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["step", "epoch", "loss", "grad_norm", "learning_rate"])
        for h in hist:
            if "loss" in h:
                w.writerow([h["step"], h.get("epoch"), h["loss"], h.get("grad_norm"), h.get("learning_rate")])
    if not args.humo and monitor.motivo_parada is None:
        model.save_pretrained(args.salida)
        tokenizer.save_pretrained(args.salida)
    print(f"\nterminado en {(time.time() - t0) / 60:.1f} min | steps {trainer.state.global_step} | loss {log['loss_inicial']:.4f} -> {log['loss_final']:.4f} | "
          f"VRAM pico reservada {log['vram_pico_reserved_mb']} MB / asignada {log['vram_pico_allocated_mb']} MB | parada: {monitor.motivo_parada}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
