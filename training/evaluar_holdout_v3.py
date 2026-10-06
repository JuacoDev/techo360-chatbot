"""T-93 (tercera corrida): genera respuestas del modelo base, v1 (T-92
original), v2 (610 pares, retrocedio) y v3 (592 pares, solo repos
aislados de cobertura, tras corregir la nomenclatura de los 8 pares
viejos de repos) sobre los 18 pares de dataset/holdout.jsonl -- el
mismo holdout, sin tocar.

Carga el modelo base UNA sola vez y adjunta los tres adaptadores como
adaptadores nombrados de PEFT, alternando con set_adapter() /
disable_adapter() -- evita cargar el modelo de 3B cuatro veces.

No modifica el modelo ni reentrena -- solo inferencia + guardado.

Uso:
    python training/evaluar_holdout_v3.py
"""

import json
import time
from pathlib import Path

import torch
from peft import PeftModel
from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig

MODEL_ID = "meta-llama/Llama-3.2-3B-Instruct"
RAIZ = Path(__file__).resolve().parent.parent
HOLDOUT_PATH = RAIZ / "dataset" / "holdout.jsonl"
DIR_TRAINING = Path(__file__).resolve().parent
ADAPTER_V1 = DIR_TRAINING / "adapters" / "techo360-v1"
ADAPTER_V2 = DIR_TRAINING / "adapters" / "techo360-v2"
ADAPTER_V3 = DIR_TRAINING / "adapters" / "techo360-v3"
SALIDA = DIR_TRAINING / "eval_holdout_generaciones_v3.json"

FECHA_FIJA_TEMPLATE = "18 Sep 2026"

SYSTEM_PROMPT = (
    "Eres el asistente virtual de Techo 360, una plataforma que analiza la "
    "pobreza y el deficit de vivienda en los municipios de Colombia. "
    "Respondes en espanol de forma clara y precisa sobre el Score de "
    "Privacion y los indicadores de Techo 360, y sobre la politica publica "
    "colombiana de vivienda y pobreza (IPM, deficit habitacional, cobertura "
    "de acueducto y alcantarillado) en la que se basa el sistema."
)

MAX_NEW_TOKENS = 350


def cargar_holdout():
    with HOLDOUT_PATH.open("r", encoding="utf-8") as f:
        return [json.loads(l) for l in f if l.strip()]


def generar(modelo, tokenizer, pregunta):
    mensajes = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": pregunta},
    ]
    texto_prompt = tokenizer.apply_chat_template(
        mensajes,
        tokenize=False,
        add_generation_prompt=True,
        date_string=FECHA_FIJA_TEMPLATE,
    )
    inputs = tokenizer(texto_prompt, return_tensors="pt", add_special_tokens=False).to(modelo.device)

    t0 = time.time()
    with torch.no_grad():
        salida = modelo.generate(
            **inputs,
            max_new_tokens=MAX_NEW_TOKENS,
            do_sample=False,
            temperature=None,
            top_p=None,
            pad_token_id=tokenizer.pad_token_id,
        )
    dt = time.time() - t0

    tokens_generados = salida[0][inputs["input_ids"].shape[1]:]
    respuesta = tokenizer.decode(tokens_generados, skip_special_tokens=True)
    return respuesta.strip(), dt


def main():
    print(f"Cargando tokenizer y modelo base {MODEL_ID} en 4-bit...")
    tokenizer = AutoTokenizer.from_pretrained(MODEL_ID)
    tokenizer.pad_token = "<|finetune_right_pad_id|>"

    bnb_config = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_quant_type="nf4",
        bnb_4bit_compute_dtype=torch.bfloat16,
    )
    modelo_base = AutoModelForCausalLM.from_pretrained(
        MODEL_ID,
        quantization_config=bnb_config,
        device_map={"": 0},
    )
    modelo_base.eval()

    print(f"Cargando adaptador v1 de {ADAPTER_V1}...")
    modelo = PeftModel.from_pretrained(modelo_base, str(ADAPTER_V1), adapter_name="v1")
    print(f"Cargando adaptador v2 de {ADAPTER_V2}...")
    modelo.load_adapter(str(ADAPTER_V2), adapter_name="v2")
    print(f"Cargando adaptador v3 de {ADAPTER_V3}...")
    modelo.load_adapter(str(ADAPTER_V3), adapter_name="v3")
    modelo.eval()

    holdout = cargar_holdout()
    print(f"{len(holdout)} pares de holdout cargados "
          f"({sum(1 for p in holdout if p.get('source'))} con fuente, "
          f"{sum(1 for p in holdout if not p.get('source'))} sin fuente)")

    resultados = []
    for i, par in enumerate(holdout):
        pregunta = par["instruction"]
        referencia = par["response"]
        categoria = "con_fuente" if par.get("source") else "sin_fuente"

        print(f"\n[{i+1}/{len(holdout)}] ({categoria}) {pregunta[:70]}...")

        with modelo.disable_adapter():
            resp_base, t_base = generar(modelo, tokenizer, pregunta)
        print(f"  base ({t_base:.1f}s): {resp_base[:80]}...")

        modelo.set_adapter("v1")
        resp_v1, t_v1 = generar(modelo, tokenizer, pregunta)
        print(f"  v1 ({t_v1:.1f}s): {resp_v1[:80]}...")

        modelo.set_adapter("v2")
        resp_v2, t_v2 = generar(modelo, tokenizer, pregunta)
        print(f"  v2 ({t_v2:.1f}s): {resp_v2[:80]}...")

        modelo.set_adapter("v3")
        resp_v3, t_v3 = generar(modelo, tokenizer, pregunta)
        print(f"  v3 ({t_v3:.1f}s): {resp_v3[:80]}...")

        resultados.append({
            "indice": i,
            "categoria": categoria,
            "source_original": par.get("source"),
            "instruction": pregunta,
            "referencia_holdout": referencia,
            "respuesta_base": resp_base,
            "respuesta_v1": resp_v1,
            "respuesta_v2": resp_v2,
            "respuesta_v3": resp_v3,
            "tiempo_base_s": round(t_base, 2),
            "tiempo_v1_s": round(t_v1, 2),
            "tiempo_v2_s": round(t_v2, 2),
            "tiempo_v3_s": round(t_v3, 2),
        })

    with SALIDA.open("w", encoding="utf-8") as f:
        json.dump(resultados, f, ensure_ascii=False, indent=2)

    print(f"\nGeneraciones guardadas en {SALIDA}")


if __name__ == "__main__":
    main()
