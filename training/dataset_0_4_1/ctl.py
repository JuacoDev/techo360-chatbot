"""Controles por par de la Fase B (fase5-1 §6 adaptados a 0.4.1) y deduplicacion incremental.

Cada control devuelve None si pasa o un MOTIVO corto; el generador descarta y cuenta. Controles:
  dorada      re-armar con el pipeline real da EXACTAMENTE los mismos mensajes de entrada (historial incluido)
  cifras      validador 4.5 del backend (bloque quitado antes, como en el pipeline); con cifras citadas, estado «ok»
  grafica     G1/G6: `procesar_grafica` del backend acepta el bloque (esquema, combinacion, zonas, datos); sin bloque donde no toca
  forma       sin emojis, LightGBM, repos sin prefijo, dobles espacios; Markdown solo como lista de guiones valida y el bloque final
  lint        lint de redaccion de 5.2b D1 (de el, minuscula tras punto...)
  b_palabras  abstenciones sin «aproximadamente», «estimo», «alrededor», «cerca de»
  tokens      prompt completo (chat template multi-turno) + respuesta <= 1.720 tokens; respuesta <= 400
  similitud   la pregunta no se parece (>= 0,75) a ninguna de los conjuntos de evaluacion
"""
import re

from . import entorno

entorno.preparar_rutas()

from scripts.dataset_0_4.similitud import Conjunto, Tfidf, UMBRAL, coseno  # noqa: E402
from scripts.dataset_0_4.tokens import Tokenizador  # noqa: E402
from services.orquestador.contexto import LINEA_SIN_CONTEXTO  # noqa: E402
from services.orquestador.validador_cifras import validar_cifras  # noqa: E402
from services.orquestador.grafica_bloque import quitar_bloques  # noqa: E402

from . import armado as ar  # noqa: E402
from . import controles as ct  # noqa: E402
from . import listas as ls  # noqa: E402
from .motor import MAX_TOKENS_PAR, Entorno, Par, prompt_multiturno  # noqa: E402

EMOJI = re.compile("[\U0001F300-\U0001FAFF\U00002600-\U000027BF\U0001F000-\U0001F2FF]")
REPO_SIN_PREFIJO = re.compile(r"(?<!techo360-)\b(ai-service|proyeccion-service)\b", re.IGNORECASE)
PALABRAS_ABSTENCION = ("aproxim", "estimo", "alrededor", "cerca de")
SUBS_CON_BLOQUE = {"g1_lineas_individual", "g1_lineas_comparar", "g1_barras_ranking", "g1_barras_agrupadas_ind", "g1_barras_agrupadas_cmp",
                   "g1_gauge", "g6_valores", "g6_codigo"}
SUBS_ABSTENCION = {"g3_sin_dato", "g5_sin_municipio", "g5_sin_variable", "fp_estimar", "h3_sin_cobertura"}
SUBS_SIN_CIFRAS_PROPIAS = SUBS_ABSTENCION | {"h6_concepto_general", "fp_revelar_solo", "g4_tipo_no_soportado"}
from scripts.dataset_0_4.controles import LINT as _LINT_52  # noqa: E402  (sensible a mayusculas: «De El» de un nombre propio no es un error)
LINT_RESPUESTA = [(p, n.replace('lint:', '')) for p, n in _LINT_52]


def lineas_validador(par: Par) -> list[str]:
    bloque = par.mensajes[-1]["contenido"].split("\n\nPREGUNTA DEL USUARIO\n")[0]
    return [l for l in bloque.split("\n")[1:] if l and l != LINEA_SIN_CONTEXTO]


class Controles:
    def __init__(self, E: Entorno, tok: Tokenizador, evaluacion: dict[str, list[str]], corpus_idf: list[str]):
        self.E, self.tok = E, tok
        self.eval_preguntas = [q for qs in evaluacion.values() for q in qs]
        self.tf = Tfidf(corpus_idf + self.eval_preguntas)
        self.eval_vec = Conjunto()
        for q in self.eval_preguntas:
            self.eval_vec.agregar(self.tf.vec(q))
        self.maximos = {}

    # ------------------------------------------------------------------ controles individuales
    def dorada(self, par: Par) -> str | None:
        rearmado = self.E.rearmar(par.a_dict(0))
        return None if rearmado == par.mensajes else "dorada_difiere"

    def cifras(self, par: Par) -> str | None:
        items = []
        try:
            r = self.E.preparar(par.entrada["pregunta"], huecos=par.entrada.get("huecos"), historial=par.entrada.get("historial"),
                                previas=par.entrada.get("previas"), rag_resultados=par.entrada.get("rag_resultados"),
                                usar_rag=bool(par.entrada.get("rag_resultados")), forzar_rag=bool(par.entrada.get("rag_forzado")))
            items = r["peticion"]["contexto"]
        except Exception:  # noqa: BLE001
            return "cifras_no_rearma"
        texto = quitar_bloques(par.respuesta)
        v = validar_cifras(texto, lineas_validador(par), items, par.entrada["pregunta"])
        if v["estado"] == "no_validada":
            return "cifra_no_validada"
        cita = bool(items) and par.subfamilia not in SUBS_SIN_CIFRAS_PROPIAS and not par.subfamilia.startswith(("fp_revelar", "fp_ignorar", "h", "g4", "g5", "hs4"))
        if cita and v["estado"] != "ok" and par.subfamilia not in ("fp_falsos", "fp_revelar", "fp_ignorar"):
            return "sin_cifras_con_datos"
        return None

    def grafica(self, par: Par) -> str | None:
        con_bloque = "```grafica" in par.respuesta
        if par.subfamilia in SUBS_CON_BLOQUE:
            if not con_bloque:
                return "falta_bloque"
            g = self.E.validar_grafica(par.respuesta, par.entrada.get("huecos"))
            return None if g and g.get("valida") else "bloque_rechazado_por_backend"
        return "bloque_donde_no_corresponde" if con_bloque or "```" in par.respuesta else None

    def forma(self, par: Par) -> str | None:
        t = par.respuesta
        sin_bloque = quitar_bloques(t)
        if EMOJI.search(t):
            return "emoji"
        if "lightgbm" in t.lower():
            return "lightgbm"
        if REPO_SIN_PREFIJO.search(t):
            return "repo_sin_prefijo"
        if "  " in sin_bloque or "\t" in t or t != t.strip():
            return "espacios"
        p = ls.validar_formato(sin_bloque)
        if p:
            return "formato:" + p[0]
        if re.search(r"\.\.(?!\.)", sin_bloque):
            return "doble_punto"
        if "\n" in sin_bloque and not any(l.startswith("- ") for l in sin_bloque.split("\n")):
            if "\n\n" in sin_bloque:  # solo se admiten saltos con listas
                return "saltos_sin_lista"
        palabras = len(sin_bloque.split())
        if palabras > (230 if "\n- " in sin_bloque else 150):
            return "respuesta_larga"
        return None

    def lint(self, par: Par) -> str | None:
        t = quitar_bloques(par.respuesta)
        t = re.sub(r"\n- ", "\n", t)
        for patron, nombre in LINT_RESPUESTA:
            if patron.search(t):
                return "lint:" + nombre
        if len(re.findall(r"\bese año\b", t, re.IGNORECASE)) >= 2:
            return "lint:ese_anio_repetido"
        return None

    def abstencion(self, par: Par) -> str | None:
        if par.subfamilia in SUBS_ABSTENCION:
            bajo = ct.norm(par.respuesta)
            for p in PALABRAS_ABSTENCION:
                if p in bajo:
                    return "palabra_prohibida_abstencion"
        return None

    def tokens(self, par: Par) -> str | None:
        prompt = prompt_multiturno(par.mensajes)
        total, _ = self.tok.contar([prompt + par.respuesta + "<|eot_id|>", par.respuesta + "<|eot_id|>"])
        par.meta["tokens_total"], par.meta["tokens_respuesta"] = total, _
        if _ > 400:
            return "respuesta_mas_de_400_tokens"
        if total > MAX_TOKENS_PAR:
            return "mas_de_1720_tokens"
        return None

    def similitud(self, par: Par) -> str | None:
        q = par.entrada["pregunta"]
        s, _ = self.eval_vec.maximo(self.tf.vec(q))
        if s >= UMBRAL:
            return "similar_a_evaluacion"
        self.maximos[par.subfamilia] = max(self.maximos.get(par.subfamilia, 0.0), s)  # maximo entre los pares ACEPTADOS
        return None

    def todos(self, par: Par) -> str | None:
        for f in (self.dorada, self.cifras, self.grafica, self.forma, self.lint, self.abstencion, self.tokens, self.similitud):
            m = f(par)
            if m:
                return m
        return None


class Dedup:
    """Deduplicacion incremental por subfamilia (< 0,75), en pregunta y en respuesta por separado."""

    def __init__(self, tf_p: Tfidf, tf_r: Tfidf, umbral_r: float = UMBRAL):
        self.tf_p, self.tf_r, self.umbral_r = tf_p, tf_r, umbral_r
        self.p: dict[str, Conjunto] = {}
        self.r: dict[str, Conjunto] = {}
        self.ternas: dict[tuple, int] = {}
        self.por_intencion: dict[tuple, int] = {}
        self.tope_intencion = 6  # H: los extractos se comparten por diseño; maximo de pares por intencion y subfamilia
        self.max_r: dict[str, float] = {}

    def probar(self, par: Par, aceptar: bool = True) -> str | None:
        fam = par.familia
        q = par.entrada["pregunta"]
        cp, cr = self.p.setdefault(fam, Conjunto()), self.r.setdefault(fam, Conjunto())
        vp, vr = self.tf_p.vec(q), self.tf_r.vec(par.respuesta)
        if cp.maximo(vp)[0] >= UMBRAL:
            return "pregunta_duplicada"
        sr, _ = cr.maximo(vr)
        self.max_r[fam] = max(self.max_r.get(fam, 0.0), sr)
        if fam != "H" and sr >= self.umbral_r:
            return "respuesta_duplicada"
        if fam == "H" and "intencion" in par.meta and par.subfamilia in ("h1_un_fragmento", "h2_marginal", "h5_premisa"):
            clave = (par.subfamilia, par.meta["intencion"])
            if self.por_intencion.get(clave, 0) >= self.tope_intencion:
                return "tope_por_intencion"
            if aceptar:
                self.por_intencion[clave] = self.por_intencion.get(clave, 0) + 1
        e = par.entrada
        if len(e["municipios"]) == 1 and len(e["variables"]) == 1 and len(e["anios"]) == 1:
            k = (e["municipios"][0], e["variables"][0], e["anios"][0], par.familia)
            if self.ternas.get(k, 0) >= 3:
                return "terna_repetida"
        if aceptar:
            cp.agregar(vp)
            cr.agregar(vr)
            if len(e["municipios"]) == 1 and len(e["variables"]) == 1 and len(e["anios"]) == 1:
                self.ternas[k] = self.ternas.get(k, 0) + 1
        return None
