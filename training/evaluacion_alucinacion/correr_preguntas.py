"""
Corre las 100 preguntas de conocimiento general contra el chatbot POR EL
SERVICIO REAL (POST /chatbot/send de app/main.py), no llamando a Ollama
directo: asi la prueba incluye el system prompt y el flujo que veria un
usuario.

Uso:
    python correr_preguntas.py <url_servicio> <etiqueta_version> <salida.json>
"""
import json
import sys
import time

import httpx

sys.path.insert(0, ".")
from preguntas_generales import PREGUNTAS

URL = sys.argv[1]
VERSION = sys.argv[2]
SALIDA = sys.argv[3]

resultados = []
t0 = time.time()
with httpx.Client(timeout=300.0) as c:
    for i, (categoria, pregunta, referencia, confianza) in enumerate(PREGUNTAS, 1):
        inicio = time.time()
        try:
            r = c.post(f"{URL}/chatbot/send", json={"message": pregunta})
            r.raise_for_status()
            respuesta = r.json()["response"]
            error = None
        except Exception as exc:
            respuesta, error = "", f"{type(exc).__name__}: {exc}"
        dur = time.time() - inicio
        resultados.append({
            "n": i, "categoria": categoria, "pregunta": pregunta,
            "referencia": referencia, "confianza_evaluador": confianza,
            "respuesta": respuesta, "error": error, "segundos": round(dur, 1),
        })
        print(f"[{VERSION}] {i:3}/100 ({categoria:<12}) {dur:5.1f}s  {pregunta[:52]}")
        sys.stdout.flush()
        with open(SALIDA, "w", encoding="utf-8") as fh:
            json.dump({"version": VERSION, "url": URL, "resultados": resultados}, fh,
                      ensure_ascii=False, indent=1)

fallos = sum(1 for r in resultados if r["error"])
print(f"\n[{VERSION}] terminado en {(time.time()-t0)/60:.1f} min. "
      f"{len(resultados)} respuestas, {fallos} con error. Guardado en {SALIDA}")
