"""Generador de HS1-HS6 (multi-turno, adenda 7.1b seccion 4).

Cada par se arma con `preparar_consulta(..., historial=[...], previa=resolver_cadena([...]))` del backend: la herencia de entidades,
el saneado del historial y el recorte a 400 tokens son los de produccion (docs/fase7-1b-historial-formato.md). El historial son
turnos de chat normales (sin CONTEXTO), y solo el ultimo `user` lleva el CONTEXTO fresco del turno actual.
"""
import re

from . import armado as ar
from . import preguntas as pq
from . import preguntas_hs as pqh
from . import respuestas as rp
from .fabrica import ANIO_MIN_VAR, VARS_6, Fabrica
from .gen_f import FALSOS_D  # noqa: F401  (reservado: HS6 puede citar los mismos textos de inyeccion)
from .motor import Par

HERENCIA = {
    "hs1_anio": ["municipios", "variables"], "hs2_municipio": ["variables", "anios"], "hs3_variable": ["municipios", "anios"],
    "hs4": ["municipios", "variables", "anios"], "hs5_cambio_tema": [], "hs6_inyeccion_previa": ["municipios", "variables"],
}


class GenHS(Fabrica):
    # ------------------------------------------------------------------ turno previo (autocontenido)
    def _intercambio(self, sub: str, rng, cod: str | None = None, v: str | None = None, anio: int | None = None,
                     real: bool | None = None, inyeccion: bool = False):
        """Un intercambio previo con dato: -> dict(pregunta, respuesta, cod, v, anio, item, previas) o None.
        `real`: True exige un año con dato real, False uno proyectado. Con `inyeccion`, la pregunta lleva una orden de cambiar las
        reglas y la respuesta previa la rechaza (F+ con dato)."""
        cod = cod or self.g.muni(sub + ":prev")
        v = v or self.g.var_equilibrada(rng, VARS_6, "HSp" + sub)
        if anio is None:
            anio = self.anio_para(rng, v, real)
        con, sin = self.g.frase_var(v, sub + ":prev")
        slots = {"M": self.g.mencion(cod, sub + ":prev")[0], "V": con, "v": sin, "Y": anio}
        q = self.pregunta(sub + ":prev", pq.G2_PUNTUAL, slots, {"Y"}, envolver=False, informal_ok=False)
        if q is None:
            return None
        texto = q[0]
        got = self.preparar(sub + ":prev", texto)
        if got is None:
            return None
        r, ctx = got
        if self.resolucion_ok(r, [cod], [v]) or len(ctx.items) != 1 or ctx.sin_datos or r["notas"]["intencion_grafica"]:
            self.descarta(sub, "turno_previo_no_apto")
            return None
        it = ctx.items[0]
        if real is not None and it.real != real:
            self.descarta(sub, "turno_previo_real_proyeccion")
            return None
        d = self.dato_puntual("prev" + sub, it)
        if d is None:
            return None
        respuesta = d[0]
        if inyeccion:
            _, orden = self.g.el(sub + ":inj").de("i", pq.TURNO_PREVIO_INYECCION)
            texto = f"{texto} {orden}"
            _, rech = self.g.el(sub + ":rech").de("r", [t for t in rp.FP_IGNORAR if "{dato}" in t])
            respuesta = ar.cerrar(rech.format(dato=respuesta))
        return {"pregunta": texto, "respuesta": respuesta, "cod": cod, "v": v, "anio": it.anio, "item": it}

    def anio_para(self, rng, v: str, real: bool | None) -> int:
        """Año con dato para `v`: real (<= frontera real) o proyectado (2025+; para deficit tambien 2019-2023)."""
        if real is True:
            return rng.choice({ar.al.V_DEFICIT_CUANTITATIVO: [2018], ar.al.V_DEFICIT_CUALITATIVO: [2018], ar.al.V_SCORE: [2018],
                               ar.al.V_DENSIDAD: list(range(2014, 2024))}.get(v, list(range(2012, 2025))))
        if real is False:
            return rng.randint(2025, 2032)
        return self.anio_azar(rng, [v], 0.3, desde=2012)

    @staticmethod
    def _historial(intercambios: list[dict]) -> list[dict]:
        return [{"pregunta": i["pregunta"], "respuesta": i["respuesta"]} for i in intercambios]

    # ------------------------------------------------------------------ respuesta con la plantilla HS
    def _responder(self, sub: str, it: ar.Item, clave: str = ""):  # `it`: item citado
        nota, nid = self.notas.puntual([it], "hs" + sub)
        slots = {"MD": it.md, "V": ar.var_con_articulo(it.variable), "Vc": ar.mayuscula(ar.var_con_articulo(it.variable)),
                 "v": ar.var_sin_articulo(it.variable), "Y": it.anio, "val": it.texto, "nota": nota}
        out = self.render(sub, rp.PLANTILLAS[sub], slots, anio=it.anio)
        if out is None:
            return None
        resp, pr = out
        return resp, pr + nid

    def _turno(self, sub: str, texto: str, previos: list[dict], cod: str, v: str, anio: int | None, heredado: list[str],
               rag: bool = False):
        got = self.preparar(sub, texto, historial=self._historial(previos), previas=[i["pregunta"] for i in previos], usar_rag=rag)
        if got is None:
            return None
        r, ctx = got
        if sorted(r["notas"].get("heredado", [])) != sorted(heredado):
            self.descarta(sub, "heredado:" + ",".join(r["notas"].get("heredado", [])))
            return None
        err = self.resolucion_ok(r, [cod], [v], [anio] if anio else None)
        if err or len(ctx.items) != 1 or ctx.sin_datos or r["notas"]["historial_intercambios"] != len(previos):
            self.descarta(sub, err or "contexto_o_historial")
            return None
        return r, ctx

    # ------------------------------------------------------------------ HS1 / HS2 / HS3
    def _previos(self, sub: str, rng, **kw):
        """Uno o dos intercambios previos (70 % uno). En el segundo caso el primero fija la entidad y el segundo es un seguimiento de año."""
        ex0 = self._intercambio(sub, rng, **kw)
        if ex0 is None:
            return None
        if rng.random() < 0.7:
            return [ex0]
        # segundo intercambio: seguimiento de año (HS1) sobre la misma entidad, respondido con la plantilla HS1
        y1 = rng.choice([a for a in range(max(ANIO_MIN_VAR[ex0["v"]], 2012), 2025) if a != ex0["anio"]])
        con_y = ar.formulaciones(pqh.HS1_ANIO, {"Y"})
        _, fr = self.g.el(sub + ":s2").de("f", con_y)
        texto = fr.format(Y=y1)
        got = self._turno(sub + ":prev2", texto, [ex0], ex0["cod"], ex0["v"], y1, HERENCIA["hs1_anio"])
        if got is None:
            return [ex0]
        r, ctx = got
        out = self._responder("hs1_anio", ctx.items[0])
        if out is None:
            return [ex0]
        return [ex0, {"pregunta": texto, "respuesta": out[0], "cod": ex0["cod"], "v": ex0["v"], "anio": y1, "item": ctx.items[0]}]

    def hs1_anio(self) -> Par | None:
        sub = "hs1_anio"
        rng = self.rng(sub)
        previos = self._previos(sub, rng)
        if previos is None:
            return None
        ult = previos[-1]
        anios_previos = {i["anio"] for i in previos}
        y = rng.choice([a for a in range(max(ANIO_MIN_VAR[ult["v"]], 2012), 2031) if a not in anios_previos])
        q = self.pregunta(sub, pqh.HS1_ANIO, {"Y": y}, {"Y"}, envolver=False)
        if q is None:
            return None
        texto, pid = q
        got = self._turno(sub, texto, previos, ult["cod"], ult["v"], y, HERENCIA[sub])
        if got is None:
            return None
        r, ctx = got
        out = self._responder(sub, ctx.items[0])
        if out is None:
            return None
        resp, pr = out
        return self.par("HS", sub, texto, r, resp, pid, pr, historial=self._historial(previos))

    def hs2_municipio(self) -> Par | None:
        sub = "hs2_municipio"
        rng = self.rng(sub)
        previos = self._previos(sub, rng)
        if previos is None:
            return None
        ult = previos[-1]
        cod = self.g.muni(sub, excluir=[i["cod"] for i in previos])
        q = self.pregunta(sub, pqh.HS2_MUNICIPIO, {"M": self.g.mencion(cod, sub)[0]}, {"M"}, envolver=False)
        if q is None:
            return None
        texto, pid = q
        got = self._turno(sub, texto, previos, cod, ult["v"], ult["anio"], HERENCIA[sub])
        if got is None:
            return None
        r, ctx = got
        out = self._responder(sub, ctx.items[0])
        if out is None:
            return None
        resp, pr = out
        return self.par("HS", sub, texto, r, resp, pid, pr, historial=self._historial(previos))

    def hs3_variable(self) -> Par | None:
        sub = "hs3_variable"
        rng = self.rng(sub)
        previos = self._previos(sub, rng)
        if previos is None:
            return None
        ult = previos[-1]
        v2 = self.g.var_equilibrada(rng, [x for x in VARS_6 if x != ult["v"]], "HS3")
        con, sin = self.g.frase_var(v2, sub)
        q = self.pregunta(sub, pqh.HS3_VARIABLE, {"V": con, "v": sin}, {"V"} if rng.random() < 0.5 else None, envolver=False)
        if q is None:
            return None
        texto, pid = q
        got = self._turno(sub, texto, previos, ult["cod"], v2, ult["anio"], HERENCIA[sub])
        if got is None:
            return None
        r, ctx = got
        out = self._responder(sub, ctx.items[0])
        if out is None:
            return None
        resp, pr = out
        return self.par("HS", sub, texto, r, resp, pid, pr, historial=self._historial(previos))

    # ------------------------------------------------------------------ HS4 (real / estimado)
    def _hs4(self, sub: str, real: bool) -> Par | None:
        rng = self.rng(sub)
        ex = self._intercambio(sub, rng, real=real)
        if ex is None:
            return None
        q = self.pregunta(sub, pqh.HS4_REFERENCIA, {}, None, envolver=False)
        if q is None:
            return None
        texto, pid = q
        got = self._turno(sub, texto, [ex], ex["cod"], ex["v"], ex["anio"], HERENCIA["hs4"])
        if got is None:
            return None
        r, ctx = got
        it = ctx.items[0]
        if it.real != real:
            self.descarta(sub, "real_proyeccion")
            return None
        slots = {"MD": it.md, "v": ar.var_sin_articulo(it.variable), "Y": it.anio, "val": it.texto, "fuente": it.fuente}
        if not real:
            slots["F"] = ar.fiab_de([it])
        # la respuesta debe contestar lo que se pregunta: por la fuente -> plantillas con {fuente}; por la fiabilidad -> con {F}
        n = ar.lg.sin_tildes(texto.lower())
        exige = []
        if any(p in n for p in ("fuente", "de donde", "quien", "publica", "genera", "calculo", "base")):
            exige.append("{fuente}")
        if not real and any(p in n for p in ("fiabilidad", "confiable", "seguro")):
            exige.append("{F}")
        excluir = tuple(i for i, t in enumerate(rp.PLANTILLAS[sub]) if any(x not in t for x in exige))
        out = self.render(sub, rp.PLANTILLAS[sub], slots, excluir)
        if out is None:
            return None
        resp, pr = out
        return self.par("HS", sub, texto, r, resp, pid, pr, historial=self._historial([ex]))

    def hs4_real(self) -> Par | None:
        return self._hs4("hs4_real", True)

    def hs4_estimado(self) -> Par | None:
        return self._hs4("hs4_estimado", False)

    # ------------------------------------------------------------------ HS5 (cambio de tema)
    def hs5_cambio_tema(self) -> Par | None:
        sub = "hs5_cambio_tema"
        rng = self.rng(sub)
        previos = self._previos(sub, rng)
        if previos is None:
            return None
        ult = previos[-1]
        cod = self.g.muni(sub, excluir=[ult["cod"]]) if rng.random() < 0.8 else ult["cod"]
        v = self.g.var_equilibrada(rng, [x for x in VARS_6 if x != ult["v"]] if cod == ult["cod"] else VARS_6, "HS5")
        y = self.anio_azar(rng, [v], 0.25, desde=2012)
        con, sin = self.g.frase_var(v, sub)
        q = self.pregunta(sub, pqh.HS5_CAMBIO_TEMA, {"M": self.g.mencion(cod, sub)[0], "V": con, "v": sin, "Y": y}, {"Y"}, envolver=False)
        if q is None:
            return None
        texto, pid = q
        got = self._turno(sub, texto, previos, cod, v, None, HERENCIA[sub])
        if got is None:
            return None
        r, ctx = got
        it = ctx.items[0]
        d = self.dato_puntual("hs5", it)
        if d is None:
            return None
        dato = d[0]
        out = self.render(sub, rp.PLANTILLAS[sub], {"dato": dato})
        if out is None:
            return None
        resp, pr = out
        if self.modo == "train" and len(re.findall(r"\b(?:Claro|Con gusto|Listo|Entendido)\b", resp)) >= 2:
            resp = resp.replace(dato, re.sub(r"^(?:Claro|Con gusto|Listo|Entendido)[.,] ", "", dato), 1)  # marcador repetido: se quita el del dato
        return self.par("HS", sub, texto, r, resp, pid, pr + d[1], historial=self._historial(previos))

    # ------------------------------------------------------------------ HS6 (inyeccion en un turno previo)
    def hs6_inyeccion_previa(self) -> Par | None:
        sub = "hs6_inyeccion_previa"
        rng = self.rng(sub)
        ex = self._intercambio(sub, rng, inyeccion=True)
        if ex is None:
            return None
        y = rng.choice([a for a in range(max(ANIO_MIN_VAR[ex["v"]], 2012), 2031) if a != ex["anio"]])
        q = self.pregunta(sub, pqh.HS6_SEGUIMIENTO, {"Y": y}, {"Y"}, envolver=False)
        if q is None:
            return None
        texto, pid = q
        got = self._turno(sub, texto, [ex], ex["cod"], ex["v"], y, HERENCIA[sub])
        if got is None:
            return None
        r, ctx = got
        it = ctx.items[0]
        d = self.dato_puntual("hs6", it)
        if d is None:
            return None
        out = self.render(sub, rp.PLANTILLAS[sub], {"dato": d[0]})
        if out is None:
            return None
        resp, pr = out
        return self.par("HS", sub, texto, r, resp, pid, pr + d[1], historial=self._historial([ex]))

    def generar(self, sub: str) -> Par | None:
        return getattr(self, sub)()
