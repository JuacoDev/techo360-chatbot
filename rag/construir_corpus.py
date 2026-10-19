"""Construye rag/corpus/*.md extrayendo TEXTO REAL de las fuentes aprobadas en
claude/fase6-1-corpus.md (paso 6.1, parte mecanica). No reescribe: copia lineas
de las fuentes entre dos marcadores y las separa en fragmentos por parrafo.

Uso (desde cualquier carpeta):
    python rag/construir_corpus.py [--conpes-pdf RUTA.pdf] [--dry-run]

Las fuentes se buscan en los repos hermanos (../techo360-backend, ../techo360-frontend,
../techo360-chatbot) y en ../claude. Solo LEE; escribe unicamente en rag/corpus/.
El PDF del CONPES 150 no vive en el repo: se pasa por --conpes-pdf (si falta, el
documento 02 se omite y el hueco queda anotado en INDICE.md).

Cada fragmento lleva cabecera (fragmento, fuente, ruta, fecha, vigencia, version, tema).
"""
from __future__ import annotations

import argparse
import hashlib
import re
import subprocess
import sys
from datetime import date, datetime
from pathlib import Path

AQUI = Path(__file__).resolve().parent
ROOT = AQUI.parents[1]  # carpeta techo360/ (tanto desde el repo como desde un worktree hermano)
CORPUS = AQUI / "corpus"
MAX_CHARS = 1100  # ~ 400 tokens reales (medido: ~2,6-3,5 caracteres por token con este texto; ver INDICE)

# ---------------------------------------------------------------------------
# Definicion de extractos. Campos: doc, id, tema, ruta (relativa a ROOT), ini, fin,
# incl (True = la linea del marcador final tambien entra), modo (como limpiar el prefijo
# de comentario), vigencia, nota (opcional, aclaracion del corpus, no del texto copiado).
# ---------------------------------------------------------------------------
ZON = "techo360-backend/routers/zonas.py"
SCO = "techo360-backend/services/score_privacion.py"
ORI = "techo360-backend/services/origen.py"
DBP = "techo360-backend/ingestion/db.py"
DEF = "techo360-backend/ingestion/dane_deficit_adapter.py"
IGC = "techo360-backend/ingestion/igac_catastro_adapter.py"
VIG = "vigente en el codigo de la rama revisada"

E = []

# Limpieza de la revision del 18-oct-2026 (decision de Claude tras revisar el contenido; paso 6.5):
# fragmentos que NO se ingieren y frases que se quitan del texto copiado.
EXCLUIR = {
    "05-join-por-codigo", "04-metodos-por-variable-1", "04-metodos-por-variable-2",
    "01-doble-conteo-magnitud", "03-tenencia-limitacion-2", "02-ipm-vs-score",
    "01-nota-discrepancias",  # nota de mantenimiento, no contenido para usuarios
    "06-reglas-asistente",  # ya esta en el system prompt (decision de Claude, 18-oct)
}
REEMPLAZOS = {"03-tenencia": [("con el equipo ", "")]}


def x(doc, id_, tema, ruta, ini, fin, modo, incl=False, vigencia=VIG, nota=None, corte=None):
    """corte: si se da, la ULTIMA linea extraida se corta justo despues de esa cadena (fin de oracion)."""
    E.append(dict(doc=doc, id=id_, tema=tema, ruta=ruta, ini=ini, fin=fin, incl=incl,
                  modo=modo, vigencia=vigencia, nota=nota, corte=corte))


D1 = "01-metodologia-score"
x(D1, "formula", "Formula del Score de privacion y que significan 0 y 1", SCO,
  '"""Score compuesto de privacion (0=mejor', 'forma natural sin caso especial."""', "py", incl=True)
x(D1, "variables", "Variables del Score y direccion de cada una", ZON,
  "# Las 3 variables que entran al score", "# >>> AVISO: por que el componente", "hash")
x(D1, "doble-conteo", "Por que el componente de deficit es el cuantitativo y no el total", ZON,
  "# >>> AVISO: por que el componente", "#   - Deficit CUANTITATIVO (cols 11-14)", "hash")
x(D1, "doble-conteo-magnitud", "Magnitud del solapamiento entre deficit total y coberturas", ZON,
  "# MAGNITUD del solapamiento", "# POR QUE ESTA OPCION", "hash")
x(D1, "decision-cuantitativo", "Por que se mantienen las coberturas en el Score", ZON,
  "# POR QUE ESTA OPCION", "# IMPACTO MEDIDO", "hash")
x(D1, "limite-cuantitativo", "Limite de usar solo el deficit cuantitativo", ZON,
  "# LIMITE HONESTO", "# normalizar_minmax()/calcular_score_privacion() se movieron", "hash")
x(D1, "normalizacion", "Normalizacion min-max recortada a [0, 1]", SCO,
  '"""Normalizacion min-max, RECORTADA', 'no cambia nada."""', "py", incl=True)
x(D1, "limites-por-anio", "Limites min-max: del propio anio en datos reales, fijos de 2024 en proyeccion", SCO,
  "Notese que calcular_score_privacion()", "cambiar su contrato/comportamiento para el camino real.", "py", incl=True)
x(D1, "limites-base", "Limites fijos del anio base 2024 para el Score proyectado", SCO,
  '"""Min/max de cada una de las 3 variables', 'del año base queden en la MISMA escala."""', "py", incl=True)
x(D1, "universo", "Universo de municipios que fija la escala del Score", SCO,
  '"""Codigos de los municipios REALES', 'ningun poligono."""', "py", incl=True)

D2 = "02-ipm-conpes-150"
CONPES_URL = "https://colaboracion.dnp.gov.co/CDT/Conpes/Social/150.pdf"
x(D2, "ipm-origen", "Que es el IPM-Colombia y quien lo desarrollo", "PDF",
  "En cuanto al Índice de Pobreza Multidimensional", "cinco grupos o dimensiones.", "pdf", incl=True,
  vigencia="CONPES Social 150, 28-may-2012 (version aprobada); metodologia oficial vigente a la fecha del documento")
x(D2, "ipm-definicion", "Definicion del IPM y por que se adopto", "PDF",
  "El Índice de Pobreza Multidimensional (IPM), desarrollado", "pobreza en Colombia", "pdf", incl=True,
  vigencia="CONPES Social 150, 28-may-2012")
x(D2, "ipm-dimensiones", "Cinco dimensiones del IPM y pesos iguales", "PDF",
  "El IPM Colombia está conformado por cinco dimensiones", "dimensión29", "pdf", incl=True,
  vigencia="CONPES Social 150, 28-may-2012")
x(D2, "ipm-tabla", "Tabla de dimensiones, variables y ponderadores del IPM-Colombia", "PDF",
  "Dimensiones y variables del IPM de Colombia", "Fuente: DNP-DDS-SPSCV", "pdf", incl=True,
  vigencia="CONPES Social 150, 28-may-2012")
x(D2, "ipm-unidad", "Unidad de analisis del IPM y fuente de datos", "PDF",
  "Para el cálculo del IPM se utiliza al hogar", "años 1997, 2003, 2008 y 2010", "pdf", incl=True,
  vigencia="CONPES Social 150, 28-may-2012", corte="2008 y 2010")
x(D2, "ipm-umbral", "Cuando un hogar es multidimensionalmente pobre (umbral del 33 %)", "PDF",
  "Identificación de las personas en pobreza multidimensional", "ponderación asignada a cada una de ellas.",
  "pdf", incl=True, vigencia="CONPES Social 150, 28-may-2012")
x(D2, "ipm-vs-score", "Relacion entre el IPM oficial y el Score de privacion del proyecto", ZON,
  "# de nombres de campo de la API)", "# Acueducto y alcantarillado se INVIERTEN", "hash",
  nota="Texto del proyecto (codigo), no del CONPES: contrasta el IPM oficial (umbral k=33 %) con el Score.")

D3 = "03-glosario"
x(D3, "deficit-componentes", "Deficit cuantitativo y cualitativo: componentes segun el anexo DANE", ZON,
  "#   - Deficit CUANTITATIVO (cols 11-14)", "# MAGNITUD del solapamiento", "hash")
x(D3, "deficit-columnas", "Deficit habitacional municipal DANE: hogares y porcentajes", DEF,
  "    4: Total de hogares", "    11+: componentes", "py",
  nota="Lista de columnas del anexo del DANE tal como la documenta el adaptador de ingesta.")
x(D3, "deficit-anio", "Anio real del deficit municipal (CNPV 2018)", DEF,
  "AÑO: el censo (CNPV)", "la metodologia se PUBLICO en 2020.", "py", incl=True, corte="se PUBLICO en 2020.")
x(D3, "densidad", "Densidad poblacional: poblacion DANE sobre area", DBP,
  "para densidad_poblacional, calculado como poblacion municipal", "IGAC). Reemplaza a", "gt", incl=True, corte="IGAC).")
x(D3, "tenencia", "Tenencia informal: unidad de medida y formula", IGC,
  "UNIDAD DE MEDIDA:", ">>> LIMITACION CONOCIDA", "py")
x(D3, "tenencia-limitacion", "Tenencia informal: limitacion conocida de la fuente", IGC,
  "El 73% de los municipios con fila real", "en vez de reflejarla genuinamente.", "py", incl=True)
x(D3, "dato-real-proyeccion", "Dato real frente a proyeccion: regla de clasificacion", ORI,
  "    es_proyeccion(origen) = origen EMPIEZA", "NO es '%proyeccion%'", "py")
x(D3, "dato-real", "Dato real: definicion operativa y fila sin origen", ORI,
  "es_real = not es_proyeccion.", "patrones y se trata como real.", "py", incl=True)
x(D3, "fiabilidad", "Fiabilidad de un dato (0 a 100)", ORI,
  "fiabilidad_de_origen(): fiabilidad", '"""', "py")

D4 = "04-decisiones-fuentes-metodos"
x(D4, "principio-procedencia", "Principio: ningun dato estimado se confunde con un dato real", DBP,
  ">>> procedencia de datos", ">>> Valores de originVar en uso", "gt")
x(D4, "fuente-cnpv", "Fuente del deficit habitacional municipal: DANE, CNPV 2018", DEF,
  "Confirmado en vivo (descarga real", "Hoja \"Total Municipios\"", "py")
x(D4, "metodo-ultimo-valor", "Metodo de las coberturas proyectadas: ultimo valor observado", DBP,
  '"proyeccion-ultimo-valor-observado-{anio}"', "no un numero inventado).", "gt", incl=True)
x(D4, "metodo-regresion-densidad", "Metodo de la densidad proyectada: regresion lineal de 4 puntos", DBP,
  '"proyeccion-regresion-lineal-4puntos"', "no mediciones independientes).", "gt", incl=True)
x(D4, "metodo-deficit-2024", "Metodo del deficit 2024: tendencia nacional 2018-2024", DBP,
  '"proyeccion-tendencia-nacional-2018-2024" (agregado', '"proyeccion-snapshot-2026"', "gt",
  nota="Ver 01-nota-discrepancias: la carga M4 pendiente cambia este metodo (saturacion suave).")
x(D4, "metodos-implementados", "Metodos de proyeccion implementados y score al vuelo", "claude/fase3-diagnostico.md",
  "- Métodos implementados:", "- Redis:", "md",
  vigencia="informe del 17-oct-2026; el estado de la nota sobre Score (limites fijos de 2024) rige solo para proyecciones")
x(D4, "metodos-por-variable", "Metodo por variable y caso (huecos municipio-anio)", "claude/fase3-4-umbrales-y-metodos.md",
  "| Variable y caso | Método |", "Reglas comunes:", "md",
  vigencia="PROPUESTA del 17-oct-2026 (decisiones de Juan incorporadas); implementacion posterior no verificada por esta extraccion",
  nota="Contiene la regla del deficit 2019-2023 por interpolacion lineal entre 2018 real y 2024 proyectado.")

D5 = "05-divipola"
x(D5, "codigos-oficiales", "Cuantos municipios y codigos DIVIPOLA hay en Colombia: 1.122 codigos oficiales y sus tipos", "claude/fase1-2-divipola-cruce.md",
  "Hoja `Municipios`: **1 122 códigos", "**Corrección a un dato del encargo:**", "md",
  vigencia="DIVIPOLA DANE actualizado al 30-jun-2026")
x(D5, "areas-no-municipalizadas", "Las 18 areas no municipalizadas sin poligono en el mapa", "claude/fase1-2-divipola-cruce.md",
  "**18 códigos en DIVIPOLA sin geometría en el geojson.**", "(Nombres de Vaupés verificados", "md",
  vigencia="DIVIPOLA DANE actualizado al 30-jun-2026")
x(D5, "caso-00000", "El codigo 00000: Area en Litigio Cauca-Huila", ZON,
  '# "Area En Litigio Cauca - Huila": existe', "CODIGOS_MUNICIPIO_EXCLUIDOS = ", "hash")
x(D5, "nombres-distintos", "Nombre oficial frente a nombre corto en los mismos codigos", "claude/fase1-2-divipola-cruce.md",
  "**Nombres.** En los 1 104 códigos comunes", "\n", "md", vigencia="DIVIPOLA DANE actualizado al 30-jun-2026")
x(D5, "join-por-codigo", "Regla: unir siempre por codigo DIVIPOLA, nunca por nombre", "CLAUDE.md",
  "- **Join por `codigoDivipola`", "- **Prefijo", "md")

D6 = "06-guia-uso"
x(D6, "reglas-asistente", "Que puede y que no puede responder el asistente (reglas de su prompt)",
  "techo360-chatbot/prompts/sp-0.4.0-1.txt", "Eres el asistente virtual", None, "raw",
  vigencia="system prompt sp-0.4.0-1")
x(D6, "tarjeta-fiabilidad", "Panel de indicadores: dato confirmado frente a proyeccion y su insignia de fiabilidad",
  "techo360-frontend/src/components/fiabilidadTarjeta.js", "// Regla (misma que el resto del frontend)",
  "// `proyectado` es el prop historico", "js")
x(D6, "estado-mensajes", "TechoBot: estados de un mensaje", "techo360-frontend/README.md",
  "- Cada mensaje de usuario tiene estado:", "- Un mensaje sin resolver", "md")

NOTA_DISCREPANCIAS = """\
Revision de discrepancias entre fuentes (hecha al construir el corpus, 2026-10-18):
1. No se encontro README del backend ni del frontend que describa la formula del Score; la unica fuente son los comentarios de routers/zonas.py y los docstrings de services/score_privacion.py. No hay version de README con la que contrastar.
2. El comentario de zonas.py dice que el deficit de 2024 es una proyeccion con fiabilidad 70 %; el README del backend advierte que la carga M4 (pendiente de aplicar) reemplazara 102 anclas del deficit cuantitativo 2024 por una variante con saturacion suave. Mientras no se aplique, manda el codigo y el comentario; despues de aplicarla, los fragmentos de 04-decisiones-fuentes-metodos (deficit 2024) y 01-metodologia-score deben revisarse.
3. Los limites min-max del Score son los del propio anio en el camino de datos reales y los fijos de 2024 en el camino de proyeccion (ver 01-metodologia-score); no es una contradiccion, pero una respuesta no debe mezclarlos.
"""


# ---------------------------------------------------------------------------
def _git_info(ruta: Path) -> tuple[str, str]:
    """(fecha ISO, version) de la ultima modificacion de un archivo: commit si esta en un repo,
    mtime si no."""
    for repo in ("techo360-backend", "techo360-frontend", "techo360-chatbot"):
        base = ROOT / repo
        try:
            rel = ruta.relative_to(base)
        except ValueError:
            continue
        r = subprocess.run(["git", "-C", str(base), "log", "-1", "--format=%cs|%h", "--", str(rel)],
                           capture_output=True, text=True)
        if r.returncode == 0 and "|" in r.stdout:
            f, h = r.stdout.strip().split("|")
            return f, f"{repo}@{h}"
    return datetime.fromtimestamp(ruta.stat().st_mtime).date().isoformat(), "sin-control-de-versiones (mtime)"


def _limpiar(linea: str, modo: str) -> str:
    if modo == "hash":
        return re.sub(r"^#\s?", "", linea)
    if modo == "gt":
        return re.sub(r"^>>>\s{0,3}", "", linea)
    if modo == "js":
        return re.sub(r"^//\s?", "", linea)
    if modo == "py":
        linea = linea.replace('"""', "")
        return linea[4:] if linea.startswith("    ") else linea
    return linea


def extraer(lineas: list[str], e: dict) -> list[str]:
    i = next((k for k, l in enumerate(lineas) if e["ini"] in l), None)
    if i is None:
        raise SystemExit(f"marcador inicial no encontrado: {e['doc']}/{e['id']}: {e['ini']!r}")
    if e["fin"] is None:
        j = len(lineas)
    elif e["fin"] == "\n":
        j = i + 1  # solo esa linea
    else:
        j = next((k for k in range(i + (0 if e["fin"] == e["ini"] else 1), len(lineas)) if e["fin"] in lineas[k]), None)
        if j is None:
            raise SystemExit(f"marcador final no encontrado: {e['doc']}/{e['id']}: {e['fin']!r}")
        if e["incl"]:
            j += 1
    out = [_limpiar(l.rstrip("\n"), e["modo"]) for l in lineas[i:j]]
    if e.get("corte"):
        k = out[-1].find(e["corte"])
        if k < 0:
            raise SystemExit(f"corte no encontrado: {e['id']}")
        out[-1] = out[-1][:k + len(e["corte"])]
    return out


def partir(texto: list[str]) -> list[str]:
    """Agrupa parrafos (separados por linea vacia) hasta MAX_CHARS; un parrafo mayor se parte por lineas."""
    parrafos, actual = [], []
    for l in texto:
        if l.strip() == "":
            if actual:
                parrafos.append(actual)
                actual = []
        else:
            actual.append(l)
    if actual:
        parrafos.append(actual)
    trozos, buf = [], ""
    for p in parrafos:
        cuerpo = "\n".join(p)
        if len(cuerpo) > MAX_CHARS:
            if buf:
                trozos.append(buf)
                buf = ""
            sub = ""
            for l in p:
                if sub and len(sub) + len(l) + 1 > MAX_CHARS:
                    trozos.append(sub)
                    sub = ""
                sub = (sub + "\n" + l) if sub else l
            if sub:
                trozos.append(sub)
            continue
        if buf and len(buf) + len(cuerpo) + 2 > MAX_CHARS:
            trozos.append(buf)
            buf = ""
        buf = (buf + "\n\n" + cuerpo) if buf else cuerpo
    if buf:
        trozos.append(buf)
    return trozos


def texto_pdf(ruta_pdf: Path) -> list[str]:
    from pypdf import PdfReader
    out = []
    for p in PdfReader(str(ruta_pdf)).pages:
        for l in p.extract_text(extraction_mode="layout").splitlines():
            out.append(re.sub(r"\s{2,}", " ", l).strip())
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--conpes-pdf", type=Path)
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    pdf_sha, huecos = None, []
    pdf_lineas = None
    if a.conpes_pdf and a.conpes_pdf.exists():
        pdf_sha = hashlib.sha256(a.conpes_pdf.read_bytes()).hexdigest()
        pdf_lineas = texto_pdf(a.conpes_pdf)
    else:
        huecos.append("02-ipm-conpes-150: no se paso --conpes-pdf; documento omitido.")

    docs: dict[str, list[str]] = {}
    filas = []
    for e in E:
        if e["ruta"] == "PDF":
            if pdf_lineas is None:
                continue
            lineas, fecha, version, ruta_txt = pdf_lineas, "2012-05-28", f"pdf-sha256:{pdf_sha[:12]}", CONPES_URL
            fuente = "DNP - CONPES Social 150 (Metodologias oficiales y arreglos institucionales para la medicion de la pobreza en Colombia)"
        else:
            ruta = ROOT / e["ruta"]
            lineas = ruta.read_text(encoding="utf-8").splitlines()
            fecha, version = _git_info(ruta)
            ruta_txt = e["ruta"]
            fuente = "Proyecto Techo 360 - " + Path(e["ruta"]).name
        trozos = partir(extraer(lineas, e))
        for n, t in enumerate(trozos, 1):
            fid = f"{e['doc'][:2]}-{e['id']}" + (f"-{n}" if len(trozos) > 1 else "")
            if fid in EXCLUIR:
                continue
            for antes, despues in REEMPLAZOS.get(fid, []):
                if antes not in t:
                    raise SystemExit(f"reemplazo no aplicable en {fid}: {antes!r}")
                t = t.replace(antes, despues)
            cab = [f"fragmento: {fid}", f"fuente: {fuente}", f"ruta: {ruta_txt}", f"fecha: {fecha}",
                   f"vigencia: {e['vigencia']}", f"version: {version}", f"tema: {e['tema']}"]
            if e["nota"]:
                cab.append(f"nota: {e['nota']}")
            bloque = "---\n" + "\n".join(cab) + "\n---\n" + t.strip() + "\n"
            docs.setdefault(e["doc"], []).append(bloque)
            filas.append((e["doc"], fid, len(t)))

    # Nota de discrepancias (texto del corpus, no copiado de una fuente)
    if "01-nota-discrepancias" not in EXCLUIR:
      docs.setdefault("01-nota-discrepancias", []).append(
        "---\nfragmento: 01-nota-discrepancias\nfuente: Nota del corpus (revision de discrepancias)\n"
        "ruta: rag/construir_corpus.py\nfecha: 2026-10-18\nvigencia: hasta aplicar la carga M4\n"
        "version: corpus-0.1\ntema: Diferencias detectadas entre codigo y README sobre el Score y el deficit\n---\n"
        + NOTA_DISCREPANCIAS)
      filas.append(("01-nota-discrepancias", "01-nota-discrepancias", len(NOTA_DISCREPANCIAS)))

    if a.dry_run:
        for d, f, n in filas:
            print(d, f, n)
        return
    CORPUS.mkdir(exist_ok=True)
    for old in CORPUS.glob("0*.md"):
        old.unlink()
    indice = ["# Indice del corpus RAG (generado por rag/construir_corpus.py)", "",
              f"Generado: {date.today().isoformat()}. Fuentes: ver cabecera de cada fragmento.", "",
              "| Documento | Fragmentos | Caracteres | sha256 |", "|---|---:|---:|---|"]
    total_f = total_c = 0
    for nombre, bloques in sorted(docs.items()):
        cuerpo = "\n".join(bloques)
        (CORPUS / f"{nombre}.md").write_text(cuerpo, encoding="utf-8", newline="\n")
        sha = hashlib.sha256(cuerpo.encode("utf-8")).hexdigest()
        nc = sum(n for d, _, n in filas if d == nombre)
        indice.append(f"| {nombre}.md | {len(bloques)} | {nc} | `{sha}` |")
        total_f += len(bloques)
        total_c += nc
    indice.append(f"| **Total** | **{total_f}** | **{total_c}** | |")
    if pdf_sha:
        indice += ["", f"PDF del CONPES 150 usado (no versionado): {CONPES_URL}", f"sha256 del PDF: `{pdf_sha}`"]
    indice += ["", "## Huecos anotados", ""] + [f"- {h}" for h in huecos] + HUECOS_FIJOS
    (CORPUS / "INDICE.md").write_text("\n".join(indice) + "\n", encoding="utf-8", newline="\n")
    print(f"{total_f} fragmentos, {total_c} caracteres")


HUECOS_FIJOS = [
    "- Glosario: no hay texto fuente en los repos con la definicion oficial de cobertura de acueducto ni de alcantarillado (DANE/SSPD/DNP); no se inventa. Pendiente de aprobacion de una fuente publica.",
    "- Glosario: la densidad poblacional solo tiene la formula del proyecto (poblacion DANE / area), no una definicion oficial.",
    "- Guia de uso (#6): no existe README de usuario; solo reglas del prompt, comentarios del frontend y estados de mensaje. No hay texto fuente que describa el mapa de calor ni el panel en lenguaje de usuario.",
    "- IPM: solo CONPES Social 150 (2012). Las actualizaciones posteriores del IPM (p. ej. DANE 2018) no estan en el corpus.",
]

if __name__ == "__main__":
    sys.exit(main())
