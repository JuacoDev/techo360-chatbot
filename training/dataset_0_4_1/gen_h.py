"""Generador de H1-H6 (RAG): contexto con `[dN]` del recuperador REAL sobre el corpus final; respuesta por extraccion + plantilla.

  H1  todas las lineas [dN] del contexto son relevantes (contienen las piezas que la respuesta cita)
  H2  hay una relevante y al menos una marginal: la respuesta usa solo la relevante
  H3  ninguna linea responde: abstencion (con o sin fragmentos irrelevantes en el contexto)
  H4  dato del contexto + definicion del documento (ver `h4`: el enrutador actual no consulta el RAG con municipio resuelto)
  H5  premisa contraria al fragmento: la respuesta sigue el fragmento
  H6  concepto general de politica publica, sin documentos: explicacion breve sin cifras ni afirmaciones de la plataforma

Cada pieza citada se comprueba contra la LINEA [dN] que realmente entro al contexto (puede venir cortada por presupuesto).
"""
import re

from . import armado as ar
from . import h_datos as hd
from . import listas as ls
from . import preguntas as pq
from . import respuestas as rp
from .fabrica import Fabrica
from .motor import Par

H4_TEMAS = {
    "score-formula": ["¿cómo se calcula el Score de privación?", "¿cómo se obtiene ese score?", "¿cuál es la fórmula del score de privación?"],
    "densidad-formula": ["¿cómo se calcula la densidad poblacional?", "¿de dónde sale la densidad de población?"],
    "deficit-anio": ["¿de qué año es el dato de déficit habitacional?", "¿a qué año corresponde ese déficit?"],
    "fuente-deficit": ["¿de dónde sale ese dato de déficit?", "¿quién publica el déficit habitacional municipal?"],
    "proyeccion-deficit": ["¿por qué el déficit de 2024 es una estimación?", "¿cómo se estima el déficit habitacional proyectado?"],
    "proyeccion-coberturas": ["¿cómo se proyectan las coberturas?", "¿cómo se estima la cobertura de años futuros?"],
    "proyeccion-densidad": ["¿cómo se proyecta la densidad poblacional?", "¿qué método usa la densidad proyectada?"],
    "fiabilidad": ["¿qué significa la fiabilidad de ese dato?", "¿qué quiere decir ese porcentaje de fiabilidad?"],
    "dato-real-vs-proyeccion": ["¿cómo sé si ese dato es real o una proyección?", "¿ese dato es real o estimado?"],
}
H4_FRAMES = [
    "Dime {V} de {M} en {Y} y, además, {tema}",
    "¿Cuál es {V} en {M} en {Y}? También, {tema}",
    "Quiero saber {V} de {M} para {Y}, y {tema}",
    "Consulta {V} en {M} en {Y}; ahora, {tema}",
    "{v} en {M}, {Y}. Y por favor, {tema}",
]
H4_PUENTES = [
    "Sobre tu otra duda, los documentos dicen lo siguiente. {e}",
    "En cuanto a tu segunda pregunta, esto explican los documentos. {e}",
    "Respecto a lo que preguntas además, los documentos señalan esto. {e}",
    "Y sobre la explicación que pides, esto es lo que dicen los documentos. {e}",
    "Para lo otro que consultas, los documentos indican lo siguiente. {e}",
    "{e} Eso es lo que dicen los documentos sobre tu segunda duda.",
    "Además, esto es lo que explican los documentos. {e}",
    "Lo demás que preguntas, según los documentos, es esto. {e}",
]
# (variable, tipo de año, intenciones posibles)
H4_COMBOS = [
    (ar.al.V_SCORE, None, ["score-formula", "fiabilidad", "dato-real-vs-proyeccion"]),
    (ar.al.V_DENSIDAD, "real", ["densidad-formula", "dato-real-vs-proyeccion"]),
    (ar.al.V_DENSIDAD, "proy", ["proyeccion-densidad", "fiabilidad"]),
    (ar.al.V_DEFICIT_CUANTITATIVO, "real", ["deficit-anio", "fuente-deficit", "dato-real-vs-proyeccion"]),
    (ar.al.V_DEFICIT_CUALITATIVO, "real", ["deficit-anio", "fuente-deficit"]),
    (ar.al.V_DEFICIT_CUANTITATIVO, "proy", ["proyeccion-deficit", "fiabilidad"]),
    (ar.al.V_DEFICIT_CUALITATIVO, "proy", ["proyeccion-deficit", "fiabilidad"]),
    (ar.al.V_ACUEDUCTO, "proy", ["proyeccion-coberturas", "fiabilidad"]),
    (ar.al.V_ALCANTARILLADO, "proy", ["proyeccion-coberturas", "fiabilidad"]),
    (ar.al.V_ACUEDUCTO, "real", ["dato-real-vs-proyeccion"]),
    (ar.al.V_ALCANTARILLADO, "real", ["dato-real-vs-proyeccion"]),
]
INTENCION = {i["id"]: i for i in hd.INTENCIONES}


def limpiar(t: str) -> str:
    """Limpieza COSMETICA de un trozo del corpus: sin negritas ni acentos graves, « -- » como coma, «_» como espacio, espacios colapsados."""
    t = t.replace("**", "").replace("`", "").replace(" -- ", ", ").replace("_", " ")
    return re.sub(r"\s+", " ", t).strip()


def cap1(t: str) -> str:
    return t[:1].upper() + t[1:] if t else t


class GenH(Fabrica):
    def __init__(self, *a, **k):
        super().__init__(*a, **k)
        self.cursor: dict[str, int] = {}

    # ------------------------------------------------------------------ extractos
    def _pieza_en(self, pieza: str, lineas_doc: list[str]) -> bool:
        p = limpiar(pieza).lower()
        return any(p in limpiar(l).lower() for l in lineas_doc)

    def _sustituir(self, plantilla: str, piezas: list[str]) -> str:
        """{pN} -> pieza limpia; con mayuscula inicial si abre oracion (inicio de la plantilla o tras «. »)."""
        salida, ultimo = [], 0
        for m in re.finditer(r"\{p(\d+)\}", plantilla):
            t = limpiar(piezas[int(m.group(1)) - 1])
            if m.start() == 0 or plantilla[:m.start()].endswith(". "):
                t = cap1(t)
            salida += [plantilla[ultimo:m.start()], t]
            ultimo = m.end()
        salida.append(plantilla[ultimo:])
        return "".join(salida)

    def texto_intencion(self, intent: dict) -> tuple[str, list[str], bool]:
        """-> (extracto ya armado, piezas usadas, es_lista)."""
        piezas = intent["piezas"]
        forma = intent["forma"]
        if forma[0] == "texto":
            usadas = sorted({int(n) for n in re.findall(r"\{p(\d+)\}", forma[1])})
            return self._sustituir(forma[1], piezas), [piezas[n - 1] for n in usadas], False
        intro = self._sustituir(forma[1], piezas)
        items = [f"- {limpiar(piezas[n - 1])}" for n in forma[2]]
        cierre = self._sustituir(forma[3], piezas) if len(forma) > 3 else None
        usadas = [piezas[n - 1] for n in forma[2]] + ([piezas[int(n) - 1] for n in re.findall(r"\{p(\d+)\}", forma[3])] if len(forma) > 3 else [])
        intro_piezas = [piezas[int(n) - 1] for n in re.findall(r"\{p(\d+)\}", forma[1])]
        return ls.armar_lista(intro, items, cierre), usadas + intro_piezas, True

    def _respuesta(self, sub: str, e: str, es_lista: bool, aperturas: list[str], aperturas_lista: list[str] | None = None) -> tuple[str, str] | None:
        if es_lista:
            i, ap = self.g.el(sub + ":apl").de("a", aperturas_lista or hd.H_APERTURAS_LISTA)
            return f"{ap} {e}", f"{sub}.l{i:02d}"
        i, ap = self.g.el(sub + ":ap").de("a", aperturas)
        return ar.cerrar(ap.format(e=e)), f"{sub}.a{i:02d}"

    # ------------------------------------------------------------------ pregunta de un banco fijo
    def _siguiente(self, clave: str, lista: list) -> object:
        i = self.cursor.get(clave, 0)
        self.cursor[clave] = i + 1
        return lista[i % len(lista)] if i < len(lista) else None

    def _preguntar_fija(self, sub: str, texto: str) -> tuple[str, str]:
        """Envoltura/informalizacion del 5.2 sobre una formulacion fija."""
        t, pid = self.g.preguntar(sub, [texto], informal_ok=True, envolver=True)
        return t, pid

    # ------------------------------------------------------------------ H1 / H2 / H5
    def _con_docs(self, sub: str, texto: str, intent: dict, aperturas: list[str], tipo_sub: str | None = None) -> Par | None:
        got = self.preparar(sub, texto)
        if got is None:
            return None
        r, ctx = got
        if ctx.items or ctx.sin_datos or r["resolucion"]["municipios"] or not ctx.docs:
            self.descarta(sub, "sin_docs_o_con_datos")
            return None
        e, usadas, es_lista = self.texto_intencion(intent)
        relevantes = [d for d in ctx.docs if any(limpiar(p).lower() in limpiar(d).lower() for p in usadas)]
        if not all(self._pieza_en(p, ctx.docs) for p in usadas):
            # el recuperador real no trajo (o corto) lo que responde: con ESE contexto la respuesta correcta es abstenerse (H3)
            i, resp = self.g.el("h3_sin_cobertura:r").de("r", hd.H3_RESPUESTAS)
            j, sug = self.g.el("h3_sin_cobertura:s").de("s", hd.H3_SUGERENCIAS)
            return self.par("H", "h3_sin_cobertura", texto, r, resp + sug, "", f"h3_sin_cobertura.r{i:02d}s{j}",
                            meta={"docs_en_contexto": len(ctx.docs), "cobertura_en_corpus": True, "intencion": intent["id"]})
        marginales = [d for d in ctx.docs if d not in relevantes]
        if tipo_sub is None:
            sub_real = "h2_marginal" if marginales else "h1_un_fragmento"
        else:
            sub_real = tipo_sub
        out = self._respuesta(sub_real, e, es_lista, aperturas)
        if out is None:
            return None
        resp, pr = out
        return self.par("H", sub_real, texto, r, resp, "", pr, meta={"intencion": intent["id"], "docs_relevantes": len(relevantes), "docs_marginales": len(marginales)})

    def h12(self) -> Par | None:
        """Siguiente pregunta de entrenamiento; la subfamilia (H1 o H2) la decide lo que recupero el retriever real."""
        orden = [(it, it["q"][k]) for k in range(max(len(i["q"]) for i in hd.INTENCIONES)) for it in hd.INTENCIONES if k < len(it["q"])]
        c = self._siguiente("h12", orden)
        if c is None:
            return None
        intent, q = c
        texto, pid = self._preguntar_fija("h1_un_fragmento", q)
        par = self._con_docs("h12", texto, intent, hd.H_APERTURAS)
        if par is not None:
            par.plantilla_p = pid
        return par

    def h5_premisa(self) -> Par | None:
        sub = "h5_premisa"
        orden = [(iid, qs[k], c) for k in range(max(len(p[1]) for p in hd.PREMISAS)) for iid, qs, c in hd.PREMISAS if k < len(qs)]
        c = self._siguiente("h5", orden)
        if c is None:
            return None
        iid, q, _ = c
        texto, pid = self._preguntar_fija(sub, q)
        par = self._con_docs(sub, texto, INTENCION[iid], hd.H5_APERTURAS, tipo_sub="h5_premisa")
        if par is not None:
            par.plantilla_p = pid
        return par

    def par_respondible(self, intent: dict, q: str) -> Par | None:
        """Holdout: una pregunta `qh` sin envoltura; solo si el retriever real trae lo que responde."""
        texto = q
        par = self._con_docs("h_holdout", texto, intent, hd.H_APERTURAS)
        return par if par is not None and par.subfamilia in ("h1_un_fragmento", "h2_marginal") else None

    def par_abstencion(self, q: str) -> Par | None:
        sub = "h3_sin_cobertura"
        got = self.preparar(sub, q)
        if got is None:
            return None
        r, ctx = got
        if ctx.items or ctx.sin_datos or r["resolucion"]["municipios"]:
            return None
        i, resp = self.g.el(sub + ":r").de("r", hd.H3_RESPUESTAS)
        j, sug = self.g.el(sub + ":s").de("s", hd.H3_SUGERENCIAS)
        return self.par("H", sub, q, r, resp + sug, "", f"{sub}.r{i:02d}s{j}", meta={"docs_en_contexto": len(ctx.docs)})

    # ------------------------------------------------------------------ H3 (abstencion)
    def h3_sin_cobertura(self) -> Par | None:
        sub = "h3_sin_cobertura"
        q = self._siguiente("h3", hd.H3_PREGUNTAS)
        if q is None:
            return None
        texto, pid = self._preguntar_fija(sub, q)
        got = self.preparar(sub, texto)
        if got is None:
            return None
        r, ctx = got
        if ctx.items or ctx.sin_datos or r["resolucion"]["municipios"]:
            self.descarta(sub, "resolvio_entidad")
            return None
        i, resp = self.g.el(sub + ":r").de("r", hd.H3_RESPUESTAS)
        j, sug = self.g.el(sub + ":s").de("s", hd.H3_SUGERENCIAS)
        return self.par("H", sub, texto, r, resp + sug, pid, f"{sub}.r{i:02d}s{j}", meta={"docs_en_contexto": len(ctx.docs)})

    # ------------------------------------------------------------------ H6 (concepto general)
    def h6_concepto_general(self) -> Par | None:
        sub = "h6_concepto_general"
        orden = [(c, qs[k]) for k in range(max(len(x[1]) for x in hd.CONCEPTOS)) for c, qs, _ in hd.CONCEPTOS if k < len(qs)]
        c = self._siguiente("h6", orden)
        if c is None:
            return None
        concepto, q = c
        expl = next(x[2] for x in hd.CONCEPTOS if x[0] == concepto)
        texto, pid = self._preguntar_fija(sub, q)
        got = self.preparar(sub, texto)
        if got is None:
            return None
        r, ctx = got
        if ctx.docs or ctx.items or r["resolucion"]["municipios"]:
            self.descarta(sub, "con_docs_o_datos")
            return None
        out = self._respuesta(sub, expl, False, hd.H6_APERTURAS)
        resp, pr = out
        return self.par("H", sub, texto, r, resp, pid, pr, meta={"concepto": concepto})

    # ------------------------------------------------------------------ H4 (dato + documento)
    def h4_datos_y_documento(self) -> Par | None:
        sub = "h4_datos_y_documento"
        rng = self.rng(sub)
        v, tipo, intenciones = self.g.el(sub + ":combo").de("c", H4_COMBOS)[1]
        iid = rng.choice(intenciones)
        cod = self.g.muni(sub)
        if tipo == "proy":
            anio = rng.randint(2025, 2030)
        elif tipo == "real":
            anio = 2018 if v in (ar.al.V_DEFICIT_CUANTITATIVO, ar.al.V_DEFICIT_CUALITATIVO) else rng.randint(2014, 2023) if v == ar.al.V_DENSIDAD else rng.randint(2012, 2024)
        else:
            anio = 2018 if rng.random() < 0.5 else rng.randint(2025, 2030)
        con, sin = self.g.frase_var(v, sub)
        _, tema = self.g.el(sub + ":tema:" + iid).de("t", H4_TEMAS[iid])
        _, marco = self.g.el(sub + ":marco").de("m", H4_FRAMES)
        texto = marco.format(V=con, v=sin, M=self.g.mencion(cod, sub)[0], Y=anio, tema=tema)
        texto = re.sub(r"\b([Dd])e el\b", lambda m: m.group(1) + "el", texto)
        texto = cap1(texto)
        got = self.preparar(sub, texto, forzar_rag=True)
        if got is None:
            return None
        r, ctx = got
        if self.resolucion_ok(r, [cod], [v]) or len(ctx.items) != 1 or ctx.sin_datos or not ctx.docs:
            self.descarta(sub, "resolucion_o_contexto")
            return None
        it = ctx.items[0]
        if tipo == "real" and not it.real or tipo == "proy" and it.real:
            self.descarta(sub, "real_proyeccion")
            return None
        e, usadas, es_lista = self.texto_intencion(INTENCION[iid])
        if es_lista or not all(self._pieza_en(p, ctx.docs) for p in usadas):
            self.descarta(sub, "pieza_ausente_del_contexto")
            return None
        dato = self.dato_puntual(sub, it)
        if dato is None:
            return None
        i, puente = self.g.el(sub + ":puente").de("p", H4_PUENTES)
        resp = ar.cerrar(f"{dato[0]} " + puente.format(e=e))
        return self.par("H", sub, texto, r, resp, "", f"{sub}.p{i:02d}" + dato[1], rag_forzado=True,
                        meta={"intencion": iid, "requiere_cambio_enrutador": True})

    def generar(self, sub: str) -> Par | None:
        return getattr(self, sub)()
