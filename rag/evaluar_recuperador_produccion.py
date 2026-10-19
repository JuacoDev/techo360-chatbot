"""Evalua el recuperador DE PRODUCCION (backend: services/orquestador/rag.py -> buscar_fragmentos, texto de
Postgres con ts_rank) y el enrutador de intencion sobre un conjunto de preguntas con fragmento esperado.

A diferencia de evaluar_recuperacion.py (6.5), que reimplementa las consultas, este script importa el codigo
del backend, asi que mide lo que correra en produccion. Solo LEE; la base debe ser LOCAL.

    RAG_DATABASE_URL=postgresql://...@127.0.0.1:55434/techo360_vector_test \\
    python rag/evaluar_recuperador_produccion.py --backend ../techo360-backend-wt-c3 \\
        --preguntas ../claude/fase6-4-preguntas.jsonl rag/preguntas_ciegas_6_7b.jsonl \\
        --excluir rag-38 rag-39 [--csv fallos.csv] [--json resumen.json]

Python: el venv del backend (SQLAlchemy y psycopg). `--excluir` saca ids del calculo (en 6.5 se quitaron rag-38 y
rag-39 porque su fragmento esperado, 06-reglas-asistente, se retiro del corpus).
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import sys
from pathlib import Path
from urllib.parse import urlparse

AQUI = Path(__file__).resolve().parent
K = 5


def es_esperado(fragmento_id: str, esperados: list[str]) -> bool:
    return any(fragmento_id == e or fragmento_id.startswith(e + "-") for e in esperados)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--backend", type=Path, required=True, help="carpeta del backend (worktree de testing)")
    ap.add_argument("--preguntas", type=Path, nargs="+", required=True)
    ap.add_argument("--excluir", nargs="*", default=[])
    ap.add_argument("--etiqueta", default="")
    ap.add_argument("--csv", type=Path)
    ap.add_argument("--json", type=Path)
    a = ap.parse_args()
    dsn = os.environ.get("RAG_DATABASE_URL") or sys.exit("Falta RAG_DATABASE_URL (base LOCAL).")
    if (urlparse(dsn).hostname or "") not in ("localhost", "127.0.0.1", "::1"):
        sys.exit("Rechazado: solo bases LOCALES.")

    a.preguntas = [p.resolve() for p in a.preguntas]  # antes del chdir al backend
    a.csv = a.csv.resolve() if a.csv else None
    a.json = a.json.resolve() if a.json else None
    backend = a.backend.resolve()
    sys.path.insert(0, str(backend))
    os.chdir(backend)
    from sqlalchemy import create_engine, text
    from sqlalchemy.orm import Session
    from services.orquestador import resolutor as rs
    from services.orquestador.intencion import intencion_conceptual
    from services.orquestador.rag import buscar_fragmentos
    from services.tests_orquestador import CAT, HOY

    engine = create_engine(dsn.replace("postgresql://", "postgresql+psycopg://", 1))
    preguntas = []
    for ruta in a.preguntas:
        preguntas += [json.loads(l) for l in ruta.read_text(encoding="utf-8").splitlines() if l.strip()]
    conc = [p for p in preguntas if p["tipo"] == "conceptual" and p["id"] not in a.excluir]
    neg = [p for p in preguntas if p["tipo"] == "negativa"]

    def enruta(texto: str) -> bool:
        return intencion_conceptual(texto, rs.resolver(texto, CAT, HOY))

    filas, rangos = [], {}
    with Session(engine) as ses:
        ses.execute(text("SET TRANSACTION READ ONLY"))
        activos = {f for (f,) in ses.execute(text("SELECT fragmento_id FROM rag_fragmentos WHERE activo"))}
        faltan = sorted({e for p in conc for e in p["fragmentos_esperados"]
                         if not any(es_esperado(f, [e]) for f in activos)})
        for p in conc:
            top = [f["fragmento_id"] for f in buscar_fragmentos(ses, p["pregunta"], k=K)]
            r = next((i for i, f in enumerate(top, 1) if es_esperado(f, p["fragmentos_esperados"])), 0)
            rangos[p["id"]] = r
            filas.append([p["id"], p["pregunta"], r, " | ".join(top[:2]), " | ".join(top), " | ".join(p["fragmentos_esperados"]),
                          "SI" if enruta(p["pregunta"]) else "NO"])
        ses.rollback()

    def metricas(ids):
        rs_ = [rangos[i] for i in ids]
        n = len(rs_)
        return dict(n=n, recall5=sum(1 for r in rs_ if r) / n, recall2=sum(1 for r in rs_ if 0 < r <= 2) / n,
                    recall1=sum(1 for r in rs_ if r == 1) / n, mrr=sum(1 / r for r in rs_ if r) / n)

    def fmt(m):
        return (f"n={m['n']:2d}  recall@5 {m['recall5']:6.1%}  recall@2 {m['recall2']:6.1%}  recall@1 {m['recall1']:6.1%}  "
                f"MRR {m['mrr']:.3f}")

    grupos = {"todas": [p["id"] for p in conc],
              "6.4 (rag-*)": [p["id"] for p in conc if p["id"].startswith("rag-")],
              "ciegas 6.7b": [p["id"] for p in conc if p["id"].startswith("ciega-")]}
    resumen = {"etiqueta": a.etiqueta, "fragmentos_activos": len(activos), "excluidas": a.excluir, "esperados_inexistentes": faltan}
    print(f"[{a.etiqueta}] fragmentos activos: {len(activos)}; conceptuales evaluadas: {len(conc)}; excluidas: {a.excluir}")
    if faltan:
        print("AVISO esperados que no existen en el corpus activo:", faltan)
    for nombre, ids in grupos.items():
        if ids:
            m = metricas(ids)
            resumen[nombre] = m
            print(f"  {nombre:12s} {fmt(m)}")
    pasa_c = sum(1 for f in filas if f[6] == "SI")
    fugas = [p["id"] for p in neg if enruta(p["pregunta"])]
    resumen["enrutador"] = dict(conceptuales_pasan=pasa_c, conceptuales=len(conc), negativas_fugan=fugas, negativas=len(neg))
    print(f"  enrutador: conceptuales que pasan {pasa_c}/{len(conc)}; negativas que fugan {len(fugas)}/{len(neg)} {fugas}")
    fuera2 = [(f[0], f[2]) for f in filas if not (0 < f[2] <= 2)]
    print(f"  fuera del top-2: {fuera2}")
    if a.csv:
        with a.csv.open("w", encoding="utf-8", newline="") as fh:
            w = csv.writer(fh)
            w.writerow(["id", "pregunta", "rango_primer_esperado(0=fuera top5)", "top2", "top5", "esperado", "enrutador_pasa"])
            w.writerows(filas)
    if a.json:
        a.json.write_text(json.dumps(resumen, ensure_ascii=False, indent=1), encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
