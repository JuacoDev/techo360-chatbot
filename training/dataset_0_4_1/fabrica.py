"""Base de los generadores de la Fase B: muestreo de entidades, redaccion de preguntas, pipeline real y armado de `Par`.

Reutiliza `scripts.dataset_0_4.familias.Generador` (5.2) para elegir municipios (por departamento, sin los reservados en train),
mencionarlos (alias, homonimos con su departamento) y nombrar variables con las frases que el resolutor reconoce.
"""
import random
import re
from collections import Counter

from . import entorno

entorno.preparar_rutas()

from scripts.dataset_0_4.familias import ANIO_MIN_VAR, FRONTERA_REAL, VARS_6, Generador  # noqa: E402
from services.orquestador import alias as al  # noqa: E402

from . import armado as ar  # noqa: E402
from .controles import huecos  # noqa: E402
from .motor import Entorno, Par  # noqa: E402

PASADO = re.compile(r"\b(fue|registró|marcó|tuvo|estaba|era|presentó|pasó)\b")  # tiempos pasados en las plantillas
VARS_PORCENTAJE = [al.V_ACUEDUCTO, al.V_ALCANTARILLADO, al.V_DEFICIT_CUANTITATIVO, al.V_DEFICIT_CUALITATIVO]
VARS_SIN_DENSIDAD = [v for v in VARS_6 if v != al.V_DENSIDAD]
MOTIVOS_FORZADOS = {  # variable -> clave de motivo que el nucleo de proyeccion puede devolver para un hueco en el rango
    al.V_ACUEDUCTO: ["sin_historia", "valor_sospechoso"], al.V_ALCANTARILLADO: ["sin_historia", "valor_sospechoso"],
    al.V_DENSIDAD: ["sin_historia", "valor_sospechoso"],
    al.V_DEFICIT_CUANTITATIVO: ["sin_extremo", "valor_sospechoso"], al.V_DEFICIT_CUALITATIVO: ["sin_extremo", "valor_sospechoso"],
}


class Fabrica:
    def __init__(self, E: Entorno, semilla: int, reservados: set[str], modo: str = "train", prefijo_id: str = ""):
        self.E, self.semilla, self.modo = E, semilla, modo
        self.g = Generador(E.d, semilla, reservados, modo)
        self.notas = ar.Notas(self.g.el("notas"))  # eleccion equilibrada por clave: self.g.el(clave)
        self.descartes: Counter = Counter()
        self.contador: Counter = Counter()
        self.prefijo = prefijo_id

    # ------------------------------------------------------------------ utilidades
    def descarta(self, sub: str, motivo: str) -> None:
        self.descartes[(sub, motivo)] += 1

    def rng(self, clave: str) -> random.Random:
        return self.g.rng(clave)

    def nuevo_id(self, sub: str) -> str:
        self.contador[sub] += 1
        return f"{self.prefijo}{sub}-{self.contador[sub]:04d}"

    def anio_azar(self, rng: random.Random, variables: list[str], proyeccion: float = 0.25, desde: int = 2000) -> int:
        """Un año plausible para TODAS las variables: dentro del rango de la que empiece mas tarde (y >= `desde`)."""
        minimo = max(max(ANIO_MIN_VAR[v] for v in variables), desde)
        if rng.random() < proyeccion:
            return rng.randint(2025, 2030)
        return rng.randint(max(minimo, 2018), 2024) if rng.random() < 0.7 else rng.randint(minimo, 2024)

    def rango_anios(self, rng: random.Random, variable: str, ancho=(3, 8), desde: int = 2010) -> tuple[int, int]:
        minimo = max(ANIO_MIN_VAR[variable], desde)
        a = min(rng.randint(*ancho), 2024 - minimo)
        y1 = rng.randint(minimo, 2024 - a) if rng.random() < 0.8 else rng.randint(2019, 2030 - a)
        return y1, y1 + a - 1

    def frases(self, sub: str, variables: list[str]) -> tuple[str, str]:
        con, sin = self.g.frase_var(variables[0], sub)
        return con, sin

    # ------------------------------------------------------------------ pregunta
    RESERVA_HOLDOUT = 5  # las ultimas formulaciones de cada banco son SOLO del holdout (nunca entran al train)

    def _banco(self, banco: list[str]) -> list[str]:
        n = self.RESERVA_HOLDOUT
        return banco[-n:] if self.modo == "holdout" else banco[:-n]

    def pregunta(self, sub: str, banco: list[str], slots: dict, obligatorias: set[str] | None = None, envolver: bool = True,
                 informal_ok: bool = True) -> tuple[str, str] | None:
        frames = ar.formulaciones(self._banco(banco), set(slots), obligatorias)
        if not frames:
            self.descarta(sub, "sin_formulacion")
            return None
        texto, pid = self.g.preguntar(sub, frames, informal_ok=informal_ok, envolver=envolver, **slots)
        # «de el» / «a el» (un hueco con articulo tras la preposicion): el usuario escribiria «del» / «al»
        texto = re.sub(r"\b([Dd])e el\b", r"\1el", texto)
        texto = re.sub(r"\b([Aa]) el\b", r"\1l", texto)
        return texto, pid

    def pregunta_cruda(self, sub: str, banco: list[str], slots: dict) -> tuple[str, str] | None:
        """Formulacion con los huecos puestos, SIN mayuscula inicial, envoltura ni informalizacion (F+ con lineas `[cN]` falsas)."""
        frames = ar.formulaciones(self._banco(banco), set(slots))
        if not frames:
            self.descarta(sub, "sin_formulacion")
            return None
        i, frame = self.g.el(sub).de("qc:" + frames[0] + str(len(frames)), frames)
        return frame.format(**slots), f"{sub}.q{i:02d}"

    # ------------------------------------------------------------------ pipeline
    def preparar(self, sub: str, texto: str, **kw):
        """-> (resultado de preparar_consulta, Ctx) o None (descartado y contado)."""
        try:
            r = self.E.preparar(texto, **kw)
        except Exception as e:  # noqa: BLE001
            self.descarta(sub, f"pipeline_{type(e).__name__}")
            return None
        if r["accion"] != "consultar":
            self.descarta(sub, f"pipeline_{r['accion']}_{r.get('tipo', '')}")
            return None
        try:
            ctx = ar.leer_ctx(r["peticion"], self.E.catalogo)
        except (ValueError, AssertionError) as e:
            self.descarta(sub, "contexto_ilegible")
            return None
        return r, ctx

    @staticmethod
    def resolucion_ok(r: dict, munis: list[str], variables: list[str], anios: list[int] | None = None, implicito: bool | None = None) -> str | None:
        """La resolucion real llego a lo previsto; None si coincide, motivo si no."""
        res = r["resolucion"]
        if [m["divipola"] for m in res["municipios"]] != list(munis):
            return "resolucion_municipios"
        if list(res["variables"]) != list(variables):
            return "resolucion_variables"
        if anios is not None and list(res["anios"]) != list(anios):
            return "resolucion_anios"
        if implicito is not None and bool(res["anio_implicito"]) != bool(implicito):
            return "resolucion_implicito"
        return None

    # ------------------------------------------------------------------ par
    def par(self, familia: str, sub: str, texto: str, r: dict, respuesta: str, plantilla_p: str, plantilla_r: str, *,
            huecos_: list[dict] | None = None, historial: list[dict] | None = None, previas: list[str] | None = None,
            meta: dict | None = None, identificador: str | None = None, rag_forzado: bool = False) -> Par:
        res = r["resolucion"]
        entrada = {
            "pregunta": texto,
            "municipios": [m["divipola"] for m in res["municipios"]], "variables": list(res["variables"]),
            "anios": list(res["anios"]), "anio_implicito": bool(res["anio_implicito"]),
        }
        if huecos_:
            entrada["huecos"] = huecos_
        if historial:
            entrada["historial"] = historial
            entrada["previas"] = previas or [h["pregunta"] for h in historial]
        if r.get("rag_resultados"):
            entrada["rag_resultados"] = r["rag_resultados"]
        if rag_forzado:
            entrada["rag_forzado"] = True
        meta = dict(meta or {})
        if historial:
            meta["heredado"] = r["notas"].get("heredado", [])
        return Par(identificador or self.nuevo_id(sub), familia, sub, r["peticion"]["mensajes"], respuesta, entrada,
                   plantilla_p, plantilla_r, meta)

    def dato_puntual(self, clave: str, it) -> tuple[str, str] | None:
        """Oracion(es) de un dato puntual (plantillas G2_PUNTUAL + nota de proyeccion), con el tiempo verbal segun el año."""
        from . import respuestas as _rp
        nota, nid = self.notas.puntual([it], "dato" + clave)
        slots = {"MD": it.md, "V": ar.var_con_articulo(it.variable), "Vc": ar.mayuscula(ar.var_con_articulo(it.variable)),
                 "v": ar.var_sin_articulo(it.variable), "Y": it.anio, "val": it.texto, "nota": nota}
        out = self.render("dato_" + clave, _rp.G2_PUNTUAL, slots, anio=it.anio)
        return None if out is None else (out[0], out[1] + nid)

    # ------------------------------------------------------------------ plantillas
    def plantilla(self, sub: str, plantillas: list[str], slots: dict, excluir=()) -> tuple[int, str] | None:
        return ar.elegir(self.g.el("r:" + sub), "r:" + sub, plantillas, slots, excluir)

    def render(self, sub: str, plantillas: list[str], slots: dict, excluir=(), anio: int | None = None) -> tuple[str, str] | None:
        """`anio`: el del dato citado; desde 2026 se excluyen las plantillas en pasado («fue», «registró»...)."""
        if anio is not None and anio >= 2026:
            excluir = tuple(excluir) + tuple(i for i, t in enumerate(plantillas) if PASADO.search(t))
        e = self.plantilla(sub, plantillas, slots, excluir)
        if e is None:
            self.descarta(sub, "sin_plantilla_compatible")
            return None
        i, t = e
        return ar.cerrar(t.format(**slots)), f"{sub}.r{i:02d}"
