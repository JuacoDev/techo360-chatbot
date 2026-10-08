"""Corre las 100 preguntas fuera de dominio, 3 corridas por modelo, a traves del servicio real (T-124).

Para cada modelo de Ollama levanta training/servicio_eval_sin_rabbitmq.py con OLLAMA_MODEL=<tag> y ejecuta evaluacion_alucinacion/correr_preguntas.py
(el mismo script de v3.2, sin cambios) una vez por corrida. Las respuestas quedan en <salida>/respuestas_<ETIQUETA>_c<k>.json.

Uso: python training/evaluar_100_muestreo.py --modelo A=techo360-chatbot:v3.2 --modelo B=techo360-chatbot:v3.3 --salida training/t124 [--corridas 3]
Es reanudable: salta las corridas cuyo archivo ya tiene 100 respuestas sin error.
"""
import argparse
import json
import os
import subprocess
import sys
import time

import httpx

AQUI = os.path.dirname(os.path.abspath(__file__))
EVAL = os.path.join(AQUI, "evaluacion_alucinacion")


def completa(ruta: str) -> bool:
    try:
        r = json.load(open(ruta, encoding="utf-8"))["resultados"]
        return len(r) == 100 and not any(x["error"] for x in r)
    except Exception:  # noqa: BLE001
        return False


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--modelo", action="append", required=True)
    ap.add_argument("--salida", required=True)
    ap.add_argument("--corridas", type=int, default=3)
    ap.add_argument("--puerto", type=int, default=8765)
    args = ap.parse_args()
    os.makedirs(args.salida, exist_ok=True)
    for par in args.modelo:
        etiqueta, tag = par.split("=", 1)
        pendientes = [k for k in range(1, args.corridas + 1) if not completa(os.path.join(args.salida, f"respuestas_{etiqueta}_c{k}.json"))]
        if not pendientes:
            continue
        env = dict(os.environ, OLLAMA_MODEL=tag, PYTHONIOENCODING="utf-8")
        servicio = subprocess.Popen([sys.executable, os.path.join(AQUI, "servicio_eval_sin_rabbitmq.py"), str(args.puerto)], env=env)
        try:
            for _ in range(60):
                try:
                    if httpx.get(f"http://127.0.0.1:{args.puerto}/health", timeout=2).status_code == 200:
                        break
                except httpx.HTTPError:
                    time.sleep(1)
            else:
                raise RuntimeError("el servicio no arranco")
            for k in pendientes:
                salida = os.path.abspath(os.path.join(args.salida, f"respuestas_{etiqueta}_c{k}.json"))
                print(f"=== modelo {etiqueta} ({tag}) corrida {k} ===", flush=True)
                subprocess.run([sys.executable, "-u", "correr_preguntas.py", f"http://127.0.0.1:{args.puerto}", f"{etiqueta}_c{k}", salida], cwd=EVAL, check=True, env=env)
        finally:
            servicio.terminate()
            servicio.wait(timeout=30)
    return 0


if __name__ == "__main__":
    sys.exit(main())
