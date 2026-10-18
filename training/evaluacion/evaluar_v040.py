"""Paso 5.6: evaluacion extendida de 0.4.0 (SOLO MIDE: no juzga, no modifica modelos, datos, holdout, validador ni prompts).

Tres brazos, base Llama 3.2 3B Instruct en 4 bits NF4 (HF, no GGUF Q4_K_M; la comprobacion en Ollama es 5.9), un adaptador por proceso:
  A: adaptador 0.4.0 + system sp-0.4.0-1  -> holdout contextual (60) y holdout previo de 0.3.3 (28)
  B: adaptador 0.3.3 + system sp-0.4.0-1  -> holdout contextual (60)
  C: adaptador 0.3.3 + system de produccion de 0.3.3 (app/ollama_client.py) -> holdout previo (28)
Mensaje de usuario = campo `instruction` byte a byte. Muestreo: temperatura 0,3, top_p 0,9, top_k 40, penalizacion de repeticion 1,15 sobre
los ultimos 64 tokens, num_predict 400, num_ctx 2048, semillas 1-5 (cinco corridas por par).

Fases (subcomandos):
  generar --brazo A|B|C [--limite N]   GPU; escribe evaluacion/crudo_<brazo>.jsonl (reanudable, una linea por generacion, progreso cada 50)
  control                              GPU; repite 3 pares con la misma semilla y compara los tokens (determinismo)
  medir                                CPU; metricas, generaciones_<brazo>.jsonl, fallos.csv, por_par.csv, resumen.json, tablas.md, sha256

Uso (desde la raiz de techo360-chatbot, venv-formateo-5-4):
    python -u training/evaluacion/evaluar_v040.py generar --brazo A
"""
import argparse
import ast
import csv
import hashlib
import importlib.util
import json
import math
import os
import re
import statistics
import sys
import time
import unicodedata
from collections import Counter, defaultdict
from itertools import combinations
from pathlib import Path

RAIZ_CHATBOT = Path(__file__).resolve().parents[2]
RAIZ_MONO = RAIZ_CHATBOT.parent
DIR_R2 = RAIZ_MONO / "trabajo-dataset-0.4.0-r2"
DIR_SALIDA = DIR_R2 / "evaluacion"
HOLDOUT_CTX = DIR_R2 / "holdout_ctx_v0_4.jsonl"
HOLDOUT_PREVIO = RAIZ_CHATBOT / "dataset" / "holdout_v3_3.jsonl"
SYSTEM_SP = RAIZ_CHATBOT / "prompts" / "sp-0.4.0-1.txt"
OLLAMA_CLIENT = RAIZ_CHATBOT / "app" / "ollama_client.py"
MODELFILE_V33 = RAIZ_CHATBOT / "training" / "ollama" / "Modelfile.v3.3"
VALIDADOR = RAIZ_MONO / "techo360-backend" / "services" / "orquestador" / "validador_cifras.py"
ADAPTADORES = {"0.4.0": RAIZ_CHATBOT / "training" / "adapters" / "techo360-v0.4.0", "0.3.3": RAIZ_CHATBOT / "training" / "adapters" / "techo360-v3.3"}

SHA_ADAPTADOR_040 = "e7768dad2ed14f8197032dcc4e82860a01319655798ff0c63c7a41deda421ec6"
SHA_HOLDOUT_CTX = "d02c7ba7c8b0d101c231658aabed7aa3e1eb9768ab6cdc65a5fb357e85a1f711"
SHA_SYSTEM_SP = "b63287584676daa3ae514b90884fa8065eeb94f11881711f4517a8b02cfaa9ce"
SHA_HOLDOUT_PREVIO_PREFIJO = "7934a5c97d9e"  # linea-base-fase-0.md: holdout_v3_3.jsonl

BRAZOS = {  # brazo -> (adaptador, system, conjuntos)
    "A": ("0.4.0", "sp", ("ctx", "previo")),
    "B": ("0.3.3", "sp", ("ctx",)),
    "C": ("0.3.3", "prod", ("previo",)),
}
SEMILLAS = [1, 2, 3, 4, 5]
MODELO = "meta-llama/Llama-3.2-3B-Instruct"
FECHA = "18 Sep 2026"  # la misma que el entrenamiento y la cordura de 5.5
EOT_ID = 128009
TEMPERATURA, TOP_P, TOP_K, PENAL_REP, VENTANA_REP = 0.3, 0.9, 40, 1.15, 64
NUM_PREDICT, NUM_CTX = 400, 2048
FALLOS_F = ["f_cifra_validador", "f_cifra_estricta", "f_cobertura", "f_municipio", "f_abstencion", "f_sobreabstencion", "f_geografia",
            "f_sin_contexto", "f_fuera_referencia", "f_eot", "f_repite", "f_idioma"]


# ----------------------------------------------------------------------------------------------------------------------
# utilidades
# ----------------------------------------------------------------------------------------------------------------------
def sha256_archivo(ruta) -> str:
    h = hashlib.sha256()
    with open(ruta, "rb") as f:
        for bloque in iter(lambda: f.read(1 << 20), b""):
            h.update(bloque)
    return h.hexdigest()


def leer_jsonl(ruta) -> list[dict]:
    texto = Path(ruta).read_bytes().decode("utf-8")
    return [json.loads(l) for l in re.split(r"\r?\n", texto) if l.strip()]


def cargar_conjuntos() -> dict[str, list[dict]]:
    """-> {"ctx": [...], "previo": [...]}, cada fila con id, familia, subfamilia, instruction, response."""
    assert sha256_archivo(HOLDOUT_CTX) == SHA_HOLDOUT_CTX, "sha256 del holdout contextual distinto"
    assert sha256_archivo(HOLDOUT_PREVIO).startswith(SHA_HOLDOUT_PREVIO_PREFIJO), "sha256 del holdout previo distinto"
    ctx = leer_jsonl(HOLDOUT_CTX)
    previo = []
    for i, r in enumerate(leer_jsonl(HOLDOUT_PREVIO), 1):
        previo.append({"id": f"prev-{i:02d}", "familia": "con_fuente" if r.get("source") else "sin_fuente", "subfamilia": "previo",
                       "instruction": r["instruction"], "response": r["response"]})
    return {"ctx": ctx, "previo": previo}


def cargar_system_produccion() -> str:
    """SYSTEM_PROMPT de app/ollama_client.py (leido por ast, sin importar el modulo)."""
    arbol = ast.parse(OLLAMA_CLIENT.read_text(encoding="utf-8"))
    for nodo in arbol.body:
        if isinstance(nodo, ast.Assign) and any(getattr(t, "id", "") == "SYSTEM_PROMPT" for t in nodo.targets):
            return ast.literal_eval(nodo.value)
    raise RuntimeError("SYSTEM_PROMPT no encontrado en ollama_client.py")


def cargar_system_sp() -> str:
    assert sha256_archivo(SYSTEM_SP) == SHA_SYSTEM_SP, "sha256 del system sp-0.4.0-1 distinto"
    return SYSTEM_SP.read_bytes().decode("utf-8")  # crudo, como cargar_system()


def system_de(brazo: str) -> str:
    return cargar_system_sp() if BRAZOS[brazo][1] == "sp" else cargar_system_produccion()


def parametros_registrados() -> dict:
    """Opciones de muestreo de produccion tal como se leen de los archivos (ollama_client.py + Modelfile.v3.3)."""
    ocl = OLLAMA_CLIENT.read_text(encoding="utf-8")
    modelfile = {m.group(1): m.group(2) for m in re.finditer(r"^PARAMETER\s+(\w+)\s+(\S+)", MODELFILE_V33.read_text(encoding="utf-8"), re.M)}
    return {
        "ollama_client.NUM_PREDICT": int(re.search(r"^NUM_PREDICT\s*=\s*(\d+)", ocl, re.M).group(1)),
        "ollama_client.NUM_THREAD_POR_DEFECTO": int(re.search(r"^NUM_THREAD_POR_DEFECTO\s*=\s*(\d+)", ocl, re.M).group(1)),
        "ollama_client.options_enviadas": "solo num_predict y num_thread (el resto sale del Modelfile)",
        "Modelfile.v3.3": modelfile,
        "usado_aqui": {"temperature": TEMPERATURA, "top_p": TOP_P, "top_k": TOP_K, "repeat_penalty": PENAL_REP, "repeat_last_n": VENTANA_REP,
                       "num_predict": NUM_PREDICT, "num_ctx": NUM_CTX, "num_thread": "no aplica (GPU)", "semillas": SEMILLAS},
    }


def fold(s: str) -> str:
    """Minusculas y sin tildes, conservando la longitud (para ubicar posiciones)."""
    return "".join(unicodedata.normalize("NFD", c)[0] for c in (s or "")).lower()


def wilson(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    if n == 0:
        return (float("nan"), float("nan"))
    p = k / n
    d = 1 + z * z / n
    centro = (p + z * z / (2 * n)) / d
    mitad = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (max(0.0, centro - mitad), min(1.0, centro + mitad))


# ----------------------------------------------------------------------------------------------------------------------
# generacion (GPU)
# ----------------------------------------------------------------------------------------------------------------------
def cargar_modelo(adaptador: Path):
    import types
    try:
        import datasets  # noqa: F401
    except Exception:  # noqa: BLE001
        import importlib.machinery
        stub = types.ModuleType("datasets")
        stub.Dataset, stub.IterableDataset = type("Dataset", (), {}), type("IterableDataset", (), {})
        stub.__spec__, stub.__version__ = importlib.machinery.ModuleSpec("datasets", None), "0.0-stub"
        sys.modules["datasets"] = stub
    import torch
    from peft import PeftModel
    from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig
    tok = AutoTokenizer.from_pretrained(str(adaptador))
    bnb = BitsAndBytesConfig(load_in_4bit=True, bnb_4bit_quant_type="nf4", bnb_4bit_compute_dtype=torch.bfloat16)
    base = AutoModelForCausalLM.from_pretrained(MODELO, quantization_config=bnb, device_map={"": 0}, dtype=torch.bfloat16)
    modelo = PeftModel.from_pretrained(base, str(adaptador)).eval()
    return torch, tok, modelo


def crear_generador(torch, tok, modelo):
    from transformers import LogitsProcessor, LogitsProcessorList

    class PenalizaRepeticion(LogitsProcessor):
        """Estilo llama.cpp: sobre los ultimos `ventana` tokens (prompt incluido), logit>0 se divide y logit<0 se multiplica por la penalizacion."""

        def __init__(self, penal, ventana):
            self.penal, self.ventana = penal, ventana

        def __call__(self, input_ids, scores):
            ids = input_ids[:, -self.ventana:]
            sc = torch.gather(scores, 1, ids)
            sc = torch.where(sc > 0, sc / self.penal, sc * self.penal)
            return scores.scatter(1, ids, sc)

    def generar(system: str, usuario: str, semilla: int) -> dict:
        msgs = [{"role": "system", "content": system}, {"role": "user", "content": usuario}]
        prompt = tok.apply_chat_template(msgs, tokenize=False, add_generation_prompt=True, date_string=FECHA)
        ids = tok(prompt, add_special_tokens=False, return_tensors="pt").to(modelo.device)
        torch.manual_seed(semilla)
        torch.cuda.manual_seed_all(semilla)
        t0 = time.time()
        with torch.no_grad():
            out = modelo.generate(**ids, do_sample=True, temperature=TEMPERATURA, top_p=TOP_P, top_k=TOP_K, max_new_tokens=NUM_PREDICT,
                                  logits_processor=LogitsProcessorList([PenalizaRepeticion(PENAL_REP, VENTANA_REP)]),
                                  eos_token_id=[EOT_ID, tok.eos_token_id], pad_token_id=tok.eos_token_id)
        nuevos = out[0][ids["input_ids"].shape[1]:].tolist()
        termina = bool(nuevos) and nuevos[-1] == EOT_ID
        texto = tok.decode([t for t in nuevos if t != EOT_ID], skip_special_tokens=False)
        return {"respuesta": texto, "tokens_prompt": int(ids["input_ids"].shape[1]), "tokens": len(nuevos), "termina_eot": termina,
                "se_repite": se_repite(nuevos), "llego_al_tope": len(nuevos) >= NUM_PREDICT and not termina,
                "ids_sha256": hashlib.sha256(json.dumps(nuevos).encode()).hexdigest(), "segundos": round(time.time() - t0, 2)}

    return generar


def se_repite(ids: list[int]) -> bool:
    """Un bloque de 8 tokens aparece 3 o mas veces (el mismo criterio que la cordura de 5.5)."""
    bloques = Counter(tuple(ids[i:i + 8]) for i in range(len(ids) - 7))
    return any(v >= 3 for v in bloques.values())


def cmd_generar(args) -> int:
    brazo = args.brazo
    adaptador_nombre, _, conjuntos_brazo = BRAZOS[brazo]
    adaptador = ADAPTADORES[adaptador_nombre]
    if adaptador_nombre == "0.4.0":
        assert sha256_archivo(adaptador / "adapter_model.safetensors") == SHA_ADAPTADOR_040, "sha256 del adaptador 0.4.0 distinto"
    conjuntos = cargar_conjuntos()
    system = system_de(brazo)
    DIR_SALIDA.mkdir(parents=True, exist_ok=True)
    ruta = DIR_SALIDA / f"crudo_{brazo}.jsonl"
    hechas = set()
    if ruta.exists():
        for g in leer_jsonl(ruta):
            hechas.add((g["conjunto"], g["id"], g["corrida"]))
    tareas = [(c, par, s) for c in conjuntos_brazo for par in conjuntos[c] for s in SEMILLAS if (c, par["id"], s) not in hechas]
    if args.limite:
        tareas = tareas[:args.limite]
    total = sum(len(conjuntos[c]) for c in conjuntos_brazo) * len(SEMILLAS)
    print(f"brazo {brazo}: adaptador {adaptador_nombre}, {len(hechas)} hechas, {len(tareas)} por hacer de {total}", flush=True)
    if not tareas:
        return 0
    torch, tok, modelo = cargar_modelo(adaptador)
    generar = crear_generador(torch, tok, modelo)
    t_ini, n = time.time(), 0
    with open(ruta, "a", encoding="utf-8", newline="\n") as f:
        for conjunto, par, semilla in tareas:
            g = generar(system, par["instruction"], semilla)
            f.write(json.dumps({"brazo": brazo, "conjunto": conjunto, "id": par["id"], "corrida": semilla, "semilla": semilla, **g}, ensure_ascii=False) + "\n")
            f.flush()
            n += 1
            if n % 50 == 0:
                prog = {"brazo": brazo, "hechas": len(hechas) + n, "total": total, "minutos": round((time.time() - t_ini) / 60, 1),
                        "vram_max_mb": round(torch.cuda.max_memory_reserved() / 2 ** 20)}
                (DIR_SALIDA / f"progreso_{brazo}.json").write_text(json.dumps(prog), encoding="utf-8")
                print(f"  checkpoint: {prog}", flush=True)
            if n <= 3 or n % 10 == 0:
                print(f"[{brazo}] {conjunto} {par['id']} s{semilla} {g['tokens']} tok {g['segundos']}s  ({len(hechas) + n}/{total}; {(time.time() - t_ini) / 60:.1f} min)", flush=True)
    print(f"listo brazo {brazo}: {n} generaciones en {(time.time() - t_ini) / 60:.1f} min; VRAM reservada max {torch.cuda.max_memory_reserved() / 2 ** 20:.0f} MB", flush=True)
    return 0


def cmd_control(args) -> int:
    """Determinismo: 3 pares con la misma semilla, dos veces cada uno; ademas se compara con la corrida original si existe."""
    conjuntos = cargar_conjuntos()
    system = system_de("A")
    torch, tok, modelo = cargar_modelo(ADAPTADORES["0.4.0"])
    generar = crear_generador(torch, tok, modelo)
    previo = {}
    ruta = DIR_SALIDA / "crudo_A.jsonl"
    if ruta.exists():
        previo = {(g["conjunto"], g["id"], g["corrida"]): g for g in leer_jsonl(ruta)}
    elegidos = [("ctx", "hctx-A1-001"), ("ctx", "hctx-A5-023"), ("previo", "prev-05")]
    pares = {c: {p["id"]: p for p in conjuntos[c]} for c in conjuntos}
    resultados = []
    for conjunto, pid in elegidos:
        par = pares[conjunto][pid]
        g1, g2 = generar(system, par["instruction"], 3), generar(system, par["instruction"], 3)
        orig = previo.get((conjunto, pid, 3))
        r = {"conjunto": conjunto, "id": pid, "semilla": 3, "tokens": g1["tokens"], "repeticion_1_igual_2": g1["ids_sha256"] == g2["ids_sha256"] and g1["respuesta"] == g2["respuesta"],
             "igual_a_corrida_original": (orig["ids_sha256"] == g1["ids_sha256"]) if orig else None}
        resultados.append(r)
        print(r, flush=True)
    salida = {"descripcion": "mismo par, misma semilla 3, brazo A (0.4.0 + sp-0.4.0-1), dos generaciones seguidas en el mismo proceso; y contra la corrida original de la semilla 3",
              "resultados": resultados, "todos_identicos": all(r["repeticion_1_igual_2"] for r in resultados)}
    (DIR_SALIDA / "control_determinismo.json").write_text(json.dumps(salida, ensure_ascii=False, indent=1), encoding="utf-8")
    return 0


# ----------------------------------------------------------------------------------------------------------------------
# metricas (CPU)
# ----------------------------------------------------------------------------------------------------------------------
def _cargar_validador():
    spec = importlib.util.spec_from_file_location("validador_cifras_4_5", VALIDADOR)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod  # dataclass necesita el modulo registrado
    spec.loader.exec_module(mod)
    return mod


def _cargar_rouge():
    sys.path.insert(0, str(RAIZ_CHATBOT / "training"))
    from metrica_rouge_l import rouge_l_f1  # noqa: E402
    return rouge_l_f1


DEPARTAMENTOS = sorted(["amazonas", "antioquia", "arauca", "atlantico", "bolivar", "boyaca", "caldas", "caqueta", "casanare", "cauca", "cesar", "choco",
                        "cordoba", "cundinamarca", "guainia", "guaviare", "huila", "la guajira", "magdalena", "meta", "narino", "norte de santander",
                        "putumayo", "quindio", "risaralda", "san andres", "santander", "sucre", "tolima", "valle del cauca", "vaupes", "vichada", "bogota"],
                       key=len, reverse=True)
FRASES_ABSTENCION = ["no tengo", "no cuento", "no dispongo", "no hay ", "no existe", "no existen", "no puedo", "no se puede", "sin dato", "no figura",
                     "no esta disponible", "no encuentro", "no registra", "no voy a", "fuera del", "fuera de", "no contamos", "no es posible",
                     "no tiene dato", "no se cuenta", "no se dispone", "no hay datos", "no cubre", "no esta en", "no hay informacion"]
ES = set("el la los las de del que en y un una es por para con no se su al como mas o sus lo son esta hay dato datos municipio año".split())
EN = set("the of and to in is that for it with as on are this not be by or an you your have".split())

_RE_DATO = re.compile(r"^\[c(?P<n>\d+)\]\s+(?P<var>[^,]+),\s+(?P<muni>.+?)\s\((?P<dep>[^()]+)\),\s+(?P<anio>\d{4})(?:\s+\([^)]*\))?:\s+(?P<val>-?[\d.,]+)\s*(?P<uni>%|hab/km²)?")
_RE_SIN = re.compile(r"^Sin dato para (?P<var>[^,]+),\s+(?P<muni>.+?)\s\((?P<dep>[^()]+)\),\s+(?P<anio>\d{4}):\s+(?P<motivo>.*)$")
_RE_UBIC = re.compile(r"^Ubicación:\s+(?P<muni>.+?)\s+pertenece al departamento de\s+(?P<dep>.+?)\.?$")
_RE_OMITIDOS = re.compile(r"^Se omitieron \d+ datos")
SIN_CONTEXTO = "Sin datos disponibles para esta consulta."


def partir_instruccion(instruction: str) -> tuple[list[str], str]:
    m = re.match(r"^CONTEXTO\n(?P<ctx>.*?)\n\nPREGUNTA DEL USUARIO\n(?P<preg>.*)$", instruction, re.S)
    if not m:
        return [], instruction  # holdout previo: la instruccion es la pregunta sola
    return m.group("ctx").split("\n"), m.group("preg")


def parsear_contexto(lineas: list[str], vd) -> dict:
    datos, sin_dato, ubic, sin_ctx, no_clasificadas = [], [], [], False, []
    for l in lineas:
        if l.strip() == SIN_CONTEXTO:
            sin_ctx = True
        elif (m := _RE_DATO.match(l)):
            valor, dec = vd._parsear(m.group("val").rstrip(".,"))
            datos.append({"id": f"c{m.group('n')}", "variable": fold(m.group("var")), "muni": m.group("muni"), "dep": m.group("dep"), "anio": int(m.group("anio")),
                          "valor": valor, "decimales": dec, "unidad": m.group("uni"), "proyeccion": "Proyección" in l})
        elif (m := _RE_SIN.match(l)):
            sin_dato.append({"variable": fold(m.group("var")), "muni": m.group("muni"), "dep": m.group("dep"), "anio": int(m.group("anio"))})
        elif (m := _RE_UBIC.match(l)):
            ubic.append({"muni": m.group("muni"), "dep": m.group("dep")})
        elif _RE_OMITIDOS.match(l):
            pass
        elif l.strip():
            no_clasificadas.append(l)
    entidades = {}
    for fuente in (datos, sin_dato, ubic):
        for d in fuente:
            entidades[(fold(d["muni"]), fold(d["dep"]))] = {"muni": d["muni"], "dep": d["dep"]}
    items = [{"id": d["id"], "variable": d["variable"], "codigodivipola": f"{fold(d['muni'])}|{fold(d['dep'])}", "anio": d["anio"], "valor": d["valor"]} for d in datos]
    return {"datos": datos, "sin_dato": sin_dato, "ubic": ubic, "sin_ctx": sin_ctx, "entidades": entidades, "items": items, "no_clasificadas": no_clasificadas}


def _deptos_en(texto_fold: str) -> list[tuple[int, str]]:
    """(posicion, depto) de cada departamento mencionado; los nombres largos se anulan primero (norte de santander antes que santander)."""
    t = texto_fold
    hallados = []
    for d in DEPARTAMENTOS:
        for m in re.finditer(r"(?<![a-z])" + re.escape(d) + r"(?![a-z])", t):
            hallados.append((m.start(), d))
            t = t[:m.start()] + " " * len(d) + t[m.end():]
    return sorted(hallados)


def _ocurrencias(texto_fold: str, nombre_fold: str) -> list[int]:
    return [m.start() for m in re.finditer(r"(?<![a-z])" + re.escape(nombre_fold) + r"(?![a-z])", texto_fold)]


def emparejar_cifras(vd, respuesta: str, datos: list[dict]) -> tuple[list[tuple[dict, object]], list[dict]]:
    """Asigna a cada linea de datos del contexto UNA cifra de la respuesta que la cite (cada cifra se usa una vez)."""
    numeros = vd.extraer_numeros(respuesta)
    usados, pares, sin_cita = set(), [], []
    for d in datos:
        for i, n in enumerate(numeros):
            if i not in usados and not (n.entero_sin_formato and 2000 <= n.valor <= 2042 and int(n.valor) == d["anio"]) and vd._coincide(n, d["valor"]):
                usados.add(i)
                pares.append((d, n))
                break
        else:
            sin_cita.append(d)
    return pares, sin_cita


def posicion_de_numero(respuesta: str, n) -> int:
    return respuesta.find(n.texto)


def evaluar_municipio(vd, resp: str, ctx: dict, pregunta: str, citados) -> dict:
    """Exactitud de municipio/departamento. Errores: (a) 'X (Depto)' con un depto que no es el del municipio en el contexto, o municipio
    desconocido; (b) departamento mencionado que no es del contexto; (c) cifra atribuida al municipio equivocado cuando hay >=2 entidades."""
    ents = ctx["entidades"]
    rf, pf = fold(resp), fold(pregunta)
    errores = []
    nombres = {}  # muni_fold -> set(dep_fold)
    for (m, d) in ents:
        nombres.setdefault(m, set()).add(d)
    deps_ctx = {d for (_, d) in ents}
    # (a) patron "X (Y)" con Y departamento
    for m in re.finditer(r"\(([^()]+)\)", rf):
        y = m.group(1).strip()
        if y not in DEPARTAMENTOS:
            continue
        previo = rf[:m.start()].rstrip()
        casados = [mn for mn in nombres if previo.endswith(mn) and (len(previo) == len(mn) or not previo[-len(mn) - 1].isalpha())]
        if not casados:
            palabras = re.findall(r"[a-z]+", previo)[-2:]
            if not any(w in pf for w in palabras[-1:]) and not (palabras and palabras[-1] in {"departamento", "de"}):
                errores.append(f"municipio_fuera_de_contexto:'{previo[-30:].strip()} ({y})'")
        elif not any(y in nombres[mn] for mn in casados):
            errores.append(f"depto_incorrecto:'{casados[0]} ({y})' (contexto: {sorted(nombres[casados[0]])})")
    # (b) departamentos mencionados fuera del contexto
    permitidos = deps_ctx | set(nombres) | {d for _, d in _deptos_en(pf)}
    for pos, d in _deptos_en(rf):
        if d not in permitidos:
            errores.append(f"depto_fuera_de_contexto:'{d}'")
    # (c) atribucion de cifras entre >=2 entidades
    atribucion = None
    if len(ents) >= 2 and ctx["datos"] and citados:
        menciones = []  # (inicio, fin, entidad)
        for (m, d) in ents:
            if len(nombres[m]) == 1:  # el nombre identifica a la entidad
                menciones += [(p, p + len(m), (m, d)) for p in _ocurrencias(rf, m)]
            if sum(1 for (_, dd) in ents if dd == d) == 1:  # el departamento identifica a la entidad
                menciones += [(p, p + len(d), (m, d)) for p in _ocurrencias(rf, d)]
        if menciones:
            atribucion = True
            valores_por_ent = defaultdict(set)
            for d in ctx["datos"]:
                valores_por_ent[(fold(d["muni"]), fold(d["dep"]))].add(round(d["valor"], 6))
            usadas = defaultdict(int)  # texto de la cifra -> cuantas apariciones ya asignadas
            for linea, n in citados:
                posiciones = [mm.start() for mm in re.finditer(re.escape(n.texto), resp)]
                pos = posiciones[min(usadas[n.texto], len(posiciones) - 1)] if posiciones else -1
                usadas[n.texto] += 1
                ent = (fold(linea["muni"]), fold(linea["dep"]))
                if pos < 0 or any(e != ent and round(linea["valor"], 6) in v for e, v in valores_por_ent.items()):
                    continue  # valor repetido en otra entidad: ambiguo, no se juzga
                cortes = [mm.end() for mm in re.finditer(r"(?<=[.!?])\s|\n", rf[:pos])]
                inicio_oracion = cortes[-1] if cortes else 0
                antes = [mn for mn in menciones if inicio_oracion <= mn[0] and mn[1] <= pos]
                despues = [mn for mn in menciones if mn[0] >= pos]
                siguiente = min(despues, key=lambda mn: mn[0]) if despues else None
                fin_numero = pos + len(n.texto)
                if siguiente and re.fullmatch(r"\s*(?:%|hab/km²)?\s*(?:en|de|para)\s+(?:el\s+municipio\s+de\s+)?(?:[a-z]+\s+){0,3}\(?\s*", rf[fin_numero:siguiente[0]]):
                    cercana = siguiente[2]  # «17,1 % en Chima (Santander)»: la cifra precede a su entidad
                elif antes:
                    cercana = max(antes, key=lambda mn: mn[1])[2]  # la mencion anterior mas proxima
                elif despues:
                    cercana = min(despues, key=lambda mn: mn[0])[2]
                else:
                    continue
                if cercana != ent:
                    atribucion = False
                    errores.append(f"cifra_atribuida_a_otro:'{n.texto}' es de {linea['muni']} ({linea['dep']}) pero queda junto a {cercana[0]} ({cercana[1]})")
    cita_depto = None
    if ents:
        cita_depto = all(d in rf for (_, d) in ents) if ents else None
    return {"error": bool(errores), "errores": errores, "atribucion_ok": atribucion, "cita_depto": cita_depto}


def espanol(texto: str) -> bool:
    palabras = re.findall(r"[a-záéíóúüñ]+", texto.lower())
    es, en = sum(p in ES for p in palabras), sum(p in EN for p in palabras)
    if len(palabras) < 3:
        return en == 0
    return es > 2 * en and es >= 1


def evaluar_respuesta(vd, rouge, conjunto: str, par: dict, g: dict) -> dict:
    resp, instruction = g["respuesta"], par["instruction"]
    lineas, pregunta = partir_instruccion(instruction)
    ctx = parsear_contexto(lineas, vd)
    m = {f: None for f in FALLOS_F}
    det = {}
    # --- cifras (validador 4.5 del orquestador, con el contexto del par) ---
    ref_lineas = [l for l in par["response"].split("\n")] if conjunto == "previo" else None
    val = vd.validar_cifras(resp, lineas if conjunto == "ctx" else [SIN_CONTEXTO], ctx["items"], pregunta)
    m["f_cifra_validador"] = val["estado"] == "no_validada"
    det["cifras_no_validadas"] = val["no_validadas"]
    # criterio estricto: todo numero de la respuesta (anios incluidos) esta en el contexto o la pregunta, sin redondeo ni derivados
    base_nums = vd.extraer_numeros("\n".join(lineas) + "\n" + pregunta)
    fuera = [n.texto for n in vd.extraer_numeros(resp) if not any(abs(abs(n.valor) - abs(b.valor)) < 1e-9 for b in base_nums)]
    m["f_cifra_estricta"] = bool(fuera)
    det["cifras_estrictas_fuera"] = fuera
    if conjunto == "previo":
        vr = vd.validar_cifras(resp, ref_lineas, None, pregunta)
        m["f_fuera_referencia"] = vr["estado"] == "no_validada"
        det["cifras_fuera_de_referencia"] = vr["no_validadas"]
        det["rouge_l"] = round(rouge(resp, par["response"]), 4)
    # --- forma ---
    palabras = len(re.findall(r"\w+", resp))
    det["palabras"] = palabras
    m["f_eot"] = not g["termina_eot"]
    m["f_repite"] = bool(g["se_repite"])
    m["f_idioma"] = not espanol(resp)
    det["llego_al_tope"] = bool(g["llego_al_tope"])
    if conjunto == "ctx":
        rf = fold(resp)
        hay_datos, hay_sin = bool(ctx["datos"]), bool(ctx["sin_dato"])
        frase = any(f in rf for f in FRASES_ABSTENCION)
        pares_citados, sin_cita = emparejar_cifras(vd, resp, ctx["datos"]) if hay_datos else ([], [])
        if hay_datos:
            cobertura = len(pares_citados) / len(ctx["datos"])
            det["cobertura"] = round(cobertura, 4)
            det["datos_sin_citar"] = [f"{d['id']}:{d['valor']}" for d in sin_cita]
            m["f_cobertura"] = cobertura < 1.0
        # municipio / departamento
        if ctx["entidades"]:
            r = evaluar_municipio(vd, resp, ctx, pregunta, pares_citados)
            m["f_municipio"] = r["error"]
            det["municipio_errores"] = r["errores"]
            det["cita_depto"] = r["cita_depto"]
        # abstencion (pares con linea "Sin dato para")
        if hay_sin:
            anios_ok = {int(n.valor) for n in vd.extraer_numeros("\n".join(lineas) + "\n" + pregunta) if n.entero_sin_formato and 1900 <= n.valor <= 2100}
            valores_ctx = [d["valor"] for d in ctx["datos"]]
            extra = [n.texto for n in vd.extraer_numeros(resp)
                     if not (n.entero_sin_formato and int(n.valor) in anios_ok) and not any(vd._coincide(n, v) for v in valores_ctx)]
            det["abstencion_cifras_extra"] = extra
            det["abstencion_frase"] = frase
            m["f_abstencion"] = bool(extra) or not frase
        # sobreabstencion: hay dato, no se pide abstenerse, y la respuesta se abstiene sin citar ninguna cifra del contexto
        if hay_datos and not hay_sin:
            m["f_sobreabstencion"] = frase and not pares_citados
        # geografia (pares de ubicacion D)
        if par["familia"] == "D":
            esperados = {fold(d) for (_, d) in ctx["entidades"]}
            mencionados = {d for _, d in _deptos_en(rf)}
            m["f_geografia"] = not (esperados <= mencionados and not (mencionados - esperados - {d for _, d in _deptos_en(fold(pregunta))}))
            det["geo_esperados"], det["geo_mencionados"] = sorted(esperados), sorted(mencionados)
        # sin contexto (bloque vacio)
        if ctx["sin_ctx"]:
            m["f_sin_contexto"] = m["f_cifra_validador"]
    det["tiene_datos"] = bool(ctx["datos"])
    return {"f": m, "d": det}


def cmd_medir(args) -> int:
    vd, rouge = _cargar_validador(), _cargar_rouge()
    conjuntos = cargar_conjuntos()
    por_id = {c: {p["id"]: p for p in conjuntos[c]} for c in conjuntos}
    todo = []  # filas con metricas
    for brazo in "ABC":
        ruta = DIR_SALIDA / f"crudo_{brazo}.jsonl"
        if not ruta.exists():
            print(f"(sin crudo_{brazo}.jsonl)")
            continue
        filas = leer_jsonl(ruta)
        esperado = sum(len(conjuntos[c]) for c in BRAZOS[brazo][2]) * len(SEMILLAS)
        print(f"brazo {brazo}: {len(filas)} generaciones de {esperado} esperadas")
        sin_clasificar = Counter()
        with open(DIR_SALIDA / f"generaciones_{brazo}.jsonl", "w", encoding="utf-8", newline="\n") as f:
            for g in filas:
                par = por_id[g["conjunto"]][g["id"]]
                r = evaluar_respuesta(vd, rouge, g["conjunto"], par, g)
                fila = {"id": g["id"], "brazo": brazo, "conjunto": g["conjunto"], "familia": par["familia"], "subfamilia": par["subfamilia"], "corrida": g["corrida"],
                        "respuesta": g["respuesta"], "tokens": g["tokens"], "termina_eot": g["termina_eot"], "se_repite": g["se_repite"],
                        "llego_al_tope": g["llego_al_tope"], "metricas": r["f"], "detalle": r["d"]}
                f.write(json.dumps(fila, ensure_ascii=False) + "\n")
                todo.append(fila)
                if g["conjunto"] == "ctx":
                    for l in parsear_contexto(partir_instruccion(par["instruction"])[0], vd)["no_clasificadas"]:
                        sin_clasificar[l] += 1
        if sin_clasificar:
            print("  lineas de contexto sin clasificar:", dict(sin_clasificar))
    escribir_resultados(todo, por_id)
    return 0


# ----------------------------------------------------------------------------------------------------------------------
# agregados, tablas y archivos de salida
# ----------------------------------------------------------------------------------------------------------------------
def tasa(filas, clave):
    aplicables = [r for r in filas if r["metricas"].get(clave) is not None]
    k = sum(1 for r in aplicables if r["metricas"][clave])
    n = len(aplicables)
    lo, hi = wilson(k, n)
    return {"k": k, "n": n, "p": (k / n if n else None), "lo": lo, "hi": hi}


def fmt(t) -> str:
    if t["n"] == 0:
        return "n/a"
    return f"{t['k']}/{t['n']} = {100 * t['p']:.1f} % [{100 * t['lo']:.1f}; {100 * t['hi']:.1f}]"


def tasa_pares(filas, clave, modo="alguna"):
    """Unidad = par: 'alguna' = fallo en >=1 de las corridas; 'todas' = fallo en todas."""
    por_par = defaultdict(list)
    for r in filas:
        if r["metricas"].get(clave) is not None:
            por_par[(r["brazo"], r["conjunto"], r["id"])].append(r["metricas"][clave])
    k = sum(1 for v in por_par.values() if (any(v) if modo == "alguna" else all(v)))
    n = len(por_par)
    lo, hi = wilson(k, n)
    return {"k": k, "n": n, "p": (k / n if n else None), "lo": lo, "hi": hi}


def percentil(xs, q):
    xs = sorted(xs)
    if not xs:
        return None
    i = (len(xs) - 1) * q
    lo, hi = int(math.floor(i)), int(math.ceil(i))
    return xs[lo] + (xs[hi] - xs[lo]) * (i - lo)


def tokens_texto(t: str) -> set:
    return set(re.findall(r"\w+", fold(t)))


def consistencia(filas):
    por_par = defaultdict(list)
    for r in filas:
        por_par[r["id"]].append(r)
    distintas, jacc, unanimes = [], [], defaultdict(list)
    for pid, rs in por_par.items():
        textos = [re.sub(r"\s+", " ", fold(r["respuesta"])).strip() for r in rs]
        distintas.append(len(set(textos)))
        ts = [tokens_texto(r["respuesta"]) for r in rs]
        for a, b in combinations(ts, 2):
            jacc.append(len(a & b) / len(a | b) if (a | b) else 1.0)
        for clave in FALLOS_F:
            vals = [r["metricas"][clave] for r in rs if r["metricas"][clave] is not None]
            if vals:
                unanimes[clave].append(len(set(vals)) == 1)
        cualquiera = [any(v for v in r["metricas"].values() if v) for r in rs]
        unanimes["__alguna_falla__"].append(len(set(cualquiera)) == 1)
    return {"pares": len(por_par), "identicas_5": sum(1 for d in distintas if d == 1), "mediana_distintas": statistics.median(distintas) if distintas else None,
            "jaccard_medio": (sum(jacc) / len(jacc)) if jacc else None,
            "unanimidad": {k: (sum(v), len(v)) for k, v in unanimes.items()}}


def escribir_resultados(todo: list[dict], por_id: dict) -> None:
    grupos = defaultdict(list)  # (brazo, conjunto) -> filas
    for r in todo:
        grupos[(r["brazo"], r["conjunto"])].append(r)
    resumen = {"parametros": parametros_registrados(), "grupos": {}}
    md = []
    metricas_ctx = [("f_cifra_validador", "Cifras inventadas (validador 4.5: `no_validada`)"), ("f_cifra_estricta", "Cifras fuera de contexto/pregunta (criterio estricto)"),
                    ("f_cobertura", "Cobertura incompleta (algún valor del contexto sin citar)"), ("f_municipio", "Error de municipio/departamento"),
                    ("f_abstencion", "Fallo de abstención (cifra o sin explicar la falta)"), ("f_sobreabstencion", "Sobreabstención (hay dato y no lo cita)"),
                    ("f_geografia", "Fallo de geografía (pares D)"), ("f_sin_contexto", "Cifra inventada ante bloque vacío (pares C)"),
                    ("f_eot", "No termina con `<|eot_id|>`"), ("f_repite", "Repetición (bloque de 8 tokens ≥3 veces)"), ("f_idioma", "No es español")]
    metricas_previo = [("f_cifra_validador", "Cifras no validadas contra contexto vacío (incluye conocimiento legítimo)"), ("f_fuera_referencia", "Cifras fuera de la referencia y la pregunta"),
                       ("f_eot", "No termina con `<|eot_id|>`"), ("f_repite", "Repetición"), ("f_idioma", "No es español")]
    for (brazo, conjunto), filas in sorted(grupos.items()):
        metricas = metricas_ctx if conjunto == "ctx" else metricas_previo
        fams = sorted({r["familia"] for r in filas})
        sub = {"total": filas, **{f: [r for r in filas if r["familia"] == f] for f in fams}}
        info = {"n_respuestas": len(filas), "n_pares": len({r['id'] for r in filas}), "por_grupo": {}}
        md.append(f"\n### Brazo {brazo} · holdout {'contextual (60 pares)' if conjunto == 'ctx' else 'previo de 0.3.3 (28 pares)'} · {len(filas)} respuestas\n")
        md.append("Fallos / respuestas aplicables = tasa [IC Wilson 95 %]. La unidad es la respuesta (5 por par); las 5 corridas de un par no son independientes, así que el IC es optimista (ver también «pares con ≥1 fallo»).\n")
        cab = "| Métrica | Total | " + " | ".join(fams) + " |"
        md.append(cab)
        md.append("|" + "---|" * (2 + len(fams)))
        for clave, nombre in metricas:
            celdas = []
            for g in ["total"] + fams:
                t = tasa(sub[g], clave)
                info["por_grupo"].setdefault(g, {})[clave] = t
                celdas.append(fmt(t))
            if all(c == "n/a" for c in celdas):
                continue
            md.append(f"| {nombre} | " + " | ".join(celdas) + " |")
        # pares con fallo
        md.append("\n**Pares con ≥1 fallo en las 5 corridas / pares aplicables** (unidad = par):\n")
        md.append("| Métrica | Total | " + " | ".join(fams) + " |")
        md.append("|" + "---|" * (2 + len(fams)))
        for clave, nombre in metricas:
            celdas = []
            for g in ["total"] + fams:
                t = tasa_pares(sub[g], clave)
                info["por_grupo"][g][clave + "__pares"] = t
                celdas.append(fmt(t))
            if all(c == "n/a" for c in celdas):
                continue
            md.append(f"| {nombre} | " + " | ".join(celdas) + " |")
        # cobertura media, longitud
        if conjunto == "ctx":
            cobs = [r["detalle"]["cobertura"] for r in filas if "cobertura" in r["detalle"]]
            info["cobertura_media"] = (sum(cobs) / len(cobs)) if cobs else None
            md.append(f"\nCobertura media (pares con datos, n={len(cobs)} respuestas): {100 * info['cobertura_media']:.1f} %" if cobs else "")
        else:
            rl = [r["detalle"]["rouge_l"] for r in filas]
            info["rouge_l_medio"] = sum(rl) / len(rl)
            info["rouge_l_medio_por_corrida"] = {s: sum(r['detalle']['rouge_l'] for r in filas if r['corrida'] == s) / sum(1 for r in filas if r['corrida'] == s) for s in SEMILLAS}
            md.append(f"\nROUGE-L (F1) medio contra la referencia: {info['rouge_l_medio']:.4f} (promedio de las 5 corridas; por corrida: "
                      + ", ".join(f"s{s}={v:.4f}" for s, v in info['rouge_l_medio_por_corrida'].items()) + ")")
        pal = [r["detalle"]["palabras"] for r in filas]
        info["palabras"] = {"mediana": statistics.median(pal), "p95": percentil(pal, 0.95), "max": max(pal)}
        info["tope_400"] = sum(1 for r in filas if r["llego_al_tope"])
        md.append(f"\nLongitud (palabras): mediana {info['palabras']['mediana']}, p95 {info['palabras']['p95']:.0f}, máx. {info['palabras']['max']}. Respuestas que llegaron al tope de 400 tokens sin `<|eot_id|>`: {info['tope_400']}.")
        # consistencia
        cons = consistencia(filas)
        info["consistencia"] = cons
        un = cons["unanimidad"]
        md.append(f"\nConsistencia entre las 5 corridas: {cons['identicas_5']}/{cons['pares']} pares con las 5 respuestas idénticas; mediana de respuestas distintas por par {cons['mediana_distintas']}; "
                  f"similitud léxica media entre corridas (Jaccard de palabras) {cons['jaccard_medio']:.3f}; "
                  f"pares donde las 5 corridas coinciden en «falla alguna métrica»: {un['__alguna_falla__'][0]}/{un['__alguna_falla__'][1]}.")
        resumen["grupos"][f"{brazo}/{conjunto}"] = info
    # comparaciones A vs C en el previo (regresiones) y A vs B en el contextual
    md.append("\n### Comparación por par (sin dictamen)\n")
    for (b1, b2, conj) in (("A", "C", "previo"), ("A", "B", "ctx")):
        f1, f2 = grupos.get((b1, conj), []), grupos.get((b2, conj), [])
        if not f1 or not f2:
            continue
        md.append(f"\n**{b1} frente a {b2} en holdout {conj}** — pares donde {b2} no falla en ninguna corrida y {b1} falla en las 5 («regresión consistente», definición de T-124), por métrica:\n")
        md.append("| Métrica | Pares |")
        md.append("|---|---|")
        claves = ["f_cifra_validador", "f_cifra_estricta", "f_cobertura", "f_municipio", "f_abstencion", "f_sobreabstencion", "f_geografia"] if conj == "ctx" else ["f_fuera_referencia", "f_eot", "f_repite", "f_idioma"]
        for clave in claves:
            def fallos_par(filas):
                d = defaultdict(list)
                for r in filas:
                    if r["metricas"].get(clave) is not None:
                        d[r["id"]].append(r["metricas"][clave])
                return d
            d1, d2 = fallos_par(f1), fallos_par(f2)
            reg = sorted(pid for pid in d1 if pid in d2 and len(d1[pid]) == 5 and all(d1[pid]) and not any(d2[pid]))
            mej = sorted(pid for pid in d1 if pid in d2 and len(d2[pid]) == 5 and all(d2[pid]) and not any(d1[pid]))
            if d1:
                md.append(f"| {clave} | {b1} falla 5/5 y {b2} 0/5: {', '.join(reg) or 'ninguno'}; {b2} falla 5/5 y {b1} 0/5: {', '.join(mej) or 'ninguno'} |")
        resumen.setdefault("comparaciones", {})[f"{b1}_vs_{b2}_{conj}"] = "ver tablas.md"
    (DIR_SALIDA / "tablas.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    (DIR_SALIDA / "resumen.json").write_text(json.dumps(resumen, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
    # por_par.csv
    por_par = defaultdict(list)
    for r in todo:
        por_par[(r["brazo"], r["conjunto"], r["id"])].append(r)
    with open(DIR_SALIDA / "por_par.csv", "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(["brazo", "conjunto", "id", "subfamilia", "corridas"] + [c + "_fallos" for c in FALLOS_F] + ["cobertura_media", "rouge_l_medio", "respuestas_distintas", "palabras_mediana"])
        for (b, c, pid), rs in sorted(por_par.items()):
            fila = [b, c, pid, rs[0]["subfamilia"], len(rs)]
            for clave in FALLOS_F:
                v = [r["metricas"][clave] for r in rs if r["metricas"][clave] is not None]
                fila.append(sum(v) if v else "")
            cobs = [r["detalle"]["cobertura"] for r in rs if "cobertura" in r["detalle"]]
            rls = [r["detalle"]["rouge_l"] for r in rs if "rouge_l" in r["detalle"]]
            fila += [f"{sum(cobs) / len(cobs):.3f}" if cobs else "", f"{sum(rls) / len(rls):.4f}" if rls else "",
                     len({re.sub(r'\s+', ' ', fold(r['respuesta'])).strip() for r in rs}), statistics.median([r["detalle"]["palabras"] for r in rs])]
            w.writerow(fila)
    # fallos.csv: TODOS los pares/corridas que fallan alguna metrica
    with open(DIR_SALIDA / "fallos.csv", "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(["brazo", "conjunto", "id", "subfamilia", "corrida", "metricas_falladas", "detalle", "pregunta_o_instruccion", "respuesta", "referencia"])
        n = 0
        for r in todo:
            falladas = [k for k, v in r["metricas"].items() if v]
            if not falladas:
                continue
            par = por_id[r["conjunto"]][r["id"]]
            det = {k: v for k, v in r["detalle"].items() if v not in (None, [], False) and k not in ("palabras",)}
            w.writerow([r["brazo"], r["conjunto"], r["id"], r["subfamilia"], r["corrida"], ";".join(falladas), json.dumps(det, ensure_ascii=False), par["instruction"], r["respuesta"], par["response"]])
            n += 1
        print(f"fallos.csv: {n} filas (respuesta·corrida) con alguna metrica fallada")
    # sha256
    sumas = {}
    for nombre in ["crudo_A.jsonl", "crudo_B.jsonl", "crudo_C.jsonl", "generaciones_A.jsonl", "generaciones_B.jsonl", "generaciones_C.jsonl", "fallos.csv", "por_par.csv", "resumen.json", "tablas.md", "control_determinismo.json"]:
        p = DIR_SALIDA / nombre
        if p.exists():
            sumas[nombre] = sha256_archivo(p)
    (DIR_SALIDA / "SHA256.txt").write_text("".join(f"{h}  {n}\n" for n, h in sumas.items()), encoding="utf-8")
    print("sha256:", json.dumps(sumas, indent=1))


def main() -> int:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    g = sub.add_parser("generar")
    g.add_argument("--brazo", choices=list(BRAZOS), required=True)
    g.add_argument("--limite", type=int, default=0)
    sub.add_parser("control")
    sub.add_parser("medir")
    args = ap.parse_args()
    return {"generar": cmd_generar, "control": cmd_control, "medir": cmd_medir}[args.cmd](args)


if __name__ == "__main__":
    sys.exit(main())
