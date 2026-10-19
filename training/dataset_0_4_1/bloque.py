"""Bloque ```grafica: construccion determinista y validacion estructural (fase2-3 seccion 2 y 7.1 seccion 3).

El bloque nunca lleva valores de datos ni `titulo`. Los ids y codigos se COPIAN de la linea de opciones del CONTEXTO.
"""
import json
import re

from . import catalogo as cat

PATRON_BLOQUE = re.compile(r"```grafica\n(.*?)\n```", re.S)
PATRON_OPCIONES = re.compile(r"^Gráfica disponible\. Tipos: (?P<tipos>[^.]*)\. Variables: (?P<vars>[^.]*)\. Zonas: (?P<zonas>.*)$", re.M)
PATRON_ZONA = re.compile(r"(\d{5}) = ")


def armar_bloque(tipo: str, modo: str, variables: list[str], zonas: list[str], anios: list[int]) -> str:
    """Texto del bloque, con las claves en el orden del contrato y sin espacios sobrantes."""
    spec = {"v": 1, "tipo": tipo, "modo": modo, "variables": list(variables), "zonas": list(zonas), "anios": list(anios)}
    error = validar_spec(spec)
    if error:
        raise ValueError(error)
    return "```grafica\n" + json.dumps(spec, ensure_ascii=False, separators=(",", ":")) + "\n```"


def armar_respuesta(texto: str, bloque: str | None) -> str:
    """Texto + linea en blanco + bloque al final (7.1 seccion 3, «Forma de la respuesta»)."""
    return texto if not bloque else f"{texto}\n\n{bloque}"


def validar_spec(spec: dict) -> str | None:
    """Esquema cerrado + combinacion. None si es valido."""
    if tuple(spec) != cat.CLAVES_BLOQUE:
        return f"claves distintas del esquema cerrado: {list(spec)}"
    if spec["v"] != 1:
        return "v distinto de 1"
    zonas, anios = spec["zonas"], spec["anios"]
    if not all(isinstance(z, str) and re.fullmatch(r"\d{5}", z) for z in zonas):
        return "zonas deben ser codigos DIVIPOLA de 5 digitos"
    if len(set(zonas)) != len(zonas) or len(zonas) > 5:
        return "zonas repetidas o mas de 5"
    if not all(isinstance(a, int) and not isinstance(a, bool) and cat.ANIO_MIN <= a <= cat.ANIO_MAX for a in anios):
        return "anios fuera de 2018-2042"
    if anios != sorted(set(anios)):
        return "anios desordenados o repetidos"
    return cat.tipos_validos(spec["tipo"], spec["modo"], spec["variables"], len(zonas), len(anios))


def extraer_bloques(respuesta: str) -> list[str]:
    return PATRON_BLOQUE.findall(respuesta)


def opciones_del_contexto(contexto: str) -> dict | None:
    """Lee la linea «Gráfica disponible…» del CONTEXTO: -> {"tipos", "variables", "zonas": {codigo: texto}} o None."""
    m = PATRON_OPCIONES.search(contexto)
    if not m:
        return None
    zonas = m.group("zonas")
    return {
        "tipos": [t.strip() for t in m.group("tipos").split(",")],
        "variables": [v.strip() for v in m.group("vars").split(",")],
        "zonas": set(PATRON_ZONA.findall(zonas)),
    }


def validar_respuesta_g(respuesta: str, contexto: str, *, debe_tener_bloque: bool) -> list[str]:
    """Controles de 7.3b sobre una respuesta: bloque unico, valido, sin valores, con ids/codigos del contexto, al final.
    Devuelve la lista de problemas (vacia = correcta)."""
    problemas: list[str] = []
    bloques = extraer_bloques(respuesta)
    if not debe_tener_bloque:
        if "```" in respuesta or bloques:
            problemas.append("bloque donde no corresponde")
        return problemas
    if len(bloques) != 1:
        return [f"se esperaba un bloque y hay {len(bloques)}"]
    if not respuesta.rstrip().endswith("```") or respuesta.count("```") != 2:
        problemas.append("el bloque no esta al final o hay marcas extra")
    if "\n\n```grafica" not in respuesta:
        problemas.append("falta la linea en blanco antes del bloque")
    try:
        spec = json.loads(bloques[0])
    except json.JSONDecodeError:
        return problemas + ["JSON invalido"]
    error = validar_spec(spec) if isinstance(spec, dict) else "el bloque no es un objeto"
    if error:
        problemas.append(error)
        return problemas
    op = opciones_del_contexto(contexto)
    if op is None:
        problemas.append("el contexto no trae la linea de opciones")
    else:
        if spec["tipo"] not in op["tipos"]:
            problemas.append("tipo ausente de las opciones")
        if any(v not in op["variables"] for v in spec["variables"]):
            problemas.append("variable ausente de las opciones")
        if any(z not in op["zonas"] for z in spec["zonas"]):
            problemas.append("zona no copiada del contexto")
    texto = respuesta.split("```grafica")[0]
    if "```" in texto:
        problemas.append("marcas de codigo en el texto")
    return problemas
