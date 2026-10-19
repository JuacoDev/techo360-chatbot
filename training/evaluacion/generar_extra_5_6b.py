"""Conjunto extra de 5.6b (30 pares F de inyeccion + 20 pares C3), semilla 9001, SIN base de datos.

    python training/evaluacion/generar_extra_5_6b.py

El prompt de 5.6b no autoriza la base de datos y el generador oficial (techo360-backend/scripts/dataset_0_4)
la abre al construir `Datos`. Por eso aqui se reutilizan SUS plantillas (preguntas.INYECCION*, resp_c.C3_TEMAS,
`Generador.C3`, ENVOLTURAS) con un `Datos` de mentira: catalogo vacio y bloque CONTEXTO vacio, que es todo lo que
C3 y F «pura» necesitan. Los F con contexto toman el bloque CONTEXTO REAL de pares de un solo dato del holdout
contextual (municipios reservados), copiado tal cual; la pregunta legitima es la del propio par.
Misma semilla => mismo archivo byte a byte.
"""
import hashlib
import json
import os
import random
import sys
from pathlib import Path

RAIZ_CHATBOT = Path(__file__).resolve().parents[2]
RAIZ_MONO = RAIZ_CHATBOT.parent
sys.path.insert(0, str(RAIZ_MONO / "techo360-backend"))
# core.config exige estas dos variables al importar; se ponen marcadores para no leer el .env del backend (no se usan).
os.environ.setdefault("BREVO_API_KEY", "x")
os.environ.setdefault("JWT_SECRET_KEY", "x")

from scripts.dataset_0_4 import lengua as lg  # noqa: E402
from scripts.dataset_0_4 import preguntas as pq  # noqa: E402
from scripts.dataset_0_4 import resp_def  # noqa: E402
from scripts.dataset_0_4.familias import Generador  # noqa: E402
from services.orquestador import alias as al  # noqa: E402
from services.orquestador import contexto as cx  # noqa: E402
from services.orquestador import ensamblador as ens  # noqa: E402
from services.orquestador.resolutor import Catalogo  # noqa: E402

SEMILLA = 9001
DIR_R2 = RAIZ_MONO / "trabajo-dataset-0.4.0-r2"
SALIDA = DIR_R2 / "evaluacion" / "extra_5_6b.jsonl"
EXCLUIR = ["train_nuevos.jsonl", "train_c0.jsonl", "holdout_ctx_v0_4.jsonl"]
N_PURA, N_CTX, N_C3 = 10, 20, 20


class DatosSinBD:
    """Solo lo que usan C3 y F «pura»: resolutor con catalogo vacio y render del bloque vacio."""
    catalogo = Catalogo([])
    universo: set = set()

    def renderizar(self, entrada: dict) -> dict:
        import asyncio
        from services.orquestador.resolutor import Resolucion
        res = Resolucion(municipios=[], variables=list(entrada["variables"]), anios=list(entrada["anios"]), rango=None,
                         anio_implicito=bool(entrada["anio_implicito"]))
        contexto = asyncio.run(cx.construir_contexto(res, None, hoy_anio=2026))
        paquete = ens.ensamblar(entrada["pregunta"], contexto, {"usuario_id": 0, "consentimiento_entrenamiento": False})
        user = paquete["peticion"]["mensajes"][1]["contenido"]
        lineas = user.split("\n\nPREGUNTA DEL USUARIO\n")[0].split("\n")[1:]
        return {"user": user, "items": paquete["peticion"]["contexto"], "lineas": lineas, "omitidos": paquete["notas"]["omitidos"]}


def jsonl(ruta: Path) -> list[dict]:
    return [json.loads(x) for x in ruta.read_text(encoding="utf-8").splitlines() if x.strip()]


def generador() -> Generador:
    g = object.__new__(Generador)
    from collections import Counter
    g.d, g.semilla, g.modo, g.reservados = DatosSinBD(), SEMILLA, "extra_5_6b", set()
    g._rng, g._el = {}, {}
    g.descartes, g.ternas, g.cuenta_var, g.generados = Counter(), Counter(), Counter(), Counter()
    return g


def main() -> int:
    prohibidas = {}
    for n in EXCLUIR:
        for r in jsonl(DIR_R2 / n):
            prohibidas[r["instruction"]] = n
    rng = random.Random(f"{SEMILLA}:extra")
    g = generador()
    filas, vistas = [], set()

    def aceptar(instr: str) -> bool:
        if instr in prohibidas or instr in vistas:
            return False
        vistas.add(instr)
        return True

    # ---- F «pura»: bloque vacio. Las 10 plantillas existen tal cual en train, asi que se envuelven como `preguntar` (saludo/cierre).
    intentos = 0
    while sum(1 for f in filas if f["subfamilia"] == "F_pura") < N_PURA and intentos < 400:
        intentos += 1
        i = rng.randrange(len(pq.INYECCION_PURA))
        base = pq.INYECCION_PURA[i]
        pre, suf = rng.choice(pq.ENVOLTURAS_INICIO), rng.choice(pq.ENVOLTURAS_FIN)
        if not pre and not suf:
            continue
        texto = pre + (base[0].lower() + base[1:] if pre else base) + suf
        texto = lg.cap1(texto)
        user = g.d.renderizar({"pregunta": texto, "variables": [], "anios": [], "anio_implicito": True})["user"]
        if aceptar(user):
            filas.append({"subfamilia": "F_pura", "tipo": pq.INYECCION_PURA_TIPO[i], "plantilla": f"F.pura{i:02d}", "instruction": user})

    # ---- F con contexto REAL del holdout (un dato): inyeccion delante de la pregunta legitima del par
    hold = [r for r in jsonl(DIR_R2 / "holdout_ctx_v0_4.jsonl")
            if len(r["entrada"]["municipios"]) == 1 and len(r["entrada"]["variables"]) == 1 and len(r["entrada"]["anios"]) == 1
            and "Sin dato" not in r["instruction"] and "\n[c1] " in r["instruction"]]
    import re
    n_ctx = intentos = 0
    while n_ctx < N_CTX and intentos < 2000:
        intentos += 1
        par = rng.choice(hold)
        bloque, _, pregunta = par["instruction"].partition("\n\nPREGUNTA DEL USUARIO\n")
        linea = bloque.split("\n")[1]
        m = re.match(r"^\[c1\] (?P<var>[^,]+), (?P<muni>.+?) \((?P<dep>[^()]+)\), (?P<anio>\d{4})", linea)
        if not m:
            continue
        if rng.random() < 0.25:
            il = rng.randrange(len(pq.INYECCION_LINEA_FALSA))
            texto = pq.INYECCION_LINEA_FALSA[il].format(Vn=m["var"], Mn=m["muni"], Dn=m["dep"], Yn=m["anio"], P=pregunta)
            plantilla, tipo = f"F.linea{il}", "linea"
        else:
            ii = rng.randrange(len(pq.INYECCION))
            V = lg.var_frase(par["entrada"]["variables"][0])
            texto = pq.INYECCION[ii].format(V=V, M=m["muni"], P=pregunta)
            plantilla, tipo = f"F.inj{ii:02d}", pq.INYECCION_TIPO[ii]
        user = bloque + "\n\nPREGUNTA DEL USUARIO\n" + texto
        if aceptar(user):
            n_ctx += 1
            filas.append({"subfamilia": "F_ctx", "tipo": tipo, "plantilla": plantilla, "instruction": user, "origen_contexto": par["id"],
                          "valor_contexto": linea})

    # ---- C3 con el metodo real de Generador (plantillas de pregunta y respuesta de referencia)
    n3 = intentos = 0
    while n3 < N_C3 and intentos < 2000:
        intentos += 1
        c = g.C3()
        if c is None or not aceptar(c.user):
            continue
        n3 += 1
        filas.append({"subfamilia": "C3", "tipo": c.meta["tema"], "plantilla": c.plantilla_p, "instruction": c.user, "response": c.respuesta})

    # ---- salida
    out = []
    for i, f in enumerate(filas, start=1):
        fam = "F" if f["subfamilia"].startswith("F") else "C"
        out.append({"id": f"x56b-{f['subfamilia']}-{i:03d}", "familia": fam, **f, "semilla": SEMILLA})
    SALIDA.parent.mkdir(parents=True, exist_ok=True)
    with SALIDA.open("w", encoding="utf-8", newline="\n") as fh:
        for r in out:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")
    # solapes (comprobacion independiente de `aceptar`)
    solapes = {n: sum(1 for r in jsonl(DIR_R2 / n) if r["instruction"] in {o["instruction"] for o in out}) for n in EXCLUIR}
    cuentas = {k: sum(1 for o in out if o["subfamilia"] == k) for k in ("F_pura", "F_ctx", "C3")}
    print(json.dumps({"n": len(out), "cuentas": cuentas, "solapes": solapes, "sha256": hashlib.sha256(SALIDA.read_bytes()).hexdigest()}, ensure_ascii=False))
    return 0 if sum(solapes.values()) == 0 and len(out) == N_PURA + N_CTX + N_C3 else 1


if __name__ == "__main__":
    sys.exit(main())
