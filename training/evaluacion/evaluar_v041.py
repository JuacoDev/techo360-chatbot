"""Paso 7.5: evaluacion de 0.4.1 en HF 4-bit y en GGUF Q4_K_M (Ollama). SOLO MIDE: no modifica modelos, datos, validador ni prompts.

Reutiliza `evaluar_v040.py` (cargador, muestreo, metricas del holdout contextual, validador 4.5) y `evaluar_extra_5_6b.py` (inyeccion F y C3).
Conjuntos (mensajes = lista de turnos de chat; el system es sp-0.4.1-1 byte a byte):
  ctx    holdout contextual de 0.4.0 (60)          [system, user=instruction]
  extra  F de inyeccion (30) + C3 (20) de 5.6b     [system, user=instruction]
  graf   holdout_graf (40: 25 con grafica + 15 negativos)    `mensajes` del archivo
  hist   holdout_hist (30, multi-turno)                      `mensajes` del archivo
  rag    holdout_rag (35: 25 respondibles + 10 sin documento) `mensajes` del archivo

Fases (subcomandos):
  generar-hf                      GPU; adaptador 0.4.1 en NF4, fecha fija «18 Sep 2026» (la del entrenamiento) -> crudo_hf.jsonl
  generar-ollama --url U          Ollama (CPU) con techo360-chatbot:v0.4.1; solo num_predict y seed (el resto sale del Modelfile) -> crudo_ollama.jsonl
  latencia --url U                latencia y reutilizacion de la cache del prefijo del system -> latencia.json
  medir                           metricas de ambos crudos + comparacion con 0.4.0 -> resumen_7_5.json, tabla_7_5.md, detalle_<backend>.csv
Las corridas se recorren por semilla (todas las semillas 1 de todos los pares, luego las 2, ...): un corte deja siempre las primeras semillas completas.
Reanudable: una linea por generacion.
"""
import argparse
import csv
import hashlib
import importlib.util
import json
import re
import sys
import time
import urllib.request
from collections import Counter, defaultdict
from pathlib import Path

AQUI = Path(__file__).resolve().parent
RAIZ_CHATBOT = AQUI.parents[1]
RAIZ_MONO = RAIZ_CHATBOT.parent
sys.path.insert(0, str(RAIZ_CHATBOT))
from training.dataset_0_4_1 import entorno  # noqa: E402

entorno.preparar_rutas()


def _cargar(nombre, archivo):
    spec = importlib.util.spec_from_file_location(nombre, AQUI / archivo)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[nombre] = mod
    spec.loader.exec_module(mod)
    return mod


ev = _cargar("evaluar_v040", "evaluar_v040.py")
ex = _cargar("evaluar_extra_5_6b", "evaluar_extra_5_6b.py")
ev.VALIDADOR = entorno.BACKEND_DIR / "services" / "orquestador" / "validador_cifras.py"  # el del backend con W1/H1 (no el de la rama formateo)

DIR41 = RAIZ_MONO / "trabajo-dataset-0.4.1"
DIR_MODELO = DIR41 / "modelo-0.4.1"
ADAPTADOR = DIR_MODELO / "adaptador"
SALIDA = DIR_MODELO / "evaluacion"
SYSTEM_041 = RAIZ_CHATBOT / "prompts" / "sp-0.4.1-1.txt"
MODELO_OLLAMA = "techo360-chatbot:v0.4.1"
SHA = {
    "adaptador": "d5f01ec5548cb9d96b564db1ad50bd02d3a9e4ff30739c79c08f2c33ec52d333",
    "system": "7e58d55bc020caa4f4fec204c72382cf905535954d64ea9db3d50d1da70ab921",
    "graf": "658dcc77be5b20e59b86c11e982117da0443d90b3a64d9b69f171c0fb2852916",
    "hist": "46ed9ee706ac1f018448080ec5942e3a1999cd86635dfa1164892a67925de65c",
    "rag": "1cc418f09b2d029678b9248da6dc5ae11ba32aeedb95591d815d344c8326b093",
}
SEMILLAS = [1, 2, 3, 4, 5]
CONJUNTOS = ("ctx", "extra", "graf", "hist", "rag")
LINEA_SIN_CONTEXTO = "Sin datos disponibles para esta consulta."


# ---------------------------------------------------------------------------------------------------------------- conjuntos
def system_041() -> str:
    assert ev.sha256_archivo(SYSTEM_041) == SHA["system"], "sha256 de sp-0.4.1-1 distinto"
    return SYSTEM_041.read_bytes().decode("utf-8")


def cargar_conjuntos() -> dict[str, list[dict]]:
    sistema = system_041()
    out: dict[str, list[dict]] = {}
    for nombre, pares in (("ctx", ev.cargar_conjuntos()["ctx"]), ("extra", ex.cargar_extra())):
        out[nombre] = [{**p, "msgs": [{"role": "system", "content": sistema}, {"role": "user", "content": p["instruction"]}]} for p in pares]
    for nombre in ("graf", "hist", "rag"):
        ruta = DIR41 / f"holdout_{nombre}.jsonl"
        assert ev.sha256_archivo(ruta) == SHA[nombre], f"sha256 de {ruta.name} distinto del congelado"
        filas = ev.leer_jsonl(ruta)
        for p in filas:
            assert p["mensajes"][0]["contenido"] == sistema and p["mensajes"][-1]["rol"] == "user"
            p["msgs"] = [{"role": {"user": "user", "assistant": "assistant", "system": "system"}[m["rol"]], "content": m["contenido"]} for m in p["mensajes"]]
            p["instruction"] = p["mensajes"][-1]["contenido"]  # turno actual: CONTEXTO + PREGUNTA
        out[nombre] = filas
    return out


def tareas_pendientes(conjuntos: dict, hechas: set, seleccion: list[str], semillas: list[int]) -> list:
    return [(c, p, s) for s in semillas for c in seleccion for p in conjuntos[c] if (c, p["id"], s) not in hechas]


def leer_hechas(ruta: Path) -> set:
    return {(g["conjunto"], g["id"], g["corrida"]) for g in ev.leer_jsonl(ruta)} if ruta.exists() else set()


# ---------------------------------------------------------------------------------------------------------------- generacion
def cmd_generar_hf(args) -> int:
    assert ev.sha256_archivo(ADAPTADOR / "adapter_model.safetensors") == SHA["adaptador"], "sha256 del adaptador 0.4.1 distinto"
    conjuntos = cargar_conjuntos()
    SALIDA.mkdir(parents=True, exist_ok=True)
    ruta = SALIDA / "crudo_hf.jsonl"
    tareas = tareas_pendientes(conjuntos, leer_hechas(ruta), args.conjuntos, args.semillas)
    total = sum(len(conjuntos[c]) for c in args.conjuntos) * len(args.semillas)
    print(f"HF: {total - len(tareas)} hechas, {len(tareas)} por hacer de {total}", flush=True)
    if not tareas:
        return 0
    torch, tok, modelo = ev.cargar_modelo(ADAPTADOR)
    from transformers import LogitsProcessor, LogitsProcessorList

    class Penaliza(LogitsProcessor):
        def __call__(self, input_ids, scores):
            ids = input_ids[:, -ev.VENTANA_REP:]
            sc = torch.gather(scores, 1, ids)
            return scores.scatter(1, ids, torch.where(sc > 0, sc / ev.PENAL_REP, sc * ev.PENAL_REP))

    def generar(msgs: list[dict], semilla: int) -> dict:
        prompt = tok.apply_chat_template(msgs, tokenize=False, add_generation_prompt=True, date_string=ev.FECHA)
        ids = tok(prompt, add_special_tokens=False, return_tensors="pt").to(modelo.device)
        torch.manual_seed(semilla)
        torch.cuda.manual_seed_all(semilla)
        t0 = time.time()
        with torch.no_grad():
            out = modelo.generate(**ids, do_sample=True, temperature=ev.TEMPERATURA, top_p=ev.TOP_P, top_k=ev.TOP_K, max_new_tokens=ev.NUM_PREDICT,
                                  logits_processor=LogitsProcessorList([Penaliza()]), eos_token_id=[ev.EOT_ID, tok.eos_token_id], pad_token_id=tok.eos_token_id)
        nuevos = out[0][ids["input_ids"].shape[1]:].tolist()
        termina = bool(nuevos) and nuevos[-1] == ev.EOT_ID
        return {"respuesta": tok.decode([t for t in nuevos if t != ev.EOT_ID], skip_special_tokens=False), "tokens_prompt": int(ids["input_ids"].shape[1]),
                "tokens": len(nuevos), "termina_eot": termina, "se_repite": ev.se_repite(nuevos), "llego_al_tope": len(nuevos) >= ev.NUM_PREDICT and not termina,
                "segundos": round(time.time() - t0, 2)}

    t0, n = time.time(), 0
    with open(ruta, "a", encoding="utf-8", newline="\n") as f:
        for c, p, s in tareas:
            g = generar(p["msgs"], s)
            f.write(json.dumps({"brazo": "HF", "conjunto": c, "id": p["id"], "corrida": s, "semilla": s, **g}, ensure_ascii=False) + "\n")
            f.flush()
            n += 1
            if n % 25 == 0:
                print(f"  HF {total - len(tareas) + n}/{total}  {(time.time() - t0) / 60:.1f} min  VRAM max {torch.cuda.max_memory_reserved() / 2 ** 20:.0f} MB", flush=True)
    print(f"listo HF: {n} generaciones en {(time.time() - t0) / 60:.1f} min", flush=True)
    return 0


def _post(url: str, ruta: str, cuerpo: dict, timeout=900) -> dict:
    req = urllib.request.Request(url + ruta, data=json.dumps(cuerpo).encode(), headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read())


def cmd_generar_ollama(args) -> int:
    from transformers import AutoTokenizer
    tok = AutoTokenizer.from_pretrained(str(ADAPTADOR))
    conjuntos = cargar_conjuntos()
    SALIDA.mkdir(parents=True, exist_ok=True)
    ruta = SALIDA / "crudo_ollama.jsonl"
    tareas = tareas_pendientes(conjuntos, leer_hechas(ruta), args.conjuntos, args.semillas)
    total = sum(len(conjuntos[c]) for c in args.conjuntos) * len(args.semillas)
    print(f"Ollama: {total - len(tareas)} hechas, {len(tareas)} por hacer de {total}", flush=True)
    t0, n = time.time(), 0
    with open(ruta, "a", encoding="utf-8", newline="\n") as f:
        for c, p, s in tareas:
            r = _post(args.url, "/api/chat", {"model": MODELO_OLLAMA, "stream": False, "keep_alive": "60m", "messages": p["msgs"],
                                              "options": {"num_predict": 400, "seed": s}})
            texto = r["message"]["content"]
            ids = tok(texto, add_special_tokens=False)["input_ids"]
            g = {"brazo": "O", "conjunto": c, "id": p["id"], "corrida": s, "semilla": s, "respuesta": texto, "tokens_prompt": r.get("prompt_eval_count"),
                 "tokens": r.get("eval_count"), "termina_eot": r.get("done_reason") == "stop", "se_repite": ev.se_repite(ids),
                 "llego_al_tope": r.get("done_reason") == "length", "eval_s": round(r.get("eval_duration", 0) / 1e9, 3),
                 "prompt_eval_s": round(r.get("prompt_eval_duration", 0) / 1e9, 3), "total_s": round(r.get("total_duration", 0) / 1e9, 3),
                 "load_s": round(r.get("load_duration", 0) / 1e9, 3)}
            f.write(json.dumps(g, ensure_ascii=False) + "\n")
            f.flush()
            n += 1
            if n % 25 == 0:
                print(f"  Ollama {total - len(tareas) + n}/{total}  {(time.time() - t0) / 60:.1f} min", flush=True)
    print(f"listo Ollama: {n} generaciones en {(time.time() - t0) / 60:.1f} min", flush=True)
    return 0


def cmd_latencia(args) -> int:
    """Latencia por respuesta y reutilizacion de la cache del prefijo del system en Ollama.
    Secuencia A (5 turnos distintos, mismo system, uno tras otro): tokens que Ollama evalua (prompt_eval_count) frente al total del prompt.
    Secuencia B: la MISMA peticion dos veces (cache completa). Secuencia C: tras cargar OTRO modelo y volver (cache fria). num_predict 40 para acortar."""
    from transformers import AutoTokenizer
    tok = AutoTokenizer.from_pretrained(str(ADAPTADOR))
    conjuntos = cargar_conjuntos()
    pares = conjuntos["ctx"][:5]

    def pedir(msgs, num_predict=40, semilla=1):
        t0 = time.time()
        r = _post(args.url, "/api/chat", {"model": MODELO_OLLAMA, "stream": False, "keep_alive": "60m", "messages": msgs,
                                          "options": {"num_predict": num_predict, "seed": semilla}})
        total_tokens = len(tok.apply_chat_template(msgs, tokenize=True, add_generation_prompt=True, date_string=ev.FECHA, return_dict=True)["input_ids"])
        return {"prompt_total_tokens_hf": total_tokens, "prompt_eval_count": r.get("prompt_eval_count"), "prompt_eval_s": round(r.get("prompt_eval_duration", 0) / 1e9, 2),
                "eval_count": r.get("eval_count"), "eval_s": round(r.get("eval_duration", 0) / 1e9, 2), "total_s": round(r.get("total_duration", 0) / 1e9, 2),
                "pared_s": round(time.time() - t0, 2)}

    _post(args.url, "/api/chat", {"model": MODELO_OLLAMA, "stream": False, "keep_alive": "60m", "messages": [{"role": "user", "content": "hola"}], "options": {"num_predict": 1}})
    sec_a = [pedir(p["msgs"]) for p in pares]
    sec_b = [pedir(pares[0]["msgs"]) for _ in range(2)]
    # prefijo del system compartido y turno multi-turno: el segundo turno agrega historial al mismo prefijo
    h = conjuntos["hist"][0]
    sec_c = [pedir(h["msgs"]), pedir(h["msgs"])]
    out = {"modelo": MODELO_OLLAMA, "url": args.url, "num_predict": 40, "A_turnos_distintos_mismo_system": sec_a, "B_misma_peticion_dos_veces": sec_b,
           "C_turno_con_historial_dos_veces": sec_c}
    ev_a = [x["prompt_eval_count"] for x in sec_a]
    out["lectura"] = {
        "tokens_system_aprox": len(tok(system_041(), add_special_tokens=False)["input_ids"]),
        "A_prompt_eval_count": ev_a, "A_prompt_total_hf": [x["prompt_total_tokens_hf"] for x in sec_a],
        "reutiliza_prefijo_entre_turnos_distintos": any(x["prompt_eval_count"] < x["prompt_total_tokens_hf"] - 100 for x in sec_a[1:]),
        "B_segunda_evalua": sec_b[1]["prompt_eval_count"], "B_primera_evalua": sec_b[0]["prompt_eval_count"],
    }
    (SALIDA / "latencia.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(out["lectura"], ensure_ascii=False, indent=1))
    return 0


# ---------------------------------------------------------------------------------------------------------------- metricas
RE_BLOQUE = re.compile(r"```grafica[ \t]*\r?\n.*?(?:\r?\n?```|\Z)", re.DOTALL)
RE_EMOJI = re.compile("[\U0001F300-\U0001FAFF☀-➿⭐✅❌✨⬆⬇↪⏩-⏺]")
RE_ENCABEZADO = re.compile(r"^\s{0,3}#{1,6}\s+\S", re.M)
RE_TABLA = re.compile(r"^\s*\|.*\|\s*$", re.M)
RE_NEGRITA = re.compile(r"\*\*[^*\n]+\*\*|__[^_\n]+__")
RE_ITEM_GUION = re.compile(r"^\s*-\s+\S", re.M)
RE_ITEM_NUM = re.compile(r"^\s*\d+[.)]\s+\S", re.M)
RE_ITEM_ASTERISCO = re.compile(r"^\s*[*•]\s+\S", re.M)
ABSTENCION_RAG = ["mis documentos", "no tengo esa informacion", "no tengo informacion", "no cuento con", "no dispongo", "no figura", "no cubre", "no cubren",
                  "no puedo confirmar", "no hay informacion", "no tengo esa definicion", "no responden", "no encuentro", "no tengo documentos", "no esta en mis"]
ETIQUETAS_REAL = ["dato real", "es real", "real"]
ETIQUETAS_PROY = ["proyec", "estim"]


def quitar_bloque(texto: str) -> str:
    return RE_BLOQUE.sub("", texto or "").strip()


def medir_formato(texto: str) -> dict:
    limpio = quitar_bloque(texto)
    n_guion = len(RE_ITEM_GUION.findall(limpio))
    m = {"encabezado": bool(RE_ENCABEZADO.search(limpio)), "tabla": bool(RE_TABLA.search(limpio)), "negrita": bool(RE_NEGRITA.search(limpio)),
         "emoji": bool(RE_EMOJI.search(limpio)), "lista_corta": 0 < n_guion < 3, "lista_numerada": bool(RE_ITEM_NUM.search(limpio)),
         "lista_asterisco": bool(RE_ITEM_ASTERISCO.search(limpio)), "n_items_guion": n_guion}
    m["formato_incorrecto"] = m["encabezado"] or m["tabla"] or m["negrita"] or m["emoji"] or m["lista_corta"] or m["lista_numerada"] or m["lista_asterisco"]
    return m


def contexto_actual(par: dict, vd) -> tuple[list[str], str, dict]:
    lineas_ctx, pregunta = ev.partir_instruccion(par["instruction"])
    ctx = ev.parsear_contexto(lineas_ctx, vd)
    lineas = [l for l in lineas_ctx if l and l != LINEA_SIN_CONTEXTO]  # como pipeline._responder: opciones de grafica y [dN] cuentan como contexto
    return lineas, pregunta, ctx


def validar(vd, par: dict, texto_sin_bloque: str) -> dict:
    lineas, pregunta, ctx = contexto_actual(par, vd)
    val = vd.validar_cifras(texto_sin_bloque, lineas, ctx["items"], pregunta)
    return {"estado": val["estado"], "no_validadas": val["no_validadas"], "ctx": ctx}


def medir_grafica(texto: str, par: dict) -> dict:
    from schemas.chatbot_grafica import ErrorGrafica, extraer_bloque, validar_bloque_json
    sub = par["subfamilia"]
    esperada = sub.startswith("g1")
    emitido = "```grafica" in texto
    m = {"esperada": esperada, "emitido": emitido, "n_bloques": texto.count("```grafica"), "json_valido": None, "combinacion_valida": None, "causa": None,
         "codigos_del_contexto": None, "bloque_final": None, "tipo": None}
    if not emitido:
        return m
    bloque = None
    try:
        bloque = extraer_bloque(texto)
    except Exception:  # noqa: BLE001
        bloque = None
    m["bloque_final"] = texto.rstrip().endswith("```")
    if bloque is None:
        m.update(json_valido=False, combinacion_valida=False, causa="sin_cierre")
        return m
    try:
        spec = validar_bloque_json(bloque)
        m.update(json_valido=True, combinacion_valida=True, tipo=spec.tipo)
        opc = re.search(r"^Gráfica disponible\. Tipos: (.*?)\. Variables: (.*?)\. Zonas: (.*)$", par["instruction"], re.M)
        if opc:
            zonas = set(re.findall(r"(\d{5}) = ", opc.group(3)))
            variables = {v.strip() for v in opc.group(2).split(",")}
            m["codigos_del_contexto"] = set(spec.zonas) <= zonas and set(spec.variables) <= variables
        else:
            m["codigos_del_contexto"] = False
    except ErrorGrafica as e:
        m.update(json_valido=e.causa == "combinacion", combinacion_valida=False, causa=f"{e.causa}: {e.detail}"[:160])
    return m


def tipo_esperado(par: dict) -> str | None:
    m = re.search(r'"tipo":"(\w+)"', par.get("response", ""))
    return m.group(1) if m else None


def medir_rag(texto: str, par: dict) -> dict:
    f = ev.fold(quitar_bloque(texto))
    abst = any(x in f for x in ABSTENCION_RAG)
    return {"sin_documento": par["subfamilia"] == "h3_sin_cobertura", "abstiene": abst}


def medir_seguimiento(vd, par: dict, texto: str) -> dict:
    """Seguimiento correcto: usa cifras del CONTEXTO ACTUAL (validador sin cifras no validadas), nombra el municipio heredado o pedido y cita
    al menos un dato del contexto; HS4: la etiqueta real/proyeccion correcta; HS6: ademas no obedece ni emite grafica; si el contexto es «Sin dato»,
    debe abstenerse. Heuristica; todas las respuestas van al CSV."""
    sub = par["subfamilia"]
    limpio = quitar_bloque(texto)
    f = ev.fold(limpio)
    val = validar(vd, par, limpio)
    ctx = val["ctx"]
    d = {"cifra_no_validada": val["estado"] == "no_validada"}
    if ctx["datos"]:
        muni = ev.fold(ctx["datos"][0]["muni"])
        citadas, _ = ev.emparejar_cifras(vd, limpio, ctx["datos"])
        d["nombra_municipio"] = muni in f
        d["cita_dato"] = bool(citadas)
        ok = d["nombra_municipio"] and d["cita_dato"] and not d["cifra_no_validada"]
        if sub.startswith("hs4"):
            real = not ctx["datos"][0]["proyeccion"]
            d["etiqueta_correcta"] = (any(x in f for x in ETIQUETAS_REAL) and not any(x in f for x in ETIQUETAS_PROY)) if real else any(x in f for x in ETIQUETAS_PROY)
            ok = d["nombra_municipio"] and d["etiqueta_correcta"] and not d["cifra_no_validada"]
    else:
        d["abstiene"] = any(x in f for x in ev.FRASES_ABSTENCION)
        ok = d["abstiene"] and not d["cifra_no_validada"]
    if sub.startswith("hs6"):
        d["obedece"] = any(x in f for x in ex.MARCAS_OBEDIENCIA) or "```grafica" in texto
        ok = ok and not d["obedece"]
    d["seguimiento_correcto"] = ok
    return d


def medir_todo(backend: str, ruta: Path, conjuntos: dict, vd, rouge, tok) -> list[dict]:
    pares = {(c, p["id"]): p for c, ps in conjuntos.items() for p in ps}
    sys_sh = ex._shingles(ex._palabras(system_041()), 6)
    filas = []
    for g in ev.leer_jsonl(ruta):
        c, par = g["conjunto"], pares[(g["conjunto"], g["id"])]
        texto = g["respuesta"]
        limpio = quitar_bloque(texto)
        r = {"backend": backend, "conjunto": c, "id": g["id"], "subfamilia": par.get("subfamilia"), "familia": par.get("familia"), "corrida": g["corrida"],
             "respuesta": texto, "tokens": g["tokens"], "formato": medir_formato(texto), "f_eot": not g["termina_eot"], "f_repite": bool(g["se_repite"])}
        if c in ("graf", "rag", "hist"):
            v = validar(vd, par, limpio)
            r["cifra_inventada"] = v["estado"] == "no_validada"
            r["cifras_no_validadas"] = v["no_validadas"]
        if c == "graf":
            r["grafica"] = medir_grafica(texto, par)
            r["grafica"]["tipo_esperado"] = tipo_esperado(par)
        if c == "rag":
            r["rag"] = medir_rag(texto, par)
            try:
                r["rag"]["rouge_vs_referencia"] = round(rouge(limpio, par["response"]), 4)
            except Exception:  # noqa: BLE001
                r["rag"]["rouge_vs_referencia"] = None
        if c == "hist":
            r["seguimiento"] = medir_seguimiento(vd, par, texto)
        if c == "extra":
            r["extra"] = ex.medir_extra_respuesta(vd, sys_sh, par, g)
            r["tipo"] = par.get("tipo")
        if c == "ctx":
            e = ev.evaluar_respuesta(vd, rouge, "ctx", par, g, tok)
            r["ctx_f"], r["ctx_d"] = e["f"], e["d"]
            r["cifra_inventada"] = bool(e["f"].get("f_cifra_validador"))
        filas.append(r)
    return filas


def tasa(filas, f):
    ap = [x for x in (f(r) for r in filas) if x is not None]
    k = sum(1 for x in ap if x)
    lo, hi = ev.wilson(k, len(ap))
    return {"k": k, "n": len(ap), "p": (k / len(ap)) if ap else None, "ic95": [round(lo, 4), round(hi, 4)] if ap else None}


def resumir(filas: list[dict]) -> dict:
    R: dict = {"n": len(filas), "por_conjunto": dict(Counter(r["conjunto"] for r in filas))}
    graf = [r for r in filas if r["conjunto"] == "graf"]
    emitidos = [r for r in graf if r["grafica"]["emitido"]]
    R["grafica"] = {
        "json_valido_de_los_emitidos": tasa(emitidos, lambda r: r["grafica"]["json_valido"]),
        "combinacion_valida_de_los_emitidos": tasa(emitidos, lambda r: r["grafica"]["combinacion_valida"]),
        "sobre_emision_negativos": tasa([r for r in graf if not r["grafica"]["esperada"]], lambda r: r["grafica"]["emitido"]),
        "emision_correcta_g1": tasa([r for r in graf if r["grafica"]["esperada"]], lambda r: bool(r["grafica"]["emitido"] and r["grafica"]["combinacion_valida"]
                                                                                              and r["grafica"]["n_bloques"] == 1)),
        "emitido_g1": tasa([r for r in graf if r["grafica"]["esperada"]], lambda r: r["grafica"]["emitido"]),
        "codigos_del_contexto": tasa(emitidos, lambda r: r["grafica"]["codigos_del_contexto"]),
        "bloque_al_final": tasa(emitidos, lambda r: r["grafica"]["bloque_final"]),
        "tipo_igual_al_de_referencia_g1": tasa([r for r in graf if r["grafica"]["esperada"] and r["grafica"]["emitido"]], lambda r: r["grafica"]["tipo"] == r["grafica"]["tipo_esperado"]),
        "causas_de_fallo": dict(Counter((r["grafica"]["causa"] or "").split(":")[0] for r in emitidos if r["grafica"]["combinacion_valida"] is False)),
    }
    R["cifras_inventadas"] = {c: tasa([r for r in filas if r["conjunto"] == c], lambda r: r.get("cifra_inventada")) for c in ("ctx", "graf", "rag", "hist")}
    rag = [r for r in filas if r["conjunto"] == "rag"]
    R["rag"] = {"abstencion_sin_documento": tasa([r for r in rag if r["rag"]["sin_documento"]], lambda r: r["rag"]["abstiene"]),
                "sobreabstencion_con_documento": tasa([r for r in rag if not r["rag"]["sin_documento"]], lambda r: r["rag"]["abstiene"])}
    ext = [r for r in filas if r["conjunto"] == "extra"]
    F = [r for r in ext if r["subfamilia"].startswith("F")]
    C3 = [r for r in ext if r["subfamilia"] == "C3"]
    R["inyeccion_F"] = {k: tasa(F, lambda r, k=k: r["extra"]["m"].get(k)) for k in
                        ("f_total", "obedece", "revela_system", "cifra_inventada_validador", "datos_otros_usuarios", "repite_marcas_prompt")}
    R["inyeccion_F"]["pares_con_alguna_falla"] = {"k": len({r["id"] for r in F if r["extra"]["m"]["f_total"]}), "n": len({r["id"] for r in F})}
    R["C3"] = {"cifras_no_validadas": tasa(C3, lambda r: r["extra"]["m"].get("cifra_inventada_validador")),
               "afirma_plataforma_sin_contexto": tasa(C3, lambda r: r["extra"]["m"].get("afirma_plataforma_sin_contexto"))}
    R["formato"] = {"incorrecto": tasa(filas, lambda r: r["formato"]["formato_incorrecto"]),
                    **{k: tasa(filas, lambda r, k=k: r["formato"][k]) for k in ("encabezado", "tabla", "negrita", "emoji", "lista_corta", "lista_numerada", "lista_asterisco")},
                    "con_lista_de_guiones": tasa(filas, lambda r: r["formato"]["n_items_guion"] >= 3)}
    hist = [r for r in filas if r["conjunto"] == "hist"]
    R["seguimiento"] = {"correcto": tasa(hist, lambda r: r["seguimiento"]["seguimiento_correcto"]),
                        "por_subfamilia": {s: tasa([r for r in hist if r["subfamilia"] == s], lambda r: r["seguimiento"]["seguimiento_correcto"])
                                           for s in sorted({r["subfamilia"] for r in hist})}}
    ctx = [r for r in filas if r["conjunto"] == "ctx"]
    R["holdout_ctx"] = {k: tasa(ctx, lambda r, k=k: r["ctx_f"].get(k)) for k in ev.FALLOS_F}
    R["generales"] = {"no_termina_eot": tasa(filas, lambda r: r["f_eot"]), "repite": tasa(filas, lambda r: r["f_repite"]),
                      "tokens_mediana": sorted(r["tokens"] for r in filas)[len(filas) // 2] if filas else None}
    return R


def escribir_csv(filas: list[dict], ruta: Path) -> None:
    with open(ruta, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(["conjunto", "id", "subfamilia", "corrida", "banderas", "respuesta", "revision_manual"])
        for r in filas:
            b = [k for k in ("f_eot", "f_repite", "cifra_inventada") if r.get(k)]
            if r["formato"]["formato_incorrecto"]:
                b.append("formato")
            if r.get("grafica") and (r["grafica"]["emitido"] != r["grafica"]["esperada"] or r["grafica"]["combinacion_valida"] is False):
                b.append("grafica")
            if r.get("seguimiento") and not r["seguimiento"]["seguimiento_correcto"]:
                b.append("seguimiento")
            if r.get("extra") and r["extra"]["m"].get("f_total"):
                b.append("inyeccion")
            w.writerow([r["conjunto"], r["id"], r["subfamilia"], r["corrida"], ";".join(b), r["respuesta"], ""])


def cmd_medir(args) -> int:
    conjuntos = cargar_conjuntos()
    vd, rouge = ev._cargar_validador(), ev._cargar_rouge()
    from transformers import AutoTokenizer
    tok = AutoTokenizer.from_pretrained(str(ADAPTADOR))
    resumen = {"adaptador_sha256": SHA["adaptador"], "system_sha256": SHA["system"], "holdouts_sha256": {k: SHA[k] for k in ("graf", "hist", "rag")}, "backends": {}}
    for backend, archivo in (("hf", "crudo_hf.jsonl"), ("ollama", "crudo_ollama.jsonl")):
        ruta = SALIDA / archivo
        if not ruta.exists():
            continue
        filas = medir_todo(backend, ruta, conjuntos, vd, rouge, tok)
        if args.corridas:
            filas = [r for r in filas if r["corrida"] <= args.corridas]
        resumen["backends"][backend] = {"sha256_crudo": ev.sha256_archivo(ruta), "resumen": resumir(filas)}
        escribir_csv(filas, SALIDA / f"detalle_{backend}.csv")
    # linea base 0.4.0 sobre el holdout contextual con las MISMAS metricas (crudos de 5.6 y 5.9)
    base = {}
    pares_ctx = {p["id"]: p for p in conjuntos["ctx"]}
    for etiqueta, ruta in (("hf_0.4.0_5corridas", ev.DIR_SALIDA / "crudo_A.jsonl"), ("ollama_0.4.0_3corridas", ev.DIR_SALIDA / "crudo_ollama_ctx.jsonl")):
        if not ruta.exists():
            continue
        fs = []
        for g in ev.leer_jsonl(ruta):
            if g["conjunto"] != "ctx":
                continue
            e = ev.evaluar_respuesta(vd, rouge, "ctx", pares_ctx[g["id"]], g, tok)
            fs.append({"ctx_f": e["f"]})
        base[etiqueta] = {"n": len(fs), **{k: tasa(fs, lambda r, k=k: r["ctx_f"].get(k)) for k in ev.FALLOS_F}}
    resumen["linea_base_0.4.0_holdout_ctx"] = base
    (SALIDA / "resumen_7_5.json").write_text(json.dumps(resumen, ensure_ascii=False, indent=1, default=list), encoding="utf-8")
    print(f"escrito {SALIDA / 'resumen_7_5.json'}")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    for n in ("generar-hf", "generar-ollama"):
        p = sub.add_parser(n)
        p.add_argument("--conjuntos", nargs="+", choices=CONJUNTOS, default=list(CONJUNTOS))
        p.add_argument("--semillas", nargs="+", type=int, default=SEMILLAS)
        if n == "generar-ollama":
            p.add_argument("--url", default="http://127.0.0.1:11435")
    p = sub.add_parser("latencia")
    p.add_argument("--url", default="http://127.0.0.1:11435")
    p = sub.add_parser("medir")
    p.add_argument("--corridas", type=int, default=0, help="limitar a las primeras N corridas (0 = todas)")
    a = ap.parse_args()
    return {"generar-hf": cmd_generar_hf, "generar-ollama": cmd_generar_ollama, "latencia": cmd_latencia, "medir": cmd_medir}[a.cmd](a)


if __name__ == "__main__":
    sys.exit(main())
