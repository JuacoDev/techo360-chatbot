"""Paso 6.5: evalua tres recuperadores sobre las preguntas conceptuales de claude/fase6-4-preguntas.jsonl.

  (a) vectores  e5-small (embedding de la consulta calculado aqui, localmente), distancia coseno en pgvector
  (b) texto     busqueda de texto de Postgres en espanol (to_tsvector('spanish', ...) calculado EN LA CONSULTA,
                sin migracion nueva), consulta OR de los lexemas de la pregunta, ponderando tema (A) y texto (B)
  (c) hibrido   RRF (k = 60) de (a) y (b)

Metricas sobre las preguntas conceptuales (recall@2 y @1 son lo que ve el modelo: 6.6 incluye como maximo 2): recall@5 (acierto si algun fragmento esperado esta en el top-5; un
fragmento partido id-1/id-2 cuenta como id) y MRR (rango del primer esperado, 0 si no aparece en el top-5).
Solo LEE; la base debe ser local (127.0.0.1). La regla de decision esta en claude/prompt-code-6-5-6-6.md.

Uso:
    RAG_DATABASE_URL=postgresql://...@127.0.0.1:54329/techo360_vector_test \\
        python rag/evaluar_recuperacion.py --preguntas ../claude/fase6-4-preguntas.jsonl [--csv fallos.csv]
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from ingesta import MODELOS, cargar_modelo, es_esperado, exigir_base_local  # noqa: E402

ACENTOS = str.maketrans("áéíóúüñÁÉÍÓÚÜÑ", "aeiouunAEIOUUN")
K = 5
RRF_K = 60

SQL_TEXTO = """
WITH q AS (
    SELECT to_tsquery('spanish', string_agg(quote_literal(lexeme), ' | ')) AS tsq
    FROM unnest(to_tsvector('spanish', %(q)s))
), docs AS (
    SELECT d.nombre, f.fragmento_id,
           setweight(to_tsvector('spanish', translate(f.tema, 'áéíóúüñÁÉÍÓÚÜÑ', 'aeiouunAEIOUUN')), 'A') ||
           setweight(to_tsvector('spanish', translate(f.texto, 'áéíóúüñÁÉÍÓÚÜÑ', 'aeiouunAEIOUUN')), 'B') AS v
    FROM rag_fragmentos f JOIN rag_documentos d ON d.id = f.documento_id
    WHERE f.activo AND d.activo
)
SELECT docs.nombre, docs.fragmento_id, {rank}(docs.v, q.tsq{norm}) AS r
FROM docs, q WHERE docs.v @@ q.tsq
ORDER BY r DESC, docs.fragmento_id LIMIT %(k)s
"""
SQL_VECTOR = """
SELECT d.nombre, f.fragmento_id, f.embedding <=> %(v)s AS dist
FROM rag_fragmentos f JOIN rag_documentos d ON d.id = f.documento_id
WHERE f.activo AND d.activo ORDER BY f.embedding <=> %(v)s, f.fragmento_id LIMIT %(k)s
"""


def sin_acentos(t: str) -> str:
    return t.translate(ACENTOS)


def buscar_texto(con, pregunta: str, k: int = K, rank: str = "ts_rank_cd", norm: int = 1):
    sql = SQL_TEXTO.format(rank=rank, norm=f", {norm}" if norm is not None else "")
    return [(f, r) for _, f, r in con.execute(sql, {"q": sin_acentos(pregunta), "k": k}).fetchall()]


def buscar_vector(con, vec, k: int = K):
    return [(f, d) for _, f, d in con.execute(SQL_VECTOR, {"v": vec, "k": k}).fetchall()]


def rrf(listas: list[list[str]], k: int = K) -> list[str]:
    puntos: dict[str, float] = {}
    for lista in listas:
        for rango, f in enumerate(lista, 1):
            puntos[f] = puntos.get(f, 0.0) + 1.0 / (RRF_K + rango)
    return [f for f, _ in sorted(puntos.items(), key=lambda x: (-x[1], x[0]))][:k]


def rango_primer_acierto(top: list[str], esperados: list[str]) -> int:
    return next((i for i, f in enumerate(top, 1) if es_esperado(f, esperados)), 0)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--preguntas", type=Path, required=True)
    ap.add_argument("--csv", type=Path)
    a = ap.parse_args()
    dsn = os.environ.get("RAG_DATABASE_URL") or sys.exit("Falta RAG_DATABASE_URL (base LOCAL).")
    exigir_base_local(dsn)
    import psycopg
    from pgvector.psycopg import register_vector

    preguntas = [json.loads(l) for l in a.preguntas.read_text(encoding="utf-8").splitlines() if l.strip()]
    conceptuales = [p for p in preguntas if p["tipo"] == "conceptual"]
    modelo, pq, _, _ = cargar_modelo("e5-small")
    resultados: dict[str, list[list[str]]] = {"a_vectores": [], "b_texto": [], "b2_ts_rank": [], "c_rrf": []}
    detalle = []
    with psycopg.connect(dsn) as con:
        con.execute("SET default_transaction_read_only = on")
        register_vector(con)
        activos = {f for (f,) in con.execute("SELECT fragmento_id FROM rag_fragmentos WHERE activo")}
        faltan = sorted({e for p in conceptuales for e in p["fragmentos_esperados"]
                         if not any(es_esperado(f, [e]) for f in activos)})
        t_b = []
        for p in conceptuales:
            vec = modelo.encode([pq + p["pregunta"]], normalize_embeddings=True, show_progress_bar=False)[0]
            va = [f for f, _ in buscar_vector(con, vec)]
            t0 = time.perf_counter()
            vb = [f for f, _ in buscar_texto(con, p["pregunta"])]
            t_b.append((time.perf_counter() - t0) * 1000)
            vb2 = [f for f, _ in buscar_texto(con, p["pregunta"], rank="ts_rank", norm=None)]
            vc = rrf([va, vb])
            for clave, top in (("a_vectores", va), ("b_texto", vb), ("b2_ts_rank", vb2), ("c_rrf", vc)):
                resultados[clave].append(top)
            detalle.append((p, va, vb, vc))
    resumen = {}
    for clave, tops in resultados.items():
        rangos = [rango_primer_acierto(t, p["fragmentos_esperados"]) for t, p in zip(tops, conceptuales)]
        n = len(rangos)
        resumen[clave] = (sum(1 for r in rangos if r) / n, sum(1 / r for r in rangos if r) / n, sum(1 for r in rangos if r), n,
                          sum(1 for r in rangos if 0 < r <= 2) / n, sum(1 for r in rangos if r == 1) / n)
    print(f"Preguntas conceptuales: {len(conceptuales)}; fragmentos activos: {len(activos)}")
    if faltan:
        print("AVISO: esperados que ya no existen en el corpus activo:", faltan)
    for clave, (rec, mrr, aciertos, n, rec2, rec1) in resumen.items():
        print(f"{clave:11s} recall@5 = {rec:6.1%} ({aciertos}/{n})   MRR = {mrr:.3f}   recall@2 = {rec2:6.1%}   recall@1 = {rec1:6.1%}")
    print(f"(b) ms por consulta (cliente local, 38 filas): mediana {sorted(t_b)[len(t_b)//2]:.1f}, max {max(t_b):.1f}")
    filas = []
    for p, va, vb, vc in detalle:
        for etiqueta, top in (("a_vectores", va), ("b_texto", vb), ("c_rrf", vc)):
            if not rango_primer_acierto(top, p["fragmentos_esperados"]):
                filas.append([etiqueta, p["id"], p["pregunta"], " | ".join(top), " | ".join(p["fragmentos_esperados"])])
    for f in filas[:0]:
        print(f)
    if a.csv:
        with a.csv.open("w", encoding="utf-8", newline="") as fh:
            w = csv.writer(fh)
            w.writerow(["recuperador", "id", "pregunta", "recuperado_top5", "esperado"])
            w.writerows(filas)
    print(f"Fallos: {len(filas)} filas" + (f" -> {a.csv}" if a.csv else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
