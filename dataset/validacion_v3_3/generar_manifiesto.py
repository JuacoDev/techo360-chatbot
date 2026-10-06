"""Genera manifiesto_pares_nuevos.csv: una fila por cada par NUEVO de v3.3 (entrenamiento y holdout), con su linea, categoria,
`source` y los anclajes (archivo y linea de codigo en los repositorios hermanos, y fuentes externas con la forma de verificacion).

Uso (desde la raiz del repo, con los repos techo360-* clonados como hermanos de este):
    python dataset/validacion_v3_3/generar_manifiesto.py

Lee anclas_pares_nuevos.py, busca cada texto en `git show origin/development:<ruta>` del repo correspondiente y registra el SHA usado.
Sale con codigo 1 si un par nuevo no tiene entrada, si un texto de codigo no se encuentra, o si la presencia de `source` no
coincide con la categoria ((a) y (c) llevan source; (b) no).
"""
import csv
import io
import json
import os
import subprocess
import sys
from collections import Counter

AQUI = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.dirname(os.path.dirname(AQUI))
sys.path.insert(0, AQUI)
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

from anclas_pares_nuevos import ANCLAS  # noqa: E402

REF = "origin/development"
HERMANOS = os.path.dirname(RAIZ)
TEMA_POR_ARCHIVO_LINEA = {}


def leer(nombre: str) -> list[dict]:
    with open(os.path.join(RAIZ, "dataset", nombre), encoding="utf-8", newline="") as f:
        return [json.loads(l) for l in f.read().split("\r\n") if l.strip()]


def git(repo: str, *args: str) -> str:
    r = subprocess.run(["git", "-C", os.path.join(HERMANOS, "techo360-" + repo), *args], capture_output=True, text=True, encoding="utf-8")
    if r.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)} en techo360-{repo}: {r.stderr.strip()}")
    return r.stdout


def linea_de(repo: str, ruta: str, texto: str) -> int:
    contenido = git(repo, "show", f"{REF}:{ruta}")
    for n, linea in enumerate(contenido.splitlines(), 1):
        if texto in linea:
            return n
    raise LookupError(f"techo360-{repo}:{ruta}: no aparece {texto!r}")


def tema_de(par: dict, entrada: dict) -> str:
    q = par["instruction"]
    return entrada.get("tema") or ""


def main() -> int:
    n_v32 = len(leer("entrenamiento_v3_2.jsonl"))
    n_h32 = len(leer("holdout.jsonl"))
    tr, ho = leer("entrenamiento_v3_3.jsonl"), leer("holdout_v3_3.jsonl")
    nuevos = [("entrenamiento_v3_3.jsonl", i + 1, "train", tr[i]) for i in range(n_v32, len(tr))] + \
             [("holdout_v3_3.jsonl", i + 1, "holdout", ho[i]) for i in range(n_h32, len(ho))]
    shas = {r: git(r, "rev-parse", "--short", REF).strip() for r in ("backend", "chatbot", "proyeccion", "frontend", "infra", "workers")}
    print("SHA usados (origin/development):", shas)

    problemas, filas = [], []
    for archivo, linea, split, par in nuevos:
        coincide = [e for e in ANCLAS if par["instruction"].startswith(e["pregunta"])]
        if len(coincide) != 1:
            problemas.append(f"{archivo}:{linea}: {len(coincide)} entradas de anclaje para {par['instruction'][:60]!r}")
            continue
        e = coincide[0]
        anclas = []
        for repo, ruta, texto in e.get("codigo", []):
            try:
                anclas.append(f"techo360-{repo}@{shas[repo]}:{ruta}:{linea_de(repo, ruta, texto)}")
            except (LookupError, RuntimeError) as exc:
                problemas.append(f"{archivo}:{linea}: {exc}")
        externas = [f"{d} <{u}> [{v}]" for d, u, v in e.get("externa", [])]
        lleva_source = bool(par.get("source"))
        if (e["cat"] in ("a", "c")) != lleva_source:
            problemas.append(f"{archivo}:{linea}: categoria ({e['cat']}) no coincide con la presencia de source ({lleva_source})")
        if not anclas and not externas:
            problemas.append(f"{archivo}:{linea}: sin ningun anclaje")
        filas.append({
            "archivo": archivo, "linea": linea, "split": split, "categoria": e["cat"],
            "lleva_source": "si" if lleva_source else "no", "source": par.get("source", ""),
            "ancla_codigo": " | ".join(anclas), "fuente_externa_y_verificacion": " | ".join(externas),
            "pregunta": par["instruction"],
        })

    sin_par = [e["pregunta"] for e in ANCLAS if not any(p["instruction"].startswith(e["pregunta"]) for _, _, _, p in nuevos)]
    problemas += [f"entrada de anclaje sin par nuevo: {q[:60]!r}" for q in sin_par]

    destino = os.path.join(AQUI, "manifiesto_pares_nuevos.csv")
    with open(destino, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(filas[0]) if filas else [], lineterminator="\r\n")
        w.writeheader()
        w.writerows(filas)
    c = Counter((f["split"], f["categoria"], f["lleva_source"]) for f in filas)
    print(f"{len(filas)} filas escritas en {os.path.relpath(destino, RAIZ)}")
    for (split, cat, src), n in sorted(c.items()):
        print(f"  {split:8} categoria ({cat}) source={src}: {n}")
    print(f"PROBLEMAS: {len(problemas)}")
    for p in problemas:
        print("  -", p)
    return 1 if problemas else 0


if __name__ == "__main__":
    sys.exit(main())
