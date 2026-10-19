"""Mide un modelo de embeddings en CPU (paso 6.2): disco, RAM, ms por fragmento y por consulta,
dimension y acierto indicativo en las 10 preguntas de preguntas_prueba.json (hit@5, NO es la
evaluacion 6.5). Un modelo por proceso, para que la RAM medida no se mezcle.

    CUDA_VISIBLE_DEVICES=-1 python rag/medir_embeddings.py --modelo e5-small [--hilos 3]
"""
import argparse, json, os, sys, time
from pathlib import Path

AQUI = Path(__file__).resolve().parent
sys.path.insert(0, str(AQUI))
import ingesta  # noqa: E402


def tam_cache(hf_id: str) -> int:
    from huggingface_hub import snapshot_download
    raiz = Path(snapshot_download(hf_id, local_files_only=True)).resolve().parents[1]
    return sum(f.stat().st_size for f in raiz.rglob("*") if f.is_file() and not f.is_symlink())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--modelo", required=True, choices=sorted(ingesta.MODELOS))
    ap.add_argument("--hilos", type=int, default=3)
    a = ap.parse_args()
    os.environ["OMP_NUM_THREADS"] = str(a.hilos)
    import numpy as np, psutil, torch
    torch.set_num_threads(a.hilos)
    proc = psutil.Process()
    frags, _ = ingesta.cargar_corpus(ingesta.CORPUS_DEFECTO)
    hf, pq, pp, dim = ingesta.MODELOS[a.modelo]
    rss0 = proc.memory_info().rss
    t0 = time.perf_counter()
    modelo, *_ = ingesta.cargar_modelo(a.modelo, a.hilos)
    t_carga = time.perf_counter() - t0
    rss1 = proc.memory_info().rss
    entradas = [f.entrada for f in frags]
    modelo.encode([pp + entradas[0]], normalize_embeddings=True)  # calentamiento
    # por fragmento, uno a uno (latencia) y en lotes de 8 (rendimiento de la ingesta)
    t0 = time.perf_counter()
    for e in entradas:
        modelo.encode([pp + e], normalize_embeddings=True)
    t_uno = (time.perf_counter() - t0) / len(entradas)
    t0 = time.perf_counter()
    M = modelo.encode([pp + e for e in entradas], batch_size=8, normalize_embeddings=True)
    t_lote = (time.perf_counter() - t0) / len(entradas)
    preguntas = json.loads((AQUI / "preguntas_prueba.json").read_text(encoding="utf-8"))
    t0 = time.perf_counter()
    Q = np.vstack([modelo.encode([pq + p["q"]], normalize_embeddings=True) for p in preguntas])
    t_consulta = (time.perf_counter() - t0) / len(preguntas)
    ids = [f.fragmento_id for f in frags]
    aciertos, mrr = 0, 0.0
    for p, q in zip(preguntas, Q):
        orden = np.argsort(-(M @ q))[:5]
        top = [ids[i] for i in orden]
        hit = [k for k, fid in enumerate(top) if ingesta.es_esperado(fid, p["esperado"])]
        aciertos += bool(hit)
        mrr += 1 / (hit[0] + 1) if hit else 0
    toks = [len(modelo.tokenizer(e)["input_ids"]) for e in entradas]
    out = dict(modelo=a.modelo, hf=hf, dim=int(M.shape[1]), hilos=a.hilos,
               disco_mb=round(tam_cache(hf) / 1e6), rss_carga_mb=round((rss1 - rss0) / 1e6),
               rss_pico_mb=round(getattr(proc.memory_info(), "peak_wset", proc.memory_info().rss) / 1e6),
               carga_s=round(t_carga, 1), ms_fragmento_uno=round(t_uno * 1e3), ms_fragmento_lote8=round(t_lote * 1e3),
               ms_consulta=round(t_consulta * 1e3), hit5=f"{aciertos}/{len(preguntas)}", mrr5=round(mrr / len(preguntas), 3),
               tokens_fragmento_mediana=sorted(toks)[len(toks) // 2], tokens_fragmento_max=max(toks),
               max_seq_len=modelo.max_seq_length, fragmentos=len(frags))
    print(json.dumps(out, ensure_ascii=False))


main()
