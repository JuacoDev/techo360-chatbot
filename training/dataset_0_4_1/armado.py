"""Piezas comunes de armado de pares de 0.4.1: lectura del contexto REAL, notas de proyeccion, huecos de plantilla y eleccion.

Las cifras salen siempre de los `items` que entrega el pipeline (los mismos del contexto que vera el modelo); el generador solo
las formatea con `formato_valor` del backend, la misma funcion que escribe las lineas.
"""
import re
from dataclasses import dataclass, field

from . import entorno

entorno.preparar_rutas()

from scripts.dataset_0_4 import lengua as lg  # noqa: E402
from scripts.dataset_0_4.resp_comun import Eleccion  # noqa: E402
from services.orquestador import alias as al  # noqa: E402
from services.orquestador import contexto as cx  # noqa: E402
from services.orquestador.grafica_intencion import PREFIJO_OPCIONES  # noqa: E402

from . import preguntas as pq  # noqa: E402
from . import respuestas as rp  # noqa: E402
from .controles import huecos  # noqa: E402

__all__ = ["Eleccion", "lg", "al", "cx"]

_DOC = re.compile(r"^\[d\d+\] ")
_DATO = re.compile(r"^\[(c\d+)\] ")
_SIN_DATO = re.compile(r"^Sin dato para (?P<var>.+?), (?P<mun>.+) \((?P<dep>[^()]+)\), (?P<anio>\d{4}|sin año con dato real): (?P<motivo>.+)\.$")
_UBICACION = re.compile(r"^Ubicación: (?P<mun>.+) pertenece al departamento de (?P<dep>.+)\.$")
_OMISION = re.compile(r"^Se omitieron (?P<n>\d+) datos por el límite de contexto\.$")
_VAR_POR_NOMBRE = {v: k for k, v in al.NOMBRE_VARIABLE.items()}


@dataclass
class Item:
    id: str
    variable: str
    divipola: str
    municipio: str
    departamento: str
    anio: int
    valor: float
    texto: str  # «94,2 %»
    real: bool
    fiabilidad: int | None
    fuente: str
    implicito: bool

    @property
    def md(self) -> str:
        return f"{self.municipio} ({self.departamento})"


@dataclass
class Ctx:
    items: list[Item] = field(default_factory=list)
    sin_datos: list[dict] = field(default_factory=list)
    ubicaciones: list[dict] = field(default_factory=list)
    docs: list[str] = field(default_factory=list)
    opciones: str | None = None
    omitidos: int = 0
    lineas: list[str] = field(default_factory=list)  # todas las lineas del bloque CONTEXTO (sin el vacio)


def leer_ctx(peticion: dict, catalogo) -> Ctx:
    """Lee el ultimo mensaje de usuario de una peticion del pipeline."""
    user = peticion["mensajes"][-1]["contenido"]
    bloque = user.split("\n\nPREGUNTA DEL USUARIO\n")[0]
    ctx = Ctx(lineas=[l for l in bloque.split("\n")[1:] if l and l != cx.LINEA_SIN_CONTEXTO])
    por_id = {i["id"]: i for i in peticion["contexto"]}
    for linea in ctx.lineas:
        m = _DATO.match(linea)
        if m:
            it = por_id[m.group(1)]
            mun = catalogo.por_codigo[it["codigodivipola"]]
            nombre_dep = catalogo.nombre_departamento[mun.cod_departamento]
            texto = cx.formato_valor(it["variable"], it["valor"])
            assert f"{mun.nombre} ({nombre_dep})" in linea and f": {texto}. " in linea, linea
            ctx.items.append(Item(
                it["id"], it["variable"], mun.divipola, mun.nombre, nombre_dep, int(it["anio"]), float(it["valor"]), texto,
                bool(it["es_real"]), it.get("fiabilidad"), it["fuente"], "(último año con dato real)" in linea or "(año de referencia)" in linea))
        elif _DOC.match(linea):
            ctx.docs.append(linea)
        elif linea.startswith(PREFIJO_OPCIONES):
            ctx.opciones = linea
        elif _SIN_DATO.match(linea):
            m = _SIN_DATO.match(linea)
            ctx.sin_datos.append({"variable": _VAR_POR_NOMBRE[m.group("var")], "municipio": m.group("mun"), "departamento": m.group("dep"),
                                  "anio": m.group("anio"), "motivo": m.group("motivo")})
        elif _UBICACION.match(linea):
            m = _UBICACION.match(linea)
            ctx.ubicaciones.append({"municipio": m.group("mun"), "departamento": m.group("dep")})
        elif _OMISION.match(linea):
            ctx.omitidos = int(_OMISION.match(linea).group("n"))
        else:
            raise ValueError(f"Linea de contexto no reconocida: {linea[:80]!r}")
    return ctx


# ---------------------------------------------------------------------------- texto
def unir(partes: list[str]) -> str:
    return lg.unir(partes)


def fiab_de(items: list[Item]) -> str:
    """«de 30 %» o «entre 30 % y 60 %» con valores que aparecen en las lineas (nunca un promedio)."""
    f = sorted({i.fiabilidad for i in items if not i.real and i.fiabilidad is not None})
    if not f:
        raise ValueError("estimacion sin fiabilidad")
    return f"de {f[0]} %" if len(f) == 1 else f"entre {f[0]} % y {f[-1]} %"


def fiab_numero(items: list[Item]) -> str:
    """«30 %» (un solo valor) para {Fn}."""
    f = sorted({i.fiabilidad for i in items if not i.real and i.fiabilidad is not None})
    return f"{f[0]} %"


def valor_frase(i: Item) -> str:
    return i.texto


def mayuscula(t: str) -> str:
    return t[0].upper() + t[1:] if t else t


def nombre_var_cap(variable: str) -> str:
    """«Cobertura de acueducto» (nombre del contexto, sin articulo)."""
    return al.NOMBRE_VARIABLE[variable]


def var_con_articulo(variable: str) -> str:
    return lg.FRASE_VARIABLE[variable][0]


def var_sin_articulo(variable: str) -> str:
    return lg.nombre_variable(variable)


def var_de(variable: str) -> str:
    return lg.FRASE_VARIABLE[variable][1]


class Notas:
    """Notas de proyeccion (hueco {nota}) con reparto equilibrado de plantillas."""

    def __init__(self, el: Eleccion):
        self.el = el

    def serie(self, items: list[Item], clave: str) -> tuple[str, str]:
        proy = [i for i in items if not i.real]
        if not proy:
            return "", ""
        i, t = self.el.de("nota_serie:" + clave, rp.NOTAS_SERIE)
        return t.format(Yp=min(p.anio for p in proy), F=fiab_de(proy)), f"ns{i:02d}"

    def puntual(self, items: list[Item], clave: str) -> tuple[str, str]:
        proy = [i for i in items if not i.real]
        if not proy:
            return "", ""
        if len(items) > 1:  # varios elementos, todos estimaciones: plural
            i, t = self.el.de("nota_varios:" + clave, rp.NOTAS_VARIOS)
            return t.format(F=fiab_de(proy)), f"nv{i:02d}"
        i, t = self.el.de("nota_puntual:" + clave, rp.NOTAS_PUNTUAL)
        return t.format(F=fiab_de(proy)), f"np{i:02d}"

    def mixta(self, items: list[Item], clave: str, nombre) -> tuple[str, str]:
        """Algunos elementos son estimaciones: se nombran (por `nombre(item)`) y se da su fiabilidad."""
        proy = [i for i in items if not i.real]
        if not proy:
            return "", ""
        if len(proy) == len(items):
            return self.puntual(items, clave)
        i, t = self.el.de("nota_mixta:" + clave, rp.NOTAS_MIXTA)
        nombres = []
        for p in proy:
            n = nombre(p)
            if n not in nombres:
                nombres.append(n)
        return t.format(E=unir(nombres), F=fiab_de(proy)), f"nm{i:02d}"


def slots_validos(plantilla: str, disponibles: dict) -> bool:
    return huecos(plantilla) <= set(disponibles)


def elegir(el: Eleccion, clave: str, plantillas: list[str], disponibles: dict, excluir=()) -> tuple[int, str] | None:
    """Plantilla (indice, texto) cuyos huecos estan todos disponibles; reparto equilibrado entre las compatibles."""
    ok = [(i, t) for i, t in enumerate(plantillas) if slots_validos(t, disponibles) and i not in excluir]
    if not ok:
        return None
    j, (i, t) = el.de(clave + f":{len(ok)}:{ok[0][0]}", ok)
    return i, t


def cerrar(texto: str) -> str:
    return lg.cerrar(texto)


def formulaciones(banco: list[str], disponibles: set[str], obligatorias: set[str] | None = None) -> list[str]:
    """Formulaciones del banco cuyos huecos estan todos disponibles (y que usan los obligatorios)."""
    return [f for f in banco if huecos(f) <= disponibles and (not obligatorias or obligatorias <= huecos(f))]
