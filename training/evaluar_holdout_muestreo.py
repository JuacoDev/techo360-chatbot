"""Evaluacion del holdout con muestreo real (T-93 rehecha), RECONSTRUIDO en T-124 (el original se perdio).

Genera, para cada par del holdout y cada semilla, la respuesta de cada modelo de Ollama con el MISMO servicio que produccion:
la peticion es la de app/ollama_client.generar_respuesta (mismo system prompt, mismo NUM_PREDICT y NUM_THREAD, importados de app/ollama_client.py)
mas la semilla y los parametros de muestreo explicitos. Temperatura 0,3, top_p 0,9, repeat_penalty 1,15, num_ctx 2048 (los del Modelfile).

Uso (desde la raiz del repo; requiere httpx):
    python training/evaluar_holdout_muestreo.py --modelo A=techo360-chatbot:v3.2 --modelo B=techo360-chatbot:v3.3 --salida training/t124/generaciones_holdout.json
Es reanudable: si la salida ya existe, salta las generaciones hechas. Las etiquetas (A, B) son las que se usan en los archivos; el cegado se hace despues
con rubrica_manual_muestreo.py.
"""
import argparse
import json
import os
import sys
import time

import httpx

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RAIZ)
from app.ollama_client import NUM_PREDICT, NUM_THREAD, OLLAMA_URL, SYSTEM_PROMPT  # noqa: E402

PARAMETROS = {"temperature": 0.3, "top_p": 0.9, "repeat_penalty": 1.15, "num_ctx": 2048}


def generar(cliente: httpx.Client, tag: str, pregunta: str, semilla: int) -> dict:
    opciones = {"num_predict": NUM_PREDICT, "num_thread": NUM_THREAD, "seed": semilla, **PARAMETROS}
    t0 = time.time()
    r = cliente.post(f"{OLLAMA_URL}/api/chat", json={
        "model": tag, "stream": False, "options": opciones,
        "messages": [{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": pregunta}],
    })
    r.raise_for_status()
    d = r.json()
    return {"respuesta": d["message"]["content"], "eval_count": d.get("eval_count"), "done_reason": d.get("done_reason"), "segundos": round(time.time() - t0, 1)}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--modelo", action="append", required=True, help="ETIQUETA=tag_de_ollama (repetible)")
    ap.add_argument("--holdout", default=os.path.join(RAIZ, "dataset", "holdout_v3_3.jsonl"))
    ap.add_argument("--semillas", default="1,2,3,4,5")
    ap.add_argument("--salida", required=True)
    args = ap.parse_args()
    modelos = dict(m.split("=", 1) for m in args.modelo)
    semillas = [int(s) for s in args.semillas.split(",")]
    with open(args.holdout, encoding="utf-8", newline="") as f:
        pares = [json.loads(l) for l in f.read().split("\r\n") if l.strip()]

    previo = json.load(open(args.salida, encoding="utf-8")) if os.path.exists(args.salida) else {"parametros": PARAMETROS, "num_predict": NUM_PREDICT, "num_thread": NUM_THREAD, "modelos": modelos, "generaciones": []}
    hechas = {(g["modelo"], g["indice"], g["semilla"]) for g in previo["generaciones"]}
    total = len(modelos) * len(pares) * len(semillas)
    os.makedirs(os.path.dirname(os.path.abspath(args.salida)), exist_ok=True)
    t_ini = time.time()
    with httpx.Client(timeout=600.0) as cliente:
        for etiqueta, tag in modelos.items():
            for i, par in enumerate(pares, 1):
                for s in semillas:
                    if (etiqueta, i, s) in hechas:
                        continue
                    g = generar(cliente, tag, par["instruction"], s)
                    previo["generaciones"].append({"modelo": etiqueta, "tag": tag, "indice": i, "semilla": s, "pregunta": par["instruction"],
                                                   "referencia": par["response"], "con_fuente": bool(par.get("source")), **g})
                    with open(args.salida, "w", encoding="utf-8") as f:
                        json.dump(previo, f, ensure_ascii=False, indent=1)
                    print(f"[{etiqueta}] par {i:2}/{len(pares)} semilla {s}  {g['segundos']:5.1f}s  {len(previo['generaciones'])}/{total}  "
                          f"(transcurrido {(time.time() - t_ini) / 60:.1f} min)", flush=True)
    cortadas = sum(1 for g in previo["generaciones"] if g["done_reason"] == "length")
    print(f"listo: {len(previo['generaciones'])} generaciones; cortadas por longitud: {cortadas}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
