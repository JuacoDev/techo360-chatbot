"""Generador de G1-G6 (graficas) de 0.4.1. Cada metodo arma UN candidato con el pipeline real o devuelve None (descarte contado).

Contexto: `preparar_consulta` real (con W1: intencion, linea de opciones, serie). Respuesta: plantilla de `respuestas.py` con las
cifras de los items del contexto; en G1 y G6 se agrega el bloque con `bloque.armar_bloque` y se valida con `procesar_grafica` del
backend (esquema cerrado, combinacion, zonas existentes y datos suficientes).
"""
from . import armado as ar
from . import bloque as bl
from . import catalogo as cat
from . import preguntas as pq
from . import respuestas as rp
from .fabrica import VARS_6, VARS_PORCENTAJE, VARS_SIN_DENSIDAD, Fabrica, MOTIVOS_FORZADOS
from .motor import Par

K_MUNIS = [2, 2, 2, 2, 3, 3, 3, 4, 4, 5, 5]  # reparto: 2 (36 %), 3 (27 %), 4 (18 %), 5 (18 %)


class GenG(Fabrica):
    # ------------------------------------------------------------------ utilidades de G
    def _munis(self, sub: str, k: int) -> list[str]:
        return self.g.munis(sub, k, mismo_depto=self.rng(sub + ":mismo").random() < 0.4)

    def _lista_munis(self, sub: str, codigos: list[str]) -> str:
        return ar.unir([self.g.mencion(c, sub)[0] for c in codigos])

    @staticmethod
    def _serie(ctx: ar.Ctx, variable: str, codigo: str) -> list[ar.Item]:
        return sorted((i for i in ctx.items if i.variable == variable and i.divipola == codigo), key=lambda i: i.anio)

    def _md_de_resolucion(self, r: dict) -> list[str]:
        cat_ = self.E.catalogo
        return [f"{cat_.por_codigo[m['divipola']].nombre} ({cat_.nombre_departamento[cat_.por_codigo[m['divipola']].cod_departamento]})"
                for m in r["resolucion"]["municipios"]]

    @staticmethod
    def _md_lista(items: list[ar.Item]) -> list[str]:
        vistos: list[str] = []
        for i in items:
            if i.md not in vistos:
                vistos.append(i.md)
        return vistos

    def _con_bloque(self, sub, texto, r, ctx, resp_texto, plantilla_r, tipo, modo, variables, zonas, anios, *, huecos_=None, meta=None):
        """Agrega el bloque, valida con el backend real y arma el Par."""
        try:
            bloque = bl.armar_bloque(tipo, modo, variables, zonas, anios)
        except ValueError as e:
            self.descarta(sub, "bloque_invalido:" + str(e)[:40])
            return None
        respuesta = bl.armar_respuesta(resp_texto, bloque)
        contexto = r["peticion"]["mensajes"][-1]["contenido"].split("\n\nPREGUNTA DEL USUARIO\n")[0]
        prob = bl.validar_respuesta_g(respuesta, contexto, debe_tener_bloque=True)
        if prob:
            self.descarta(sub, "respuesta_g:" + prob[0][:30])
            return None
        g = self.E.validar_grafica(respuesta, huecos_)
        if not g or not g.get("valida"):
            self.descarta(sub, "backend_grafica_invalida:" + str((g or {}).get("motivo", ""))[:30])
            return None
        return self.par(cat.familia(sub), sub, texto, r, respuesta, "", plantilla_r, huecos_=huecos_, meta=meta)

    # ------------------------------------------------------------------ G1 lineas individual
    def g1_lineas_individual(self) -> Par | None:
        sub = "g1_lineas_individual"
        rng = self.rng(sub)
        cod = self.g.muni(sub)
        v = self.g.var_equilibrada(rng, VARS_6, "G1li")
        con_rango = rng.random() < 0.3
        con, sin = self.g.frase_var(v, sub)
        slots = {"M": self.g.mencion(cod, sub)[0], "V": con, "v": sin}
        if con_rango:
            y1, y2 = self.rango_anios(rng, v, desde=2018)
            slots.update(Y1=y1, Y2=y2)
        q = self.pregunta(sub, pq.G1_LINEAS_INDIVIDUAL, slots, {"Y1", "Y2"} if con_rango else None)
        if q is None:
            return None
        texto, pid = q
        got = self.preparar(sub, texto)
        if got is None:
            return None
        r, ctx = got
        if not r["notas"]["intencion_grafica"]:
            self.descarta(sub, "sin_intencion_grafica")
            return None
        err = self.resolucion_ok(r, [cod], [v], list(range(y1, y2 + 1)) if con_rango else None, implicito=not con_rango)
        if err:
            self.descarta(sub, err)
            return None
        serie = self._serie(ctx, v, cod)
        if ctx.sin_datos or (con_rango and ctx.omitidos) or len(serie) != len(ctx.items):
            self.descarta(sub, "serie_no_apta")
            return None
        return self._g1_lineas(sub, texto, pid, r, ctx, serie, "individual", [cod], v, slots_resp_extra={})

    def _g1_lineas(self, sub, texto, pid, r, ctx, serie_ctx, modo, zonas, v, slots_resp_extra):
        # el esquema del bloque acepta anios 2018-2042: se grafica (y se describe) lo que cae en ese rango
        serie = [i for i in serie_ctx if i.anio >= 2018]
        if len(serie) < 2:
            self.descarta(sub, "menos_de_2_anios_graficables")
            return None
        y1, y2 = serie[0], serie[-1]
        nota, nid = self.notas.serie(serie, sub)
        slots = {
            "MD": serie[0].md, "V": ar.var_con_articulo(v), "Vc": ar.mayuscula(ar.var_con_articulo(v)), "Vde": ar.var_de(v),
            "v": ar.var_sin_articulo(v), "Y1": y1.anio, "Y2": y2.anio, "V1": y1.texto, "V2": y2.texto, "nota": nota,
            "tendencia": "subió" if y2.valor > y1.valor else "bajó", **slots_resp_extra,
        }
        excluir = () if y1.valor != y2.valor else tuple(i for i, t in enumerate(rp.G1_LINEAS_INDIVIDUAL) if "{tendencia}" in t)
        out = self.render(sub, rp.PLANTILLAS[sub], slots, excluir)
        if out is None:
            return None
        resp, pr = out
        return self._con_bloque(sub, texto, r, ctx, resp, pr + nid, "lineas", modo, [v], zonas, [i.anio for i in serie])

    # ------------------------------------------------------------------ G1 lineas comparar
    def g1_lineas_comparar(self) -> Par | None:
        sub = "g1_lineas_comparar"
        rng = self.rng(sub)
        k = rng.choice(K_MUNIS)
        codigos = self._munis(sub, k)
        v = self.g.var_equilibrada(rng, VARS_6, "G1lc")
        con_rango = rng.random() < 0.3
        con, sin = self.g.frase_var(v, sub)
        slots = {"Ms": self._lista_munis(sub, codigos), "V": con, "v": sin}
        if con_rango:
            y1, y2 = self.rango_anios(rng, v, (3, 6), desde=2018)
            slots.update(Y1=y1, Y2=y2)
        q = self.pregunta(sub, pq.G1_LINEAS_COMPARAR, slots, {"Y1", "Y2"} if con_rango else None)
        if q is None:
            return None
        texto, pid = q
        got = self.preparar(sub, texto)
        if got is None:
            return None
        r, ctx = got
        if not r["notas"]["intencion_grafica"]:
            self.descarta(sub, "sin_intencion_grafica")
            return None
        orden = [m["divipola"] for m in r["resolucion"]["municipios"]]
        if sorted(orden) != sorted(codigos) or list(r["resolucion"]["variables"]) != [v]:
            self.descarta(sub, "resolucion")
            return None
        if ctx.sin_datos:
            self.descarta(sub, "contexto_no_apto")
            return None
        series = {c: self._serie(ctx, v, c) for c in orden}
        comunes = sorted(a for a in set.intersection(*(set(i.anio for i in s) for s in series.values())) if a >= 2018)
        if len(comunes) < 2:
            self.descarta(sub, "anios_comunes")
            return None
        if con_rango and comunes != list(range(y1, y2 + 1)):
            self.descarta(sub, "rango_incompleto")
            return None
        ultimos = [next(i for i in series[c] if i.anio == comunes[-1]) for c in orden]
        mostrados = [i for c in orden for i in series[c] if i.anio in comunes]
        nota, nid = self.notas.serie(mostrados, sub)
        lista = ar.unir([f"{i.md} con {i.texto}" for i in ultimos])
        slots_r = {"MDs": ar.unir([i.md for i in ultimos]), "V": ar.var_con_articulo(v), "Vc": ar.mayuscula(ar.var_con_articulo(v)),
                   "v": ar.var_sin_articulo(v), "Y1": comunes[0], "Y2": comunes[-1], "lista": lista, "nota": nota}
        out = self.render(sub, rp.PLANTILLAS[sub], slots_r)
        if out is None:
            return None
        resp, pr = out
        return self._con_bloque(sub, texto, r, ctx, resp, pr + nid, "lineas", "comparar", [v], orden, comunes)

    # ------------------------------------------------------------------ G1 ranking
    def g1_barras_ranking(self) -> Par | None:
        sub = "g1_barras_ranking"
        rng = self.rng(sub)
        k = rng.choice(K_MUNIS)
        codigos = self._munis(sub, k)
        v = self.g.var_equilibrada(rng, VARS_6, "G1br")
        con_anio = rng.random() < 0.65
        con, sin = self.g.frase_var(v, sub)
        slots = {"Ms": self._lista_munis(sub, codigos), "V": con, "v": sin}
        if con_anio:
            slots["Y"] = self.anio_azar(rng, [v], desde=2018)
        q = self.pregunta(sub, pq.G1_BARRAS_RANKING, slots, {"Y"} if con_anio else None)
        if q is None:
            return None
        texto, pid = q
        got = self.preparar(sub, texto)
        if got is None:
            return None
        r, ctx = got
        orden = [m["divipola"] for m in r["resolucion"]["municipios"]]
        if sorted(orden) != sorted(codigos) or list(r["resolucion"]["variables"]) != [v] or not r["notas"]["intencion_grafica"]:
            self.descarta(sub, "resolucion_o_intencion")
            return None
        items = [i for i in ctx.items if i.variable == v]
        if ctx.sin_datos or ctx.omitidos or len(items) != len(orden) or len({i.anio for i in items}) != 1:
            self.descarta(sub, "contexto_no_apto")
            return None
        reales = {i.real for i in items}
        if len(reales) != 1:
            self.descarta(sub, "mixto_real_proyeccion")
            return None
        valores = sorted(items, key=lambda i: i.valor)
        if valores[0].valor == valores[1].valor or valores[-1].valor == valores[-2].valor:
            self.descarta(sub, "empate_extremos")
            return None
        bot, top = valores[0], valores[-1]
        nota, nid = self.notas.puntual(items, sub)
        slots_r = {"MDs": ar.unir([i.md for i in items]), "v": ar.var_sin_articulo(v), "Y": items[0].anio, "top": top.md, "topv": top.texto,
                   "bot": bot.md, "botv": bot.texto, "nota": nota}
        out = self.render(sub, rp.PLANTILLAS[sub], slots_r)
        if out is None:
            return None
        resp, pr = out
        return self._con_bloque(sub, texto, r, ctx, resp, pr + nid, "barras_ranking", "comparar", [v], orden, [items[0].anio])

    # ------------------------------------------------------------------ G1 agrupadas
    def _agrupadas(self, sub: str, banco: list[str], comparar: bool) -> Par | None:
        rng = self.rng(sub)
        k = rng.choice(K_MUNIS) if comparar else 1
        if comparar and k * 2 > 20:
            k = 5
        codigos = self._munis(sub, k) if comparar else [self.g.muni(sub)]
        n_vars = rng.choice([2, 2, 3, 3, 4]) if not comparar else rng.choice([2, 2, 3])
        n_vars = min(n_vars, 20 // max(k, 1))
        variables = sorted(rng.sample(VARS_PORCENTAJE, n_vars), key=VARS_PORCENTAJE.index)
        for v in variables:
            self.cuenta_var_g(v)
        con_anio = rng.random() < 0.7
        slots = {"Vs": self.g.frases_vars(variables, sub)}
        slots["Ms" if comparar else "M"] = self._lista_munis(sub, codigos) if comparar else self.g.mencion(codigos[0], sub)[0]
        if con_anio:
            slots["Y"] = self.anio_azar(rng, variables, desde=2018)
        q = self.pregunta(sub, banco, slots, {"Y"} if con_anio else None)
        if q is None:
            return None
        texto, pid = q
        got = self.preparar(sub, texto)
        if got is None:
            return None
        r, ctx = got
        orden = [m["divipola"] for m in r["resolucion"]["municipios"]]
        if sorted(orden) != sorted(codigos) or sorted(r["resolucion"]["variables"]) != sorted(variables) or not r["notas"]["intencion_grafica"]:
            self.descarta(sub, "resolucion_o_intencion")
            return None
        variables = list(r["resolucion"]["variables"])
        if ctx.sin_datos or ctx.omitidos or len(ctx.items) != len(orden) * len(variables) or len({i.anio for i in ctx.items}) != 1:
            self.descarta(sub, "contexto_no_apto")
            return None
        anio = ctx.items[0].anio
        nombre = lambda i: ar.var_con_articulo(i.variable)  # noqa: E731
        nota, nid = self.notas.mixta(ctx.items, sub, nombre)
        vs_txt = ar.unir([ar.var_con_articulo(v) for v in variables])
        if comparar:
            slots_r = {"MDs": ar.unir([ctx.items[j * len(variables)].md for j in range(len(orden))]), "Vs_txt": vs_txt, "Y": anio, "nota": nota}
        else:
            lista_vars = ar.unir([f"{ar.var_con_articulo(i.variable)} con {i.texto}" for i in ctx.items])
            slots_r = {"MD": ctx.items[0].md, "Vs_txt": vs_txt, "Y": anio, "lista_vars": lista_vars, "nota": nota}
        out = self.render(sub, rp.PLANTILLAS[sub], slots_r)
        if out is None:
            return None
        resp, pr = out
        return self._con_bloque(sub, texto, r, ctx, resp, pr + nid, "barras_agrupadas", "comparar" if comparar else "individual", variables, orden, [anio])

    def cuenta_var_g(self, v: str) -> None:
        self.g.cuenta_var[("G1ag", v)] += 1

    def g1_barras_agrupadas_ind(self) -> Par | None:
        return self._agrupadas("g1_barras_agrupadas_ind", pq.G1_BARRAS_AGRUPADAS_IND, False)

    def g1_barras_agrupadas_cmp(self) -> Par | None:
        return self._agrupadas("g1_barras_agrupadas_cmp", pq.G1_BARRAS_AGRUPADAS_CMP, True)

    # ------------------------------------------------------------------ G1 gauge
    def g1_gauge(self) -> Par | None:
        sub = "g1_gauge"
        rng = self.rng(sub)
        cod = self.g.muni(sub)
        v = self.g.var_equilibrada(rng, VARS_SIN_DENSIDAD, "G1g")
        con_anio = rng.random() < 0.55
        con, sin = self.g.frase_var(v, sub)
        slots = {"M": self.g.mencion(cod, sub)[0], "V": con, "v": sin}
        if con_anio:
            slots["Y"] = self.anio_azar(rng, [v], desde=2018)
        q = self.pregunta(sub, pq.G1_GAUGE, slots, {"Y"} if con_anio else None)
        if q is None:
            return None
        texto, pid = q
        got = self.preparar(sub, texto)
        if got is None:
            return None
        r, ctx = got
        err = self.resolucion_ok(r, [cod], [v])
        if err or not r["notas"]["intencion_grafica"] or ctx.sin_datos or len(ctx.items) != 1:
            self.descarta(sub, err or "contexto_no_apto")
            return None
        it = ctx.items[0]
        nota, nid = self.notas.puntual([it], sub)
        slots_r = {"MD": it.md, "V": ar.var_con_articulo(v), "Vc": ar.mayuscula(ar.var_con_articulo(v)), "v": ar.var_sin_articulo(v),
                   "Y": it.anio, "val": it.texto, "nota": nota}
        out = self.render(sub, rp.PLANTILLAS[sub], slots_r)
        if out is None:
            return None
        resp, pr = out
        return self._con_bloque(sub, texto, r, ctx, resp, pr + nid, "gauge", "individual", [v], [cod], [it.anio])

    # ------------------------------------------------------------------ G2 (sin bloque)
    def g2_serie(self) -> Par | None:
        sub = "g2_serie"
        rng = self.rng(sub)
        cod = self.g.muni(sub)
        v = self.g.var_equilibrada(rng, VARS_6, "G2s")
        y1, y2 = self.rango_anios(rng, v, (3, 7))
        con, sin = self.g.frase_var(v, sub)
        slots = {"M": self.g.mencion(cod, sub)[0], "V": con, "v": sin, "Y1": y1, "Y2": y2}
        q = self.pregunta(sub, pq.G2_SERIE, slots, {"Y1", "Y2"})
        if q is None:
            return None
        texto, pid = q
        got = self.preparar(sub, texto)
        if got is None:
            return None
        r, ctx = got
        err = self.resolucion_ok(r, [cod], [v], list(range(y1, y2 + 1)), implicito=False)
        if err or r["notas"]["intencion_grafica"] or ctx.sin_datos or ctx.omitidos or ctx.opciones or len(ctx.items) != y2 - y1 + 1:
            self.descarta(sub, err or "contexto_no_apto")
            return None
        items = self._serie(ctx, v, cod)
        nota, nid = self.notas.serie(items, sub)
        serie = ar.unir([f"{i.texto} en {i.anio}" for i in items])
        slots_r = {"MD": items[0].md, "V": ar.var_con_articulo(v), "Vc": ar.mayuscula(ar.var_con_articulo(v)), "v": ar.var_sin_articulo(v),
                   "Y1": y1, "Y2": y2, "serie": serie, "nota": nota}
        out = self.render(sub, rp.PLANTILLAS[sub], slots_r)
        if out is None:
            return None
        resp, pr = out
        return self.par("G2", sub, texto, r, resp, pid, pr + nid)

    def g2_comparacion(self) -> Par | None:
        sub = "g2_comparacion"
        rng = self.rng(sub)
        k = rng.choice(K_MUNIS)
        codigos = self._munis(sub, k)
        v = self.g.var_equilibrada(rng, VARS_6, "G2c")
        con, sin = self.g.frase_var(v, sub)
        slots = {"Ms": self._lista_munis(sub, codigos), "V": con, "v": sin, "Y": self.anio_azar(rng, [v], 0.2)}
        q = self.pregunta(sub, pq.G2_COMPARACION, slots, {"Y"})
        if q is None:
            return None
        texto, pid = q
        got = self.preparar(sub, texto)
        if got is None:
            return None
        r, ctx = got
        orden = [m["divipola"] for m in r["resolucion"]["municipios"]]
        if (sorted(orden) != sorted(codigos) or list(r["resolucion"]["variables"]) != [v] or r["notas"]["intencion_grafica"] or ctx.sin_datos
                or ctx.omitidos or len(ctx.items) != len(orden)):
            self.descarta(sub, "contexto_no_apto")
            return None
        if len({i.real for i in ctx.items}) != 1:
            self.descarta(sub, "mixto_real_proyeccion")
            return None
        nota, nid = self.notas.puntual(ctx.items, sub)
        lista = ar.unir([f"{i.md} con {i.texto}" for i in ctx.items])
        slots_r = {"MDs": ar.unir([i.md for i in ctx.items]), "V": ar.var_con_articulo(v), "Vc": ar.mayuscula(ar.var_con_articulo(v)),
                   "v": ar.var_sin_articulo(v), "Y": ctx.items[0].anio, "lista": lista, "nota": nota}
        out = self.render(sub, rp.PLANTILLAS[sub], slots_r)
        if out is None:
            return None
        resp, pr = out
        return self.par("G2", sub, texto, r, resp, pid, pr + nid)

    def g2_puntual(self) -> Par | None:
        sub = "g2_puntual"
        rng = self.rng(sub)
        cod = self.g.muni(sub)
        v = self.g.var_equilibrada(rng, VARS_6, "G2p")
        con, sin = self.g.frase_var(v, sub)
        slots = {"M": self.g.mencion(cod, sub)[0], "V": con, "v": sin, "Y": self.anio_azar(rng, [v], 0.3)}
        q = self.pregunta(sub, pq.G2_PUNTUAL, slots, {"Y"})
        if q is None:
            return None
        texto, pid = q
        got = self.preparar(sub, texto)
        if got is None:
            return None
        r, ctx = got
        err = self.resolucion_ok(r, [cod], [v])
        if err or r["notas"]["intencion_grafica"] or ctx.sin_datos or len(ctx.items) != 1:
            self.descarta(sub, err or "contexto_no_apto")
            return None
        it = ctx.items[0]
        nota, nid = self.notas.puntual([it], sub)
        slots_r = {"MD": it.md, "V": ar.var_con_articulo(v), "Vc": ar.mayuscula(ar.var_con_articulo(v)), "v": ar.var_sin_articulo(v),
                   "Y": it.anio, "val": it.texto, "nota": nota}
        out = self.render(sub, rp.PLANTILLAS[sub], slots_r, anio=it.anio)
        if out is None:
            return None
        resp, pr = out
        return self.par("G2", sub, texto, r, resp, pid, pr + nid)

    # ------------------------------------------------------------------ G3 (sin bloque)
    def g3_un_anio(self) -> Par | None:
        sub = "g3_un_anio"
        rng = self.rng(sub)
        cod = self.g.muni(sub)
        v = self.g.var_equilibrada(rng, VARS_6, "G3u")
        con, sin = self.g.frase_var(v, sub)
        slots = {"M": self.g.mencion(cod, sub)[0], "V": con, "v": sin, "Y": self.anio_azar(rng, [v], 0.2)}
        q = self.pregunta(sub, pq.G3_UN_ANIO, slots, {"Y"})
        if q is None:
            return None
        texto, pid = q
        got = self.preparar(sub, texto)
        if got is None:
            return None
        r, ctx = got
        err = self.resolucion_ok(r, [cod], [v], implicito=False)
        if err or not r["notas"]["intencion_grafica"] or ctx.sin_datos or len(ctx.items) != 1 or not ctx.opciones:
            self.descarta(sub, err or "contexto_no_apto")
            return None
        it = ctx.items[0]
        nota, nid = self.notas.puntual([it], sub)
        slots_r = {"MD": it.md, "V": ar.var_con_articulo(v), "Vc": ar.mayuscula(ar.var_con_articulo(v)), "v": ar.var_sin_articulo(v),
                   "Y": it.anio, "val": it.texto, "nota": nota}
        out = self.render(sub, rp.PLANTILLAS[sub], slots_r, anio=it.anio)
        if out is None:
            return None
        resp, pr = out
        return self.par("G3", sub, texto, r, resp, pid, pr + nid)

    def _hueco_forzado(self, sub: str, rng, cod: str, v: str, anios: list[int]) -> list[dict] | None:
        """Huecos forzados (como 5.2 B1) para una variable de la base; None si la variable es el Score."""
        motivos = MOTIVOS_FORZADOS.get(v)
        if not motivos:
            return None
        motivo = rng.choice(motivos)
        return [{"variable": v, "divipola": cod, "anio": a, "motivo": motivo} for a in anios]

    def g3_sin_dato(self) -> Par | None:
        sub = "g3_sin_dato"
        rng = self.rng(sub)
        cod = self.g.muni(sub)
        v = self.g.var_equilibrada(rng, [x for x in VARS_6 if x in MOTIVOS_FORZADOS], "G3s")
        con, sin = self.g.frase_var(v, sub)
        con_rango = rng.random() < 0.4
        slots = {"M": self.g.mencion(cod, sub)[0], "V": con, "v": sin}
        if con_rango:
            y1, y2 = self.rango_anios(rng, v, (3, 5))
            slots.update(Y1=y1, Y2=y2)
            anios = list(range(y1, y2 + 1))
        else:
            anios = []
        q = self.pregunta(sub, pq.G3_SIN_DATO, slots, {"Y1", "Y2"} if con_rango else None)
        if q is None:
            return None
        texto, pid = q
        if con_rango:
            hu = self._hueco_forzado(sub, rng, cod, v, anios)
        else:
            # sin años: el pipeline usa el ultimo año con dato real; se oculta ese año para forzar «Sin dato»
            serie = self.E.d.serie(cod, v)
            reales = [f["anio"] for f in serie if f["valor"] is not None and not f["origen"].startswith("proyeccion")]
            if not reales:
                hu = None
            else:
                hu = self._hueco_forzado(sub, rng, cod, v, [max(reales)])
        got = self.preparar(sub, texto, huecos=hu)
        if got is None:
            return None
        r, ctx = got
        if not r["notas"]["intencion_grafica"] or not ctx.sin_datos or ctx.items:
            self.descarta(sub, "contexto_no_apto")
            return None
        sd = ctx.sin_datos[0]
        slots_r = {"MD": f"{sd['municipio']} ({sd['departamento']})", "v": ar.var_sin_articulo(v), "motivo": sd["motivo"], "alterno": ""}
        out = self.render(sub, rp.PLANTILLAS[sub], slots_r)
        if out is None:
            return None
        resp, pr = out
        return self.par("G3", sub, texto, r, resp, pid, pr, huecos_=hu)

    # ------------------------------------------------------------------ G4
    def g4_tipo_no_soportado(self) -> Par | None:
        sub = "g4_tipo_no_soportado"
        rng = self.rng(sub)
        _, t = self.g.el(sub + ":t").de("t", list(cat.TIPOS_NO_SOPORTADOS))
        v = self.g.var_equilibrada(rng, VARS_6, "G4")
        multi = rng.random() < 0.3
        codigos = self._munis(sub, rng.choice([2, 3])) if multi else [self.g.muni(sub)]
        con, sin = self.g.frase_var(v, sub)
        slots = {"V": con, "v": sin, "t": t, "T": pq.ARTICULO_TIPO[t]}
        slots["Ms" if multi else "M"] = self._lista_munis(sub, codigos) if multi else self.g.mencion(codigos[0], sub)[0]
        if rng.random() < 0.3:
            slots["Y"] = self.anio_azar(rng, [v], 0.2)
        q = self.pregunta(sub, pq.G4_TIPO_NO_SOPORTADO, slots)
        if q is None:
            return None
        texto, pid = q
        got = self.preparar(sub, texto)
        if got is None:
            return None
        r, ctx = got
        orden = [m["divipola"] for m in r["resolucion"]["municipios"]]
        if sorted(orden) != sorted(codigos) or v not in r["resolucion"]["variables"] or not r["notas"]["intencion_grafica"] or not ctx.opciones:
            self.descarta(sub, "resolucion_o_intencion")
            return None
        mds = ar.unir(self._md_lista(ctx.items)) if ctx.items else ar.unir(self._md_de_resolucion(r))
        out = self.render(sub, rp.PLANTILLAS[sub], {"t": t, "MDs": mds})
        if out is None:
            return None
        resp, pr = out
        return self.par("G4", sub, texto, r, resp, pid, pr, meta={"tipo_no_soportado": t})

    # ------------------------------------------------------------------ G5
    def g5_sin_municipio(self) -> Par | None:
        sub = "g5_sin_municipio"
        rng = self.rng(sub)
        v = self.g.var_equilibrada(rng, VARS_6, "G5m")
        con, sin = self.g.frase_var(v, sub)
        vs = [v] + [x for x in rng.sample(VARS_PORCENTAJE, 2) if x != v]
        slots = {"V": con, "v": sin, "Vs": self.g.frases_vars(vs[:2], sub), "Y": self.anio_azar(rng, [v], 0.2)}
        q = self.pregunta(sub, pq.G5_SIN_MUNICIPIO, slots)
        if q is None:
            return None
        texto, pid = q
        got = self.preparar(sub, texto)
        if got is None:
            return None
        r, ctx = got
        if r["resolucion"]["municipios"] or ctx.items or ctx.opciones or r["notas"]["intencion_grafica"]:
            self.descarta(sub, "resolvio_municipio")
            return None
        out = self.render(sub, rp.PLANTILLAS[sub], {})
        if out is None:
            return None
        resp, pr = out
        return self.par("G5", sub, texto, r, resp, pid, pr)

    def g5_sin_variable(self) -> Par | None:
        sub = "g5_sin_variable"
        rng = self.rng(sub)
        multi = rng.random() < 0.25
        codigos = self._munis(sub, rng.choice([2, 3])) if multi else [self.g.muni(sub)]
        slots = {"Y": self.anio_azar(rng, VARS_6[:1], 0.2)}
        y1 = rng.randint(2012, 2018)
        slots.update(Y1=y1, Y2=y1 + rng.randint(3, 6))
        slots["Ms" if multi else "M"] = self._lista_munis(sub, codigos) if multi else self.g.mencion(codigos[0], sub)[0]
        if not multi:
            slots["Ms"] = slots["M"]
        q = self.pregunta(sub, pq.G5_SIN_VARIABLE, slots)
        if q is None:
            return None
        texto, pid = q
        got = self.preparar(sub, texto)
        if got is None:
            return None
        r, ctx = got
        orden = [m["divipola"] for m in r["resolucion"]["municipios"]]
        if sorted(orden) != sorted(codigos if multi else codigos) or r["resolucion"]["variables"] or not ctx.opciones or not ctx.ubicaciones:
            self.descarta(sub, "resolucion_o_contexto")
            return None
        mds = ar.unir(self._md_de_resolucion(r))
        out = self.render(sub, rp.PLANTILLAS[sub], {"MDs": mds})
        if out is None:
            return None
        resp, pr = out
        return self.par("G5", sub, texto, r, resp, pid, pr)

    # ------------------------------------------------------------------ G6
    def _numeros_inventados(self, rng) -> str:
        n = rng.choice([3, 3, 4, 5])
        base = rng.randint(5, 70)
        paso = rng.randint(3, 25)
        vals = [base + paso * i + rng.randint(-2, 2) for i in range(n)]
        formato = rng.choice(["y", "coma", "pc"])
        if formato == "y":
            return ", ".join(map(str, vals[:-1])) + f" y {vals[-1]}"
        return ("; " if formato == "pc" else ", ").join(map(str, vals))

    def _g6(self, sub: str, banco: list[str], clave: str) -> Par | None:
        rng = self.rng(sub)
        cod = self.g.muni(sub)
        v = self.g.var_equilibrada(rng, VARS_6, "G6" + clave)
        con, sin = self.g.frase_var(v, sub)
        slots = {"M": self.g.mencion(cod, sub)[0], "V": con, "v": sin}
        if clave == "N":
            slots["N"] = self._numeros_inventados(rng)
        else:
            sin_anio = [x for x in pq.G6_FRAGMENTOS_X if not __import__("re").search(r"(?<!\d)(?:19|20)\d{2}(?!\d)", x)]
            _, slots["X"] = self.g.el(sub + ":x").de("x", sin_anio)
        q = self.pregunta(sub, banco, slots, {clave})
        if q is None:
            return None
        texto, pid = q
        got = self.preparar(sub, texto)
        if got is None:
            return None
        r, ctx = got
        err = self.resolucion_ok(r, [cod], [v], implicito=True)
        if err or not r["notas"]["intencion_grafica"]:
            self.descarta(sub, err or "sin_intencion_grafica")
            return None
        serie_ctx = self._serie(ctx, v, cod)
        serie = [i for i in serie_ctx if i.anio >= 2018]
        if ctx.sin_datos or len(serie) < 2 or len(serie_ctx) != len(ctx.items):
            self.descarta(sub, "serie_no_apta")
            return None
        y1, y2 = serie[0], serie[-1]
        nota, nid = self.notas.serie(serie, sub)
        slots_r = {"MD": y1.md, "V": ar.var_con_articulo(v), "Vc": ar.mayuscula(ar.var_con_articulo(v)), "Vde": ar.var_de(v),
                   "v": ar.var_sin_articulo(v), "Y1": y1.anio, "Y2": y2.anio, "V1": y1.texto, "V2": y2.texto, "nota": nota,
                   "tendencia": "subió" if y2.valor > y1.valor else "bajó"}
        excluir = () if y1.valor != y2.valor else tuple(i for i, t in enumerate(rp.PLANTILLAS[sub]) if "{tendencia}" in t)
        out = self.render(sub, rp.PLANTILLAS[sub], slots_r, excluir)
        if out is None:
            return None
        resp, pr = out
        return self._con_bloque(sub, texto, r, ctx, resp, pr + nid, "lineas", "individual", [v], [cod], [i.anio for i in serie])

    def g6_valores(self) -> Par | None:
        return self._g6("g6_valores", pq.G6_VALORES, "N")

    def g6_codigo(self) -> Par | None:
        return self._g6("g6_codigo", pq.G6_CODIGO, "X")

    # ------------------------------------------------------------------ despacho
    def generar(self, sub: str) -> Par | None:
        return getattr(self, sub)()
