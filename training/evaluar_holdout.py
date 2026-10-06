"""T-93: genera respuestas del modelo base y del modelo fine-tuneado
(T-92) sobre los 18 pares de dataset/holdout.jsonl, nunca vistos en
entrenamiento -- guarda las generaciones crudas para su evaluacion
posterior (metrica automatica ROUGE-L + rubrica manual, ver
training/README.md seccion T-93).

No modifica el modelo ni reentrena -- solo inferencia + guardado.

NOTA sobre el "modelo de referencia externo" pedido en la tarea: este
entorno no tiene ninguna API key de Anthropic/Claude ni de otro proveedor
configurada (verificado -- no hay ANTHROPIC_API_KEY ni similar en el
entorno ni en .env). Por instruccion explicita de la tarea ("si no hay
acceso disponible, saltalo y dilo explicitamente en vez de improvisar
una alternativa"), este script SOLO genera con los 2 modelos locales
(base y fine-tuneado) -- no hay tercer modelo de referencia en T-93.

Uso:
    python training/evaluar_holdout.py
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
ADAPTER_PATH = Path(__file__).resolve().parent / "adapters" / "techo360-v1"
SALIDA = Path(__file__).resolve().parent / "eval_holdout_generaciones.json"

FECHA_FIJA_TEMPLATE = "18 Sep 2026"  # misma fecha fija que T-70, por consistencia

# Mismo system prompt fijado en T-70 -- para que la comparacion entre
# base y fine-tuneado sea justa (ambos ven exactamente el mismo contexto
# de sistema; solo cambia si el adaptador LoRA esta activo o no).
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
            do_sample=False,  # greedy, deterministico -- comparacion reproducible entre corridas
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

    print(f"Cargando adaptadores LoRA de {ADAPTER_PATH}...")
    modelo_ft = PeftModel.from_pretrained(modelo_base, str(ADAPTER_PATH))
    modelo_ft.eval()

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

        # Modelo base: adaptador LoRA desactivado temporalmente -- mismo
        # objeto en memoria, sin recargar pesos, via el context manager
        # de peft.
        with modelo_ft.disable_adapter():
            resp_base, t_base = generar(modelo_ft, tokenizer, pregunta)
        print(f"  base ({t_base:.1f}s): {resp_base[:80]}...")

        # Modelo fine-tuneado: adaptador activo (estado default de PeftModel)
        resp_ft, t_ft = generar(modelo_ft, tokenizer, pregunta)
        print(f"  fine-tuneado ({t_ft:.1f}s): {resp_ft[:80]}...")

        resultados.append({
            "indice": i,
            "categoria": categoria,
            "source_original": par.get("source"),
            "instruction": pregunta,
            "referencia_holdout": referencia,
            "respuesta_base": resp_base,
            "respuesta_finetuneado": resp_ft,
            "tiempo_base_s": round(t_base, 2),
            "tiempo_finetuneado_s": round(t_ft, 2),
        })

    with SALIDA.open("w", encoding="utf-8") as f:
        json.dump(resultados, f, ensure_ascii=False, indent=2)

    print(f"\nGeneraciones guardadas en {SALIDA}")


if __name__ == "__main__":
    main()
