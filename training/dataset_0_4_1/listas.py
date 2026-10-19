"""Regeneracion con listas de A3, A4 y A5 (adenda 7.1b seccion 2) y validador de formato.

Reglas: lista con guiones SOLO con 3 o mas elementos; con menos se queda la prosa de 5.2 (control negativo, lo genera la
Fase B con las plantillas A existentes). Cada elemento copia su cifra del contexto: «- 2019: 90,1 % (dato real)».
Sin encabezados, tablas, negritas ni emojis. Una introduccion en prosa termina en «:» y la lista va una linea por elemento.
Huecos: como `respuestas.py`; {Fn} = fiabilidad sin «de» («30 %»); {Vn} = nombre de variable con mayuscula y sin articulo.
"""
import re

MIN_ELEMENTOS = 3

INTROS_SERIE = [
    "Esta es la serie de {v} en {MD}, año por año:",
    "{Vc} en {MD} registró estos valores entre {Y1} y {Y2}:",
    "Aquí tienes {v} de {MD} de {Y1} a {Y2}:",
    "Estos son los datos de {v} en {MD}:",
    "Año por año, esto es lo que registra {V} en {MD}:",
    "Entre {Y1} y {Y2}, {V} en {MD} tuvo estos valores:",
    "Te muestro la evolución de {v} en {MD}:",
    "Los valores de {v} para {MD} entre {Y1} y {Y2} son:",
    "Con los datos de la plataforma, {V} en {MD} fue así:",
    "Claro. Esta es la serie de {v} de {MD}:",
    "Desde {Y1} hasta {Y2}, {V} en {MD} marcó lo siguiente:",
    "Revisé {v} en {MD} y esto es lo que hay:",
    "Así se comportó {V} en {MD} entre {Y1} y {Y2}:",
    "{Vc} en {MD}, año por año:",
]
INTROS_MUNICIPIOS = [
    "Estos son los valores de {v} en {Y}, municipio por municipio:",
    "{Vc} en {Y} para los municipios consultados:",
    "Aquí tienes la comparación de {v} en {Y}:",
    "Para {Y}, {V} es así en cada municipio:",
    "Esto es lo que registra la plataforma de {v} en {Y}:",
    "Los datos de {v} de {Y} por municipio son:",
    "Te muestro {V} de cada municipio en {Y}:",
    "Claro. Estos son los valores de {Y}:",
    "Comparando los municipios, {V} en {Y} queda así:",
    "En {Y}, {V} se ubica de esta manera:",
    "Con los datos de {Y}, {v} resulta así:",
    "Revisé {v} para {Y} y esto es lo que hay:",
    "Municipio por municipio, {V} en {Y} es:",
    "{Vc} para los municipios que preguntas, en {Y}:",
]
INTROS_PERFIL = [
    "Este es el perfil de {MD} en {Y}:",
    "Esto es lo que registra la plataforma de {MD}:",
    "Aquí tienes los datos de {MD}:",
    "Para {MD}, estas son las variables disponibles:",
    "Te muestro el perfil de {MD}:",
    "Estos son los valores de {MD} en {Y}:",
    "Claro. Así está {MD}:",
    "Los datos de {MD} para {Y} son:",
    "Revisé {MD} y esto es lo que hay:",
    "Con la información de la plataforma, {MD} presenta lo siguiente:",
    "El perfil de {MD} queda así:",
    "En {Y}, {MD} registra lo siguiente:",
    "Resumen de {MD}, variable por variable:",
    "{MD}, con los datos disponibles:",
]
ITEM_SERIE = {"real": "- {Y}: {val} (dato real)", "estimado": "- {Y}: {val} (estimación con fiabilidad de {Fn})"}
ITEM_MUNICIPIO = {"real": "- {MD}: {val} (dato real)", "estimado": "- {MD}: {val} (estimación con fiabilidad de {Fn})"}
ITEM_PERFIL = {"real": "- {Vn}: {val} (dato real)", "estimado": "- {Vn}: {val} (estimación con fiabilidad de {Fn})"}
# Variantes con el año en el elemento, cuando los elementos no comparten año (año implícito: último año con dato real de cada uno)
ITEM_MUNICIPIO_ANIO = {"real": "- {MD} ({Y}): {val} (dato real)", "estimado": "- {MD} ({Y}): {val} (estimación con fiabilidad de {Fn})"}
ITEM_PERFIL_ANIO = {"real": "- {Vn} ({Y}): {val} (dato real)", "estimado": "- {Vn} ({Y}): {val} (estimación con fiabilidad de {Fn})"}
# Cierre opcional (solo si la lista mezcla estimaciones); no lleva cifras.
CIERRES_ESTIMACION = [
    "Los elementos marcados como estimación son proyecciones, no datos observados.",
    "Lo que aparece como estimación no es un dato real.",
    "Las estimaciones se muestran con su fiabilidad y no deben leerse como datos observados.",
    "Ten presente que las estimaciones son proyecciones.",
    "Las líneas con fiabilidad corresponden a proyecciones y no a mediciones.",
    "Recuerda que lo marcado como estimación es una proyección.",
]

TIPOS = {
    "lst_serie": (INTROS_SERIE, ITEM_SERIE, {"MD", "V", "Vc", "v", "Y1", "Y2"}),
    "lst_municipios": (INTROS_MUNICIPIOS, ITEM_MUNICIPIO, {"V", "Vc", "v", "Y"}),
    "lst_perfil": (INTROS_PERFIL, ITEM_PERFIL, {"MD", "Y"}),
}
HUECOS_ITEM = {"lst_serie": {"Y", "val", "Fn"}, "lst_municipios": {"MD", "val", "Fn", "Y"}, "lst_perfil": {"Vn", "val", "Fn", "Y"}}


def armar_lista(intro: str, items: list[str], cierre: str | None = None) -> str:
    """Intro + un elemento por linea (+ linea en blanco y cierre). Con menos de 3 elementos NO se arma: la prosa la hace 5.2."""
    if len(items) < MIN_ELEMENTOS:
        raise ValueError("una lista exige al menos 3 elementos; con menos se usa prosa")
    if not intro.rstrip().endswith(":"):
        raise ValueError("la introduccion de una lista termina en ':'")
    texto = intro + "\n" + "\n".join(items)
    return texto + ("\n\n" + cierre if cierre else "")


_ITEM = re.compile(r"^- \S.*\S$")
_NO_GUION = re.compile(r"^\s*(?:\*|•|\d+[.)]|[a-z][.)])\s")
_EMOJI = re.compile(r"[\U0001F300-\U0001FAFF☀-➿]")


def validar_formato(respuesta: str) -> list[str]:
    """Formato de 0.4.1: prosa breve; lista con guiones solo con >= 3 elementos; sin encabezados, tablas, negritas ni emojis.
    Devuelve los problemas (vacio = correcto). No revisa las cifras (eso es el validador 4.5)."""
    problemas = []
    lineas = respuesta.split("\n")
    if any(re.match(r"^\s*#{1,6}\s", l) for l in lineas):
        problemas.append("encabezado")
    if any("|" in l for l in lineas):
        problemas.append("tabla")
    if "**" in respuesta or "__" in respuesta:
        problemas.append("negrita")
    if _EMOJI.search(respuesta):
        problemas.append("emoji")
    if "```" in respuesta:
        problemas.append("bloque de codigo")
    if any(_NO_GUION.match(l) for l in lineas):
        problemas.append("lista con marcador distinto del guion")
    elementos = [l for l in lineas if l.startswith("- ")]
    if elementos:
        if len(elementos) < MIN_ELEMENTOS:
            problemas.append("lista con menos de 3 elementos")
        if not all(_ITEM.match(l) for l in elementos):
            problemas.append("elemento de lista mal formado")
        idx = [i for i, l in enumerate(lineas) if l.startswith("- ")]
        if idx != list(range(idx[0], idx[0] + len(idx))):
            problemas.append("la lista no es un bloque contiguo")
        if idx[0] == 0 or not lineas[idx[0] - 1].rstrip().endswith(":"):
            problemas.append("la lista debe ir precedida de una introduccion que termine en ':'")
    return problemas
