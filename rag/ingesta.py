"""Ingesta del corpus RAG (Fase 6.2): lee rag/corpus/*.md, fragmenta, calcula embeddings y
escribe en rag_documentos / rag_fragmentos (migracion 0005).

Reglas de seguridad (CLAUDE.md, plan 0.4):
  * Solo escribe en una base LOCAL: el DSN debe apuntar a localhost / 127.0.0.1 / ::1.
    Contra cualquier otro host el script se niega (la carga en produccion es el paso 6.8, [AUT]).
  * --dry-run no escribe nada: abre una transaccion de SOLO LECTURA, compara hashes y reporta
    cuantos fragmentos se insertarian, actualizarian, omitirian o desactivarian. No carga el modelo.
  * Idempotente: cada fragmento lleva sha256(texto embebido + modelo). Si el hash no cambia, no se
    recalcula el embedding ni se toca la fila. Un fragmento que ya no esta en el corpus se
    DESACTIVA (activo = false); nunca se borra.

Uso:
    RAG_DATABASE_URL=postgresql://usuario:clave@localhost:5433/techo360_vector_test \\
        python rag/ingesta.py [--dry-run] [--modelo e5-small] [--corpus rag/corpus]
    python rag/ingesta.py --solo-analizar        # sin base de datos: valida y fragmenta el corpus
"""
from __future__ import annotations

import argparse
import hashlib
import os
import re
import sys
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from urllib.parse import urlparse

AQUI = Path(__file__).resolve().parent
CORPUS_DEFECTO = AQUI / "corpus"
MAX_CHARS = 1100            # ~ 400 tokens reales (medido con el tokenizador de e5: 2,6-3,5 car/token)
CHARS_POR_TOKEN = 3.7
VERSION_CORPUS = "corpus-0.1"
CAMPOS = ("fragmento", "fuente", "ruta", "fecha", "vigencia", "version", "tema")

# nombre corto -> (id en Hugging Face, prefijo de consulta, prefijo de pasaje, dimension)
MODELOS = {
    "e5-small": ("intfloat/multilingual-e5-small", "query: ", "passage: ", 384),
    "minilm": ("sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2", "", "", 384),
    "bge-m3": ("BAAI/bge-m3", "", "", 1024),
}
MODELO_DEFECTO = "e5-small"

TITULOS = {
    "01-metodologia-score": "Metodologia del Score de privacion",
    "01-nota-discrepancias": "Nota de discrepancias entre fuentes",
    "02-ipm-conpes-150": "IPM y CONPES Social 150",
    "03-glosario": "Glosario",
    "04-decisiones-fuentes-metodos": "Decisiones publicas: fuentes y metodos",
    "05-divipola": "Notas DIVIPOLA",
    "06-guia-uso": "Guia de uso de la plataforma y del asistente",
}


@dataclass
class Fragmento:
    documento: str
    fragmento_id: str
    orden: int
    texto: str
    meta: dict = field(default_factory=dict)

    @property
    def entrada(self) -> str:
        """Texto que se embebe: el tema (titulo del fragmento) + el texto."""
        return f"{self.meta.get('tema', '')}\n{self.texto}".strip()

    def hash(self, modelo: str) -> str:
        base = "\x1f".join([modelo, self.entrada, self.meta.get("fuente", ""), self.meta.get("ruta", ""),
                            self.meta.get("fecha", ""), self.meta.get("vigencia", ""), self.meta.get("version", "")])
        return hashlib.sha256(base.encode("utf-8")).hexdigest()

    @property
    def tokens_estimados(self) -> int:
        return round(len(self.entrada) / CHARS_POR_TOKEN)


def parsear_archivo(ruta: Path) -> list[Fragmento]:
    """Lee un .md del corpus: bloques '---' con cabecera 'campo: valor' seguidos del texto."""
    lineas = ruta.read_text(encoding="utf-8").splitlines()
    nombre, out, i, orden = ruta.stem, [], 0, 0
    while i < len(lineas):
        if lineas[i] == "---" and i + 1 < len(lineas) and lineas[i + 1].startswith("fragmento:"):
            j, meta = i + 1, {}
            while j < len(lineas) and lineas[j] != "---":
                k, _, v = lineas[j].partition(":")
                meta[k.strip()] = v.strip()
                j += 1
            faltan = [c for c in CAMPOS if not meta.get(c)]
            if faltan:
                raise ValueError(f"{ruta.name}: fragmento {meta.get('fragmento', '?')} sin campos {faltan}")
            cuerpo, j = [], j + 1
            while j < len(lineas) and not (lineas[j] == "---" and j + 1 < len(lineas) and lineas[j + 1].startswith("fragmento:")):
                cuerpo.append(lineas[j])
                j += 1
            texto = "\n".join(cuerpo).strip()
            partes = fragmentar(texto)
            for n, t in enumerate(partes, 1):
                m = dict(meta)
                fid = meta["fragmento"] + (f"#{n}" if len(partes) > 1 else "")
                orden += 1
                out.append(Fragmento(nombre, fid, orden, t, m))
            i = j
        else:
            i += 1
    return out


def fragmentar(texto: str, max_chars: int = MAX_CHARS) -> list[str]:
    """Un fragmento ya viene dimensionado (<= ~400 tokens); solo se parte si se pasa del tope,
    por parrafos y, si un parrafo es mayor, por lineas."""
    if len(texto) <= max_chars:
        return [texto]
    partes, buf = [], ""
    for par in re.split(r"\n\s*\n", texto):
        for l in ([par] if len(par) <= max_chars else par.splitlines()):
            if buf and len(buf) + len(l) + 2 > max_chars:
                partes.append(buf)
                buf = ""
            buf = (buf + "\n\n" + l) if buf else l
    if buf:
        partes.append(buf)
    return partes


def cargar_corpus(directorio: Path) -> tuple[list[Fragmento], dict[str, str]]:
    """Devuelve (fragmentos, {documento: sha256 del archivo}); falla si hay ids repetidos."""
    frags, shas, vistos = [], {}, set()
    for ruta in sorted(directorio.glob("0*.md")):
        shas[ruta.stem] = hashlib.sha256(ruta.read_bytes()).hexdigest()
        for f in parsear_archivo(ruta):
            if (f.documento, f.fragmento_id) in vistos:
                raise ValueError(f"fragmento repetido: {f.documento}/{f.fragmento_id}")
            vistos.add((f.documento, f.fragmento_id))
            frags.append(f)
    if not frags:
        raise SystemExit(f"No hay fragmentos en {directorio}")
    return frags, shas


# ---------------------------------------------------------------------------
# Embeddings
# ---------------------------------------------------------------------------
def cargar_modelo(clave: str, hilos: int = 3):
    import torch
    from sentence_transformers import SentenceTransformer
    torch.set_num_threads(hilos)
    hf, pq, pp, dim = MODELOS[clave]
    return SentenceTransformer(hf, device="cpu"), pq, pp, dim


def embeber(modelo, prefijo: str, textos: list[str], lote: int = 8):
    return modelo.encode([prefijo + t for t in textos], batch_size=lote, normalize_embeddings=True,
                         show_progress_bar=False)


# ---------------------------------------------------------------------------
# Base de datos
# ---------------------------------------------------------------------------
def exigir_base_local(dsn: str) -> None:
    host = urlparse(dsn).hostname or ""
    if host not in ("localhost", "127.0.0.1", "::1"):
        raise SystemExit("Rechazado: la ingesta solo escribe en una base LOCAL (localhost/127.0.0.1). "
                         "La carga en produccion es el paso 6.8 y requiere autorizacion.")


def es_esperado(fragmento_id: str, esperados: list[str]) -> bool:
    """Un fragmento partido (id-1, id-2) cuenta como el id esperado."""
    return any(fragmento_id == e or fragmento_id.startswith(e + "-") for e in esperados)


def fecha_iso(s: str):
    try:
        return date.fromisoformat(s)
    except ValueError:
        return None


def plan_y_aplicar(dsn: str, frags: list[Fragmento], shas: dict[str, str], clave_modelo: str, dry_run: bool) -> dict:
    import psycopg
    from pgvector.psycopg import register_vector

    hf, pq, pp, dim = MODELOS[clave_modelo]
    stats = dict(nuevos=0, actualizados=0, omitidos=0, desactivados=0, documentos_nuevos=0, documentos_actualizados=0)
    with psycopg.connect(dsn, autocommit=False) as con:
        if dry_run:
            con.execute("SET TRANSACTION READ ONLY")
        register_vector(con)
        con.execute("SET LOCAL lock_timeout = '3s'")
        tabla = con.execute("SELECT to_regclass('public.rag_fragmentos'), to_regclass('public.rag_documentos')").fetchone()
        if None in tabla:
            raise SystemExit("Faltan rag_documentos/rag_fragmentos: aplicar antes la migracion 0005 (en la base LOCAL).")
        existentes = {(d, f): (h, a) for d, f, h, a in con.execute(
            "SELECT d.nombre, f.fragmento_id, f.sha256, f.activo FROM rag_fragmentos f JOIN rag_documentos d ON d.id = f.documento_id")}
        docs_db = {n: s for n, s in con.execute("SELECT nombre, sha256 FROM rag_documentos")}
        pendientes = []
        for f in frags:
            h = f.hash(hf)
            prev = existentes.get((f.documento, f.fragmento_id))
            if prev is None:
                stats["nuevos"] += 1
                pendientes.append((f, h))
            elif prev[0] != h or not prev[1]:
                stats["actualizados"] += 1
                pendientes.append((f, h))
            else:
                stats["omitidos"] += 1
        en_corpus = {(f.documento, f.fragmento_id) for f in frags}
        sobran = [k for k, (h, a) in existentes.items() if k not in en_corpus and a]
        stats["desactivados"] = len(sobran)
        stats["documentos_nuevos"] = sum(1 for d in shas if d not in docs_db)
        stats["documentos_actualizados"] = sum(1 for d, s in shas.items() if d in docs_db and docs_db[d] != s)
        if dry_run:
            con.rollback()
            return stats

        if pendientes:
            modelo, pq, pp, _ = cargar_modelo(clave_modelo)
            vecs = embeber(modelo, pp, [f.entrada for f, _ in pendientes])
            toks = [len(modelo.tokenizer(f.entrada, add_special_tokens=True)["input_ids"]) for f, _ in pendientes]
        else:
            vecs, toks = [], []
        # documentos
        ids_doc = {}
        for nombre, sha in shas.items():
            delf = [f for f in frags if f.documento == nombre]
            fecha_max = max((fecha_iso(f.meta["fecha"]) for f in delf if fecha_iso(f.meta["fecha"])), default=None)
            row = con.execute("""
                INSERT INTO rag_documentos (nombre, titulo, fuente, tipo_fuente, fecha_fuente, vigente_desde, version, sha256)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (nombre) DO UPDATE SET titulo = EXCLUDED.titulo, fecha_fuente = EXCLUDED.fecha_fuente,
                    vigente_desde = EXCLUDED.vigente_desde, version = EXCLUDED.version, sha256 = EXCLUDED.sha256,
                    activo = true, actualizado_en = now()
                RETURNING id""",
                (nombre, TITULOS.get(nombre, nombre), "varias (ver cada fragmento)", "mixta", fecha_max, fecha_max,
                 VERSION_CORPUS, sha)).fetchone()
            ids_doc[nombre] = row[0]
        for (f, h), v, t in zip(pendientes, vecs, toks):
            m = f.meta
            con.execute("""
                INSERT INTO rag_fragmentos (documento_id, fragmento_id, orden, texto, tokens, fuente, ruta, fecha_fuente,
                                            vigencia, version_fuente, tema, sha256, embedding, modelo_embedding, activo)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,true)
                ON CONFLICT (documento_id, fragmento_id) DO UPDATE SET orden = EXCLUDED.orden, texto = EXCLUDED.texto,
                    tokens = EXCLUDED.tokens, fuente = EXCLUDED.fuente, ruta = EXCLUDED.ruta,
                    fecha_fuente = EXCLUDED.fecha_fuente, vigencia = EXCLUDED.vigencia,
                    version_fuente = EXCLUDED.version_fuente, tema = EXCLUDED.tema, sha256 = EXCLUDED.sha256,
                    embedding = EXCLUDED.embedding, modelo_embedding = EXCLUDED.modelo_embedding, activo = true,
                    actualizado_en = now()""",
                (ids_doc[f.documento], f.fragmento_id, f.orden, f.texto, t, m["fuente"], m["ruta"],
                 fecha_iso(m["fecha"]), m["vigencia"], m["version"], m["tema"], h, v, hf))
        for d, fid in sobran:
            con.execute("UPDATE rag_fragmentos SET activo = false, actualizado_en = now() "
                        "WHERE fragmento_id = %s AND documento_id = (SELECT id FROM rag_documentos WHERE nombre = %s)",
                        (fid, d))
        con.commit()
    return stats


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--corpus", type=Path, default=CORPUS_DEFECTO)
    ap.add_argument("--modelo", choices=sorted(MODELOS), default=MODELO_DEFECTO)
    ap.add_argument("--dry-run", action="store_true", help="solo lectura: informa que haria, no escribe ni carga el modelo")
    ap.add_argument("--solo-analizar", action="store_true", help="no usa base de datos: valida y fragmenta el corpus")
    a = ap.parse_args(argv)

    frags, shas = cargar_corpus(a.corpus)
    toks = [f.tokens_estimados for f in frags]
    print(f"Corpus: {len(shas)} documentos, {len(frags)} fragmentos; tokens estimados por fragmento "
          f"min/mediana/max = {min(toks)}/{sorted(toks)[len(toks)//2]}/{max(toks)} (HIPOTESIS: 3,7 car./token)")
    if a.solo_analizar:
        return 0

    dsn = os.environ.get("RAG_DATABASE_URL")
    if not dsn:
        raise SystemExit("Falta RAG_DATABASE_URL (base LOCAL desechable). Con --solo-analizar no hace falta.")
    exigir_base_local(dsn)
    stats = plan_y_aplicar(dsn, frags, shas, a.modelo, a.dry_run)
    print(("[dry-run] " if a.dry_run else "") + ", ".join(f"{k}={v}" for k, v in stats.items()))
    return 0


if __name__ == "__main__":
    sys.exit(main())
