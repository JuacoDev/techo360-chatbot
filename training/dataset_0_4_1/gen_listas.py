"""Regeneracion con listas de A3 (serie >= 3 lineas), A4 (>= 3 municipios) y A5 (perfil >= 3 variables) de 0.4.0 (adenda 7.1b §2).

La pregunta y el contexto son los de 0.4.0, re-armados con el pipeline real; solo cambia la respuesta: introduccion en prosa que
termina en «:» y un elemento por linea con la cifra copiada del contexto («- 2019: 90,1 % (dato real)»). Con menos de 3 elementos
el par no se toca aqui (se queda la prosa de 0.4.0, control negativo).
"""
from . import armado as ar
from . import listas as ls
from .fabrica import Fabrica
from .motor import Par

TIPO_POR_SUB = {"A3": "lst_serie", "A4": "lst_municipios", "A5": "lst_perfil"}


class GenListas(Fabrica):
    def regenerar(self, par040: dict) -> Par | None:
        """`par040`: un registro de train_nuevos 0.4.0 de subfamilia A3, A4 o A5. -> Par con lista, o None (se queda en prosa)."""
        sub040 = par040["subfamilia"]
        tipo = TIPO_POR_SUB[sub040]
        e = par040["entrada"]
        got = self.preparar(tipo, e["pregunta"], huecos=e.get("huecos"), usar_rag=False)
        if got is None:
            return None
        r, ctx = got
        user_040 = par040["instruction"]
        if r["peticion"]["mensajes"][-1]["contenido"] != user_040:
            self.descarta(tipo, "contexto_distinto_de_0.4.0")
            return None
        if ctx.sin_datos or ctx.omitidos or ctx.opciones or ctx.docs or ctx.ubicaciones:
            self.descarta(tipo, "contexto_con_lineas_especiales")
            return None
        items = sorted(ctx.items, key=lambda i: (i.divipola, i.variable, i.anio)) if sub040 == "A3" else list(ctx.items)
        if len(items) < ls.MIN_ELEMENTOS:
            self.descarta(tipo, "menos_de_3_elementos")
            return None
        munis, variables, anios = {i.divipola for i in items}, {i.variable for i in items}, {i.anio for i in items}
        if len(items) != len({(i.divipola, i.variable, i.anio) for i in items}):
            self.descarta(tipo, "elementos_repetidos")
            return None
        if sub040 == "A3":
            # el orden del contexto es municipio -> variable -> año: se respeta
            items = list(ctx.items)
        # forma de la lista segun las dimensiones que varian
        if len(munis) == 1 and len(variables) == 1:
            forma_id, tipo_intro = "serie", "lst_serie"
        elif len(variables) == 1 and len(anios) == 1:
            forma_id, tipo_intro = "municipios", "lst_municipios"
        elif len(munis) == 1 and len(anios) == 1:
            forma_id, tipo_intro = "perfil", "lst_perfil"
        else:
            forma_id, tipo_intro = "general", "lst_general"
        intros, formas, permitidos = ls.TIPOS[tipo_intro]
        elementos = []
        for it in items:
            clave = "real" if it.real else "estimado"
            slots_i = {"Y": it.anio, "val": it.texto, "MD": it.md, "Vn": ar.nombre_var_cap(it.variable),
                       "Fn": ar.fiab_numero([it]) if not it.real else ""}
            if forma_id == "serie":
                forma = formas[clave]
            elif forma_id == "municipios":
                forma = formas[clave] if len(anios) == 1 else ls.ITEM_MUNICIPIO_ANIO[clave]
            elif forma_id == "perfil":
                forma = formas[clave]
            else:
                partes = []
                if len(munis) > 1:
                    partes.append(it.md)
                if len(variables) > 1:
                    partes.append(ar.nombre_var_cap(it.variable))
                if len(anios) > 1 or it.implicito:
                    partes.append(str(it.anio))
                slots_i["Etiqueta"] = ", ".join(partes)
                forma = formas[clave]
            elementos.append(forma.format(**slots_i))
        v0 = items[0].variable
        slots = {
            "MD": items[0].md, "V": ar.var_con_articulo(v0), "Vc": ar.mayuscula(ar.var_con_articulo(v0)), "v": ar.var_sin_articulo(v0),
            "Y1": items[0].anio, "Y2": items[-1].anio,
        }
        if len(anios) == 1:
            slots["Y"] = items[0].anio
        if forma_id == "municipios":
            slots.pop("MD")
        if forma_id == "perfil":
            for k in ("V", "Vc", "v", "Y1", "Y2"):
                slots.pop(k, None)
        if forma_id == "general":
            slots = {}
        e_i = ar.elegir(self.g.el("lst:" + tipo_intro), "lst:" + tipo_intro, intros, slots)
        if e_i is None:
            self.descarta(tipo, "sin_introduccion_compatible")
            return None
        i, intro = e_i
        cierre = None
        if any(not it.real for it in items):
            _, cierre = self.g.el("lstc:" + tipo).de("c", ls.CIERRES_ESTIMACION)
        respuesta = ls.armar_lista(intro.format(**slots), elementos, cierre)
        if ls.validar_formato(respuesta):
            self.descarta(tipo, "formato:" + ls.validar_formato(respuesta)[0])
            return None
        par = self.par(par040["familia"], f"{tipo}", e["pregunta"], r, respuesta, par040.get("plantilla_pregunta", ""), f"{tipo_intro}.i{i:02d}",
                       huecos_=e.get("huecos"), meta={"origen_0_4_0": par040["id"], "subfamilia_0_4_0": sub040})
        par.id = f"{tipo}-{par040['id']}"
        return par
