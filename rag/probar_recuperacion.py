"""Prueba minima de recuperacion (paso 6.2/6.3, NO es la evaluacion 6.5): ejecuta las preguntas de
rag/preguntas_prueba.json contra la base LOCAL ya cargada con rag/ingesta.py y muestra el top-5 con
distancia coseno (0 = identico). Solo lectura. Misma regla de seguridad que la ingesta: base local.

    RAG_DATABASE_URL=postgresql://...@localhost:.../techo360_vector_test python rag/probar_recuperacion.py [--k 5]
"""
import argparse
import json
import os
import sys
from pathlib import Path

AQUI = Path(__file__).resolve().parent
sys.path.insert(0, str(AQUI))
import ingesta  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--k", type=int, default=5)
    ap.add_argument("--modelo", choices=sorted(ingesta.MODELOS), default=ingesta.MODELO_DEFECTO)
    ap.add_argument("--salida", type=Path, help="escribe la tabla en Markdown en este archivo")
    a = ap.parse_args()
    dsn = os.environ.get("RAG_DATABASE_URL") or sys.exit("Falta RAG_DATABASE_URL (base LOCAL)")
    ingesta.exigir_base_local(dsn)

    import psycopg
    from pgvector.psycopg import register_vector

    modelo, pq, _pp, _dim = ingesta.cargar_modelo(a.modelo)
    preguntas = json.loads((AQUI / "preguntas_prueba.json").read_text(encoding="utf-8"))
    lineas, aciertos = [], 0
    with psycopg.connect(dsn) as con:
        con.execute("SET default_transaction_read_only = on")
        register_vector(con)
        for n, p in enumerate(preguntas, 1):
            v = ingesta.embeber(modelo, pq, [p["q"]])[0]
            filas = con.execute(
                """SELECT d.nombre || '/' || f.fragmento_id, f.tema, f.embedding <=> %s AS dist
                     FROM rag_fragmentos f JOIN rag_documentos d ON d.id = f.documento_id
                    WHERE f.activo AND d.activo
                    ORDER BY f.embedding <=> %s LIMIT %s""", (v, v, a.k)).fetchall()
            ids = [r[0].split("/", 1)[1] for r in filas]
            pos = next((i + 1 for i, x in enumerate(ids) if ingesta.es_esperado(x, p["esperado"])), None)
            aciertos += pos is not None
            lineas.append(f"\n### {n}. {p['q']}\nEsperado: {', '.join(p['esperado'])} -> "
                          + (f"acierto en el puesto {pos}" if pos else "NO aparece en el top-" + str(a.k)))
            lineas.append("| # | fragmento | tema | distancia |\n|---|---|---|---:|")
            for i, (fid, tema, dist) in enumerate(filas, 1):
                marca = " **(esperado)**" if ingesta.es_esperado(fid.split("/", 1)[1], p["esperado"]) else ""
                lineas.append(f"| {i} | {fid}{marca} | {tema} | {dist:.4f} |")
    resumen = f"hit@{a.k} = {aciertos}/{len(preguntas)} (indicativo; 10 preguntas, no es la evaluacion 6.5)"
    texto = resumen + "\n" + "\n".join(lineas) + "\n"
    if a.salida:
        a.salida.write_text(texto, encoding="utf-8", newline="\n")
    print(resumen)
    return 0


if __name__ == "__main__":
    sys.exit(main())
