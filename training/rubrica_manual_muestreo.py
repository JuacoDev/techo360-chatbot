"""Cegado y resumen de la puntuacion manual de T-124, RECONSTRUIDO (el original se perdio). Quien PUNTUA es una IA (Claude), no una persona.

Flujo (el mismo para el holdout y para las 100 preguntas fuera de dominio):
  1. `preparar-holdout` / `preparar-100`: mezcla las respuestas de ambos modelos, les pone un id al azar sin etiqueta de modelo y escribe
     `ciego_*.json` (lo unico que ve quien puntua) y `clave_*.json` (id -> modelo, corrida o semilla; NO se abre hasta terminar de puntuar).
  2. quien puntua escribe `puntajes_*_v3_3.py` con un dict {id: puntaje}. Holdout: 1-5 segun training/rubrica_holdout_v3_3.json (criterios fijados antes de
     generar nada). 100 preguntas: C/I/A/N segun evaluacion_alucinacion/RUBRICA.md (M = confianza media, apartada, como en v3.2).
  3. `resumir-holdout` / `resumir-100`: abre la clave, une los puntajes y calcula ROUGE-L (metrica_rouge_l.rouge_l_f1, la de metrica_rouge_l_v3.py),
     rubrica media, regresiones y mejoras por par, y los porcentajes de las 100 preguntas por modelo, categoria y corrida.

Definiciones de la comparacion por par (holdout, 5 semillas): acierto = rubrica >= 4; fallo = rubrica <= 3 (no acierta); consistente = en >= 4 de las 5 corridas.
  regresion consistente = el modelo A acierta de forma consistente y el B falla de forma consistente; mejora consistente = al reves.
  Ademas se reportan los pares con diferencia de medias >= 1 punto como "tendencia" (no consistente).
"""
import argparse
import importlib.util
import json
import os
import random
import statistics
import string
import sys

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)
sys.path.insert(0, os.path.join(AQUI, "evaluacion_alucinacion"))
sys.stdout.reconfigure(encoding="utf-8")
SEMILLA_MEZCLA = 20261006
ETIQUETAS = {"C": "correcta", "I": "incorrecta", "A": "alucinacion", "N": "se_nego"}


def ids_unicos(n: int, rng: random.Random) -> list[str]:
    vistos: set[str] = set()
    while len(vistos) < n:
        vistos.add("".join(rng.choice(string.ascii_lowercase) for _ in range(5)))
    out = sorted(vistos)
    rng.shuffle(out)
    return out


def cargar_py(ruta: str) -> dict:
    spec = importlib.util.spec_from_file_location("puntajes", ruta)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m.PUNTAJES


def guardar(ruta: str, obj) -> None:
    with open(ruta, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=1)


# ------------------------------------------------------------------ holdout
def preparar_holdout(args) -> None:
    gens = json.load(open(args.generaciones, encoding="utf-8"))["generaciones"]
    rng = random.Random(SEMILLA_MEZCLA)
    ids = ids_unicos(len(gens), rng)
    orden = list(range(len(gens)))
    rng.shuffle(orden)
    clave, por_par = {}, {}
    for id_, k in zip(ids, orden):
        g = gens[k]
        clave[id_] = {"modelo": g["modelo"], "indice": g["indice"], "semilla": g["semilla"]}
        por_par.setdefault(g["indice"], []).append({"id": id_, "texto": g["respuesta"]})
    ciego = [{"indice": i, "pregunta": next(g["pregunta"] for g in gens if g["indice"] == i),
              "referencia": next(g["referencia"] for g in gens if g["indice"] == i), "respuestas": por_par[i]} for i in sorted(por_par)]
    guardar(args.ciego, ciego)
    guardar(args.clave, clave)
    print(f"{len(gens)} respuestas en {len(ciego)} pares -> {args.ciego} (la clave queda en {args.clave}: no abrir hasta puntuar)")


def resumir_holdout(args) -> None:
    from metrica_rouge_l import rouge_l_f1
    gens = json.load(open(args.generaciones, encoding="utf-8"))["generaciones"]
    clave = json.load(open(args.clave, encoding="utf-8"))
    punt = cargar_py(args.puntajes)
    faltan = [i for i in clave if i not in punt]
    assert not faltan, f"faltan {len(faltan)} puntajes: {faltan[:5]}"
    assert all(1 <= v <= 5 for v in punt.values()), "puntajes fuera de 1-5"
    por_id = {(c["modelo"], c["indice"], c["semilla"]): i for i, c in clave.items()}
    filas = []
    for g in gens:
        filas.append({**{k: g[k] for k in ("modelo", "indice", "semilla", "con_fuente")},
                      "rubrica": punt[por_id[(g["modelo"], g["indice"], g["semilla"])]],
                      "rouge_l": rouge_l_f1(g["respuesta"], g["referencia"]), "cortada": g["done_reason"] == "length"})
    modelos = sorted({f["modelo"] for f in filas})
    print(f"{'':14}" + "".join(f"{m:>16}" for m in modelos))
    for nombre, filtro in (("GENERAL", None), ("con fuente", True), ("sin fuente", False)):
        sel = lambda m: [f for f in filas if f["modelo"] == m and (filtro is None or f["con_fuente"] == filtro)]  # noqa: E731
        print(f"ROUGE-L {nombre:<7}" + "".join(f"{statistics.mean(f['rouge_l'] for f in sel(m)):>16.4f}" for m in modelos))
        print(f"rubrica {nombre:<7}" + "".join(f"{statistics.mean(f['rubrica'] for f in sel(m)):>16.3f}" for m in modelos))
    print("generaciones cortadas por longitud:", {m: sum(f["cortada"] for f in filas if f["modelo"] == m) for m in modelos})
    A, B = modelos[0], modelos[1]
    print(f"\npor par ({A} vs {B}): media de rubrica, aciertos (>=4) y fallos (<=3) sobre las corridas")
    reg, mej, tend = [], [], []
    for i in sorted({f["indice"] for f in filas}):
        d = {}
        for m in modelos:
            r = [f["rubrica"] for f in filas if f["modelo"] == m and f["indice"] == i]
            d[m] = {"media": statistics.mean(r), "aciertos": sum(x >= 4 for x in r), "fallos": sum(x <= 3 for x in r), "n": len(r), "r": r}
        cons_a, cons_b = d[A]["aciertos"] >= 4, d[B]["aciertos"] >= 4
        fallo_a, fallo_b = d[A]["fallos"] >= 4, d[B]["fallos"] >= 4
        marca = ""
        if cons_a and fallo_b:
            marca, _ = "REGRESION CONSISTENTE", reg.append(i)
        elif cons_b and fallo_a:
            marca, _ = "mejora consistente", mej.append(i)
        elif abs(d[B]["media"] - d[A]["media"]) >= 1.0:
            marca = "tendencia a " + ("favor de " + B if d[B]["media"] > d[A]["media"] else "favor de " + A)
            tend.append((i, marca))
        print(f"  par {i:2}  {A}: {d[A]['media']:.1f} {d[A]['r']}  {B}: {d[B]['media']:.1f} {d[B]['r']}  {marca}")
    print(f"\nregresiones consistentes ({A} acierta >=4/5 y {B} falla >=4/5): {reg}\nmejoras consistentes: {mej}\ntendencias: {tend}")
    guardar(args.salida, {"modelos": modelos, "por_generacion": filas, "regresiones_consistentes": reg, "mejoras_consistentes": mej})
    print("detalle en", args.salida)


# --------------------------------------------------------------------- 100
def preparar_100(args) -> None:
    from preguntas_generales import PREGUNTAS
    rng = random.Random(SEMILLA_MEZCLA + 1)
    tablas = {}
    for ruta in args.respuestas:
        base = os.path.basename(ruta)[len("respuestas_"):-len(".json")]   # p. ej. A_c1
        modelo, corrida = base.rsplit("_c", 1)
        for r in json.load(open(ruta, encoding="utf-8"))["resultados"]:
            tablas.setdefault(r["n"], []).append({"modelo": modelo, "corrida": int(corrida), "texto": r["respuesta"], "error": r["error"]})
    total = sum(len(v) for v in tablas.values())
    ids = ids_unicos(total, rng)
    clave, ciego = {}, []
    k = 0
    for n in sorted(tablas):
        cat, preg, ref, conf = PREGUNTAS[n - 1]
        resp = tablas[n][:]
        rng.shuffle(resp)
        items = []
        for r in resp:
            id_ = ids[k]; k += 1
            clave[id_] = {"modelo": r["modelo"], "corrida": r["corrida"], "n": n}
            items.append({"id": id_, "texto": r["texto"] if not r["error"] else f"[ERROR DE GENERACION: {r['error']}]"})
        ciego.append({"n": n, "categoria": cat, "pregunta": preg, "referencia": ref, "confianza_evaluador": conf, "respuestas": items})
    guardar(args.ciego, ciego)
    guardar(args.clave, clave)
    print(f"{total} respuestas ({len(tablas)} preguntas) -> {args.ciego} (clave en {args.clave}: no abrir hasta puntuar)")


def resumir_100(args) -> None:
    from preguntas_generales import PREGUNTAS
    clave = json.load(open(args.clave, encoding="utf-8"))
    punt = cargar_py(args.puntajes)
    faltan = [i for i in clave if i not in punt]
    assert not faltan, f"faltan {len(faltan)} puntajes: {faltan[:5]}"
    assert all(v in set(ETIQUETAS) | {"M"} for v in punt.values())
    cat_de = {i + 1: c for i, (c, *_r) in enumerate(PREGUNTAS)}
    media_de = {i + 1 for i, (_c, _q, _r, conf) in enumerate(PREGUNTAS) if conf != "alta"}
    por_modelo: dict = {}
    for id_, c in clave.items():
        p = "M" if c["n"] in media_de else punt[id_]   # las de confianza media quedan apartadas siempre, como en v3.2
        por_modelo.setdefault(c["modelo"], []).append((c["n"], c["corrida"], p))
    resumen = {}
    for m, lst in sorted(por_modelo.items()):
        punt_l = [x for x in lst if x[2] != "M"]
        tot = len(punt_l)
        cnt = {k: sum(1 for x in punt_l if x[2] == k) for k in ETIQUETAS}
        print(f"\n{'=' * 66}\nMODELO {m}: {tot} respuestas puntuables ({len(lst) - tot} apartadas por confianza media; {len(set(x[1] for x in lst))} corridas)\n{'=' * 66}")
        for k, nombre in ETIQUETAS.items():
            print(f"  {nombre:<14}{cnt[k]:>5}   {100 * cnt[k] / tot:>5.1f}%")
        print(f"  ALUCINACION GLOBAL: {100 * cnt['A'] / tot:.1f}% ({cnt['A']}/{tot})   por corrida: " +
              ", ".join(f"c{c}={sum(1 for x in punt_l if x[1] == c and x[2] == 'A')}A/{sum(1 for x in punt_l if x[1] == c and x[2] == 'C')}C" for c in sorted(set(x[1] for x in lst))))
        cats = {}
        for n, c, p in punt_l:
            cats.setdefault(cat_de[n], []).append(p)
        print(f"  {'categoria':<13}{'n':>5}{'%aluc':>8}{'%corr':>8}")
        for cat, ps in sorted(cats.items()):
            print(f"  {cat:<13}{len(ps):>5}{100 * ps.count('A') / len(ps):>8.1f}{100 * ps.count('C') / len(ps):>8.1f}")
        sal = cats.get("salud", [])
        print(f"  SALUD aparte: {len(sal)} respuestas; correcta {sal.count('C')}, incorrecta {sal.count('I')}, alucinacion {sal.count('A')}, se nego {sal.count('N')}")
        resumen[m] = {"puntuables": tot, **{ETIQUETAS[k]: cnt[k] for k in ETIQUETAS}, "salud": {k: sal.count(k) for k in "CIAN"}}
    guardar(args.salida, {"resumen": resumen, "por_respuesta": {m: v for m, v in por_modelo.items()}})
    print("\ndetalle en", args.salida)


def main() -> int:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("preparar-holdout"); p.add_argument("--generaciones", required=True); p.add_argument("--ciego", required=True); p.add_argument("--clave", required=True); p.set_defaults(f=preparar_holdout)
    p = sub.add_parser("resumir-holdout"); p.add_argument("--generaciones", required=True); p.add_argument("--clave", required=True); p.add_argument("--puntajes", required=True); p.add_argument("--salida", required=True); p.set_defaults(f=resumir_holdout)
    p = sub.add_parser("preparar-100"); p.add_argument("--respuestas", nargs="+", required=True); p.add_argument("--ciego", required=True); p.add_argument("--clave", required=True); p.set_defaults(f=preparar_100)
    p = sub.add_parser("resumir-100"); p.add_argument("--clave", required=True); p.add_argument("--puntajes", required=True); p.add_argument("--salida", required=True); p.set_defaults(f=resumir_100)
    args = ap.parse_args()
    args.f(args)
    return 0


if __name__ == "__main__":
    sys.exit(main())
