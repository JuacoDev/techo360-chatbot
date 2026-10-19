"""Fase B de 7.3: genera el dataset 0.4.1 (G, H, F+, HS, listas, 0.4.0 re-renderizado) y los holdouts nuevos.

    python -m training.dataset_0_4_1.generar_fase_b --salida ../trabajo-dataset-0.4.1

Entradas: snapshot de mapcalordb (CSV), backend en un worktree de origin/testing (pipeline real), nucleo de proyeccion con sha256 verificado,
corpus RAG final en un Postgres local desechable, y el dataset 0.4.0 en `../trabajo-dataset-0.4.0-r2`. No usa base de produccion ni red.
Misma semilla => mismos archivos.
"""
import argparse
import collections
import hashlib
import json
import sys
import time
from pathlib import Path

from . import entorno

entorno.preparar_rutas()

from . import catalogo as cat  # noqa: E402
from . import controles as ct  # noqa: E402
from .ctl import Controles, Dedup  # noqa: E402
from .gen_f import GenF  # noqa: E402
from .gen_g import GenG  # noqa: E402
from .gen_h import GenH  # noqa: E402
from .gen_hs import GenHS  # noqa: E402
from .gen_listas import GenListas  # noqa: E402
from .motor import MAX_TOKENS_PAR, SYSTEM_SHA256, VERSION_PROMPT, Entorno, Par, escribir_jsonl, prompt_multiturno  # noqa: E402
from .rag_local import RagLocal  # noqa: E402

DIR_040 = entorno.RAIZ_MONOREPO / "trabajo-dataset-0.4.0-r2"
G_SUBS = [s for s in cat.CUOTAS if s.startswith(("g1", "g2", "g3", "g4", "g5", "g6"))]
F_SUBS = [s for s in cat.CUOTAS if s.startswith("fp_")]
HS_SUBS = [s for s in cat.CUOTAS if s.startswith("hs")]
HOLDOUT_GRAF = {"g1_lineas_individual": 6, "g1_lineas_comparar": 5, "g1_barras_ranking": 5, "g1_barras_agrupadas_ind": 3,
                "g1_barras_agrupadas_cmp": 2, "g1_gauge": 4, "g2_serie": 2, "g2_comparacion": 1, "g2_puntual": 1, "g3_un_anio": 2,
                "g3_sin_dato": 2, "g4_tipo_no_soportado": 3, "g5_sin_municipio": 2, "g5_sin_variable": 2}
HOLDOUT_HIST = {"hs1_anio": 8, "hs2_municipio": 6, "hs3_variable": 5, "hs4_real": 2, "hs4_estimado": 2, "hs5_cambio_tema": 4, "hs6_inyeccion_previa": 3}


def jsonl(ruta: Path) -> list[dict]:
    return [json.loads(l) for l in ruta.read_text(encoding="utf-8").splitlines() if l.strip()]


def escalar(cuotas: dict[str, int], escala: float) -> dict[str, int]:
    return {k: max(1, round(v * escala)) for k, v in cuotas.items()} if escala != 1 else dict(cuotas)


class Corrida:
    def __init__(self, args):
        self.args = args
        self.t0 = time.time()
        self.rechazos: collections.Counter = collections.Counter()  # (sub, motivo)
        self.pares: dict[str, list[Par]] = collections.defaultdict(list)

    def log(self, *a):
        print(f"[{time.time() - self.t0:6.0f}s]", *a, flush=True)

    # ------------------------------------------------------------------ bucle de una subfamilia
    def llenar(self, gen, sub: str, cuota: int, ctl: Controles, dd: Dedup, almacen: dict, intentos_por_par: int = 40, produce=None) -> None:
        produce = produce or (lambda: gen.generar(sub))
        intentos = 0
        while len(almacen[sub]) < cuota and intentos < cuota * intentos_por_par:
            intentos += 1
            p = produce()
            if p is None:
                continue
            if p.subfamilia != sub:
                continue
            m = ctl.todos(p) or dd.probar(p)
            if m:
                self.rechazos[(sub, m)] += 1
                continue
            almacen[sub].append(p)
        self.log(f"{sub}: {len(almacen[sub])}/{cuota} (intentos {intentos})")


def principal(argv=None) -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser()
    ap.add_argument("--salida", default=str(entorno.RAIZ_MONOREPO / "trabajo-dataset-0.4.1"))
    ap.add_argument("--semilla", type=int, default=entorno.SEMILLA)
    ap.add_argument("--escala", type=float, default=1.0, help="reduce las cuotas (pruebas)")
    ap.add_argument("--sin-reuso", action="store_true", help="no re-renderiza el dataset 0.4.0 (pruebas)")
    ap.add_argument("--umbral-respuesta", type=float, default=0.75, help="similitud maxima entre respuestas de una familia")
    args = ap.parse_args(argv)
    salida = Path(args.salida)
    salida.mkdir(parents=True, exist_ok=True)
    run = Corrida(args)

    nucleo = entorno.verificar_nucleo_proyeccion()
    backend = entorno.huella_backend()
    run.log("nucleo de proyeccion", nucleo["commit"][:8], "backend", backend["commit"][:8])

    reservados = set(json.loads((DIR_040 / "reservados.json").read_text(encoding="utf-8"))["codigos"])
    train_c0 = jsonl(DIR_040 / "train_c0.jsonl")
    train_nuevos = jsonl(DIR_040 / "train_nuevos.jsonl")
    evaluacion, faltantes = ct.cargar_conjuntos_evaluacion(entorno.RAIZ_CHATBOT, entorno.RAIZ_MONOREPO)
    run.log("conjuntos de evaluacion:", {k: len(v) for k, v in evaluacion.items()}, "faltantes:", faltantes)

    from scripts.dataset_0_4.tokens import Tokenizador  # noqa: E402
    tok = Tokenizador(cache=salida / "cache_tokens.json")

    with RagLocal() as rag:
        E = Entorno(rag=rag)
        corpus_idf = [json.loads(x)["entrada"]["pregunta"] for x in (DIR_040 / "train_nuevos.jsonl").read_text(encoding="utf-8").splitlines() if x.strip()]
        ctl = Controles(E, tok, evaluacion, corpus_idf)
        from scripts.dataset_0_4.similitud import Tfidf
        tf_p = ctl.tf
        tf_r = Tfidf([r["response"] for r in train_nuevos])

        # ------------------------------------------------------------------ holdouts (primero: sus preguntas quedan vetadas para el train)
        run.log("== holdouts")
        hold: dict[str, dict] = {"graf": collections.defaultdict(list), "rag": collections.defaultdict(list), "hist": collections.defaultdict(list)}
        dd_h = {k: Dedup(tf_p, tf_r, args.umbral_respuesta) for k in hold}
        gh = GenG(E, args.semilla, reservados, "holdout", "hold-")
        for sub, n in escalar(HOLDOUT_GRAF, args.escala).items():
            run.llenar(gh, sub, n, ctl, dd_h["graf"], hold["graf"], 200)
        hh = GenHS(E, args.semilla, reservados, "holdout", "hold-")
        for sub, n in escalar(HOLDOUT_HIST, args.escala).items():
            run.llenar(hh, sub, n, ctl, dd_h["hist"], hold["hist"], 200)
        hr = GenH(E, args.semilla, reservados, "holdout", "hold-")
        from . import h_datos as hd
        answerable = hold["rag"]["h_respondible"]
        for it in [x for x in hd.INTENCIONES if x["qh"]]:
            if len(answerable) >= round(30 * args.escala):
                break
            p = hr.par_respondible(it, it["qh"]) or (hr.par_respondible(it, it["qh2"]) if it.get("qh2") else None)
            if p is None:
                run.rechazos[("holdout_rag", "no_recuperado:" + it["id"])] += 1
                continue
            m = ctl.todos(p) or dd_h["rag"].probar(p)
            if m:
                run.rechazos[("holdout_rag", m)] += 1
                continue
            answerable.append(p)
        for q in hd.H3_HOLDOUT[:max(1, round(10 * args.escala))]:
            p = hr.par_abstencion(q)
            if p is None:
                continue
            m = ctl.todos(p) or dd_h["rag"].probar(p)
            if m:
                run.rechazos[("holdout_rag", m)] += 1
                continue
            hold["rag"]["h_abstencion"].append(p)
        for k in hold:
            for lista in hold[k].values():
                for p in lista:
                    q = p.entrada["pregunta"]
                    ctl.eval_vec.agregar(ctl.tf.vec(q))  # sus preguntas quedan vetadas para el train
        run.log("holdouts:", {k: sum(len(v) for v in d.values()) for k, d in hold.items()})

        # ------------------------------------------------------------------ train nuevo
        run.log("== train nuevo")
        dd = Dedup(tf_p, tf_r, args.umbral_respuesta)
        nuevos: dict[str, list[Par]] = collections.defaultdict(list)
        cuotas = escalar(cat.CUOTAS, args.escala)
        gg = GenG(E, args.semilla, reservados, "train")
        for sub in G_SUBS:
            run.llenar(gg, sub, cuotas[sub], ctl, dd, nuevos)
        gf = GenF(E, args.semilla, reservados, "train")
        for sub in F_SUBS:
            run.llenar(gf, sub, cuotas[sub], ctl, dd, nuevos)
        ghs = GenHS(E, args.semilla, reservados, "train")
        for sub in HS_SUBS:
            run.llenar(ghs, sub, cuotas[sub], ctl, dd, nuevos)
        gH = GenH(E, args.semilla, reservados, "train")
        cH = escalar(cat.CUOTAS_H, args.escala)
        # H1/H2/H3 salen de las mismas preguntas segun lo que recupera el retriever real
        agotado = False
        intentos = 0
        while not agotado and intentos < 2000:
            intentos += 1
            p = gH.h12()
            if p is None:
                if gH.cursor.get("h12", 0) > 400:
                    agotado = True
                continue
            if len(nuevos[p.subfamilia]) >= cH[p.subfamilia]:
                continue
            m = ctl.todos(p) or dd.probar(p)
            if m:
                run.rechazos[(p.subfamilia, m)] += 1
                continue
            nuevos[p.subfamilia].append(p)
        for sub in ("h1_un_fragmento", "h2_marginal"):
            run.log(f"{sub}: {len(nuevos[sub])}/{cH[sub]}")
        for sub in ("h3_sin_cobertura", "h5_premisa", "h6_concepto_general", "h4_datos_y_documento"):
            gH.cursor.pop(sub, None)
            run.llenar(gH, sub, cH[sub], ctl, dd, nuevos, 80)

        # ------------------------------------------------------------------ listas y 0.4.0
        run.log("== listas y reutilizacion de 0.4.0")
        gl = GenListas(E, args.semilla, set(), "train")
        listas, regeneradas = [], set()
        for p0 in train_nuevos:
            if p0["subfamilia"] not in ("A3", "A4", "A5"):
                continue
            p = gl.regenerar(p0)
            if p is None:
                continue
            m = ctl.todos(p)
            if m:
                run.rechazos[("listas", m)] += 1
                continue
            listas.append(p)
            regeneradas.add(p0["id"])
        run.log("listas:", collections.Counter(p.meta["subfamilia_0_4_0"] for p in listas))

        reutil, info_reuso = [], collections.Counter()
        if not args.sin_reuso:
            reutil, info_reuso, rag_afecta = reutilizar(E, train_c0, train_nuevos, regeneradas, tok, run)
        else:
            rag_afecta = {}

        # ------------------------------------------------------------------ escribir
        run.log("== escritura")
        todos = [p for sub in nuevos for p in nuevos[sub]]
        filas_nuevos = [p.a_dict(args.semilla) for p in todos + listas]
        filas_reutil = [p.a_dict(args.semilla) for p in reutil]
        dataset = filas_reutil + filas_nuevos
        h4 = {p["id"] for p in filas_nuevos if p["subfamilia"] == "h4_datos_y_documento"}
        sumas = {}
        sumas["dataset_0_4_1.jsonl"] = escribir_jsonl(salida / "dataset_0_4_1.jsonl", dataset)
        sumas["dataset_0_4_1_sin_h4.jsonl"] = escribir_jsonl(salida / "dataset_0_4_1_sin_h4.jsonl", [f for f in dataset if f["id"] not in h4])
        sumas["train_nuevos_0_4_1.jsonl"] = escribir_jsonl(salida / "train_nuevos_0_4_1.jsonl", filas_nuevos)
        nombres = {"graf": "holdout_graf.jsonl", "rag": "holdout_rag.jsonl", "hist": "holdout_hist.jsonl"}
        for k, d in hold.items():
            filas = [p.a_dict(args.semilla) for lista in d.values() for p in lista]
            sumas[nombres[k]] = escribir_jsonl(salida / nombres[k], filas)
        (salida / "SHA256SUMS").write_text("".join(f"{v}  {k}\n" for k, v in sorted(sumas.items())), encoding="utf-8", newline="\n")
        resumen = {
            "semilla": args.semilla, "escala": args.escala, "sha256": sumas, "backend": backend, "nucleo_proyeccion": nucleo,
            "sistema": {"version": VERSION_PROMPT, "sha256": SYSTEM_SHA256}, "rag": rag.meta | {"fragmentos_ids": len(rag.meta["fragmentos_ids"])},
            "conteos_nuevos": {s: len(v) for s, v in nuevos.items()}, "conteos_listas": dict(collections.Counter(p.subfamilia for p in listas)),
            "conteos_reutilizados": dict(collections.Counter(f["subfamilia"] for f in filas_reutil)),
            "holdouts": {k: {s: len(v) for s, v in d.items()} for k, d in hold.items()},
            "rechazos": {f"{s}|{m}": n for (s, m), n in sorted(run.rechazos.items())},
            "reuso": dict(info_reuso), "rag_afectaria_a_reutilizados": rag_afecta,
            "max_sim_eval": ctl.maximos, "max_sim_respuesta": dd.max_r,
            "tokens": tokens_resumen(dataset), "h4_ids": sorted(h4), "total_dataset": len(dataset),
            "segundos": round(time.time() - run.t0),
        }
        (salida / "resumen.json").write_text(json.dumps(resumen, ensure_ascii=False, indent=1), encoding="utf-8", newline="\n")
        run.log("listo:", len(dataset), "pares;", sumas["dataset_0_4_1.jsonl"][:12])
        tok.guardar()
    return 0


def tokens_resumen(filas: list[dict]) -> dict:
    t = [f.get("tokens_total") for f in filas if f.get("tokens_total")]
    return {"max": max(t) if t else None, "sobre_1720": sum(1 for x in t if x > MAX_TOKENS_PAR), "n": len(t)}


def reutilizar(E: Entorno, train_c0, train_nuevos, regeneradas: set, tok, run: Corrida):
    """Re-renderiza los pares de 0.4.0 con sp-0.4.1-1: mismo contexto, misma respuesta. Sin C3 (lo sustituye H) ni los regenerados con listas."""
    reutil: list[Par] = []
    info: collections.Counter = collections.Counter()
    rag_afecta: collections.Counter = collections.Counter()
    for p0 in train_c0 + train_nuevos:
        sub = p0["subfamilia"]
        if sub == "C3":
            info["retirados_C3_sustituidos_por_H"] += 1
            continue
        if p0["id"] in regeneradas:
            info["regenerados_con_lista"] += 1
            continue
        e = p0["entrada"]
        r = E.preparar(e["pregunta"], huecos=e.get("huecos"), usar_rag=False)
        if r["accion"] != "consultar" or r["peticion"]["mensajes"][-1]["contenido"] != p0["instruction"]:
            info["descartados_contexto_distinto"] += 1
            continue
        # con el RAG activo, ¿produccion agregaria fragmentos a esta pregunta? (hallazgo; el par NO se modifica)
        r2 = E.preparar(e["pregunta"], huecos=e.get("huecos"), usar_rag=True)
        if r2["accion"] == "consultar" and r2["rag_resultados"] and "[d1]" in r2["peticion"]["mensajes"][-1]["contenido"]:
            rag_afecta[sub] += 1
        mensajes = r["peticion"]["mensajes"]
        par = Par(p0["id"], p0["familia"], sub, mensajes, p0["response"], e, p0.get("plantilla_pregunta", ""), p0.get("plantilla_respuesta", ""),
                  {"origen": "0.4.0", "source_0_4_0": p0.get("source", "")})
        prompt = prompt_multiturno(mensajes)
        total, resp = tok.contar([prompt + par.respuesta + "<|eot_id|>", par.respuesta + "<|eot_id|>"])
        par.meta["tokens_total"], par.meta["tokens_respuesta"] = total, resp
        if total > MAX_TOKENS_PAR:
            info["sobre_1720_tokens_con_el_system_nuevo"] += 1
        reutil.append(par)
        info["reutilizados"] += 1
    run.log("reutilizados:", dict(info), "| el RAG agregaria [dN] a:", dict(rag_afecta))
    return reutil, info, dict(rag_afecta)


if __name__ == "__main__":
    sys.exit(principal())
