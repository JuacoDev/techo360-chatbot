"""Recuperador RAG REAL sobre un Postgres LOCAL desechable (para generar los contextos con [dN] de H).

Levanta `pgvector/pgvector:pg16` en 127.0.0.1:55433 (imagen ya local), aplica las migraciones 0001 y 0005 del chatbot, carga el corpus
FINAL de rag/corpus/ con el mismo parser de `rag/ingesta.py` y consulta con `services.orquestador.rag.buscar_fragmentos` del
backend (texto en español, ts_rank). Los embeddings no intervienen en ese recuperador: se cargan como vector cero y se dice asi en
el informe. Nada de esto toca produccion: el contenedor se crea y se destruye aqui, y la contrasena se genera al vuelo y no se imprime.

    with RagLocal() as rag:
        rag.buscar("¿Qué es el IPM?")
"""
import hashlib
import secrets
import subprocess
import sys
import time
from datetime import date
from pathlib import Path

from . import entorno

entorno.preparar_rutas()

import psycopg2  # noqa: E402
from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402

CONTENEDOR = "techo360-ds73-pgvector"
PUERTO = 55433
BASE = "techo360_vector_ds73"
IMAGEN = "pgvector/pgvector:pg16"
# Solo 0001 (crea conversaciones y mensajes, que 0005 exige) y 0005 (tablas del RAG). 0002-0004 traen verificaciones de backfill
# ligadas a los datos de produccion y no intervienen en la busqueda.
MIGRACIONES = ["0001_conversaciones_mensajes.sql", "0005_rag_documentos_fragmentos.sql"]
VERSION_CORPUS = "corpus-0.1"
CERO = "[" + ",".join(["0"] * 384) + "]"


def _docker(*args: str, entrada: bytes | None = None, check: bool = True) -> subprocess.CompletedProcess:
    r = subprocess.run(["docker", *args], input=entrada, capture_output=True)
    if check and r.returncode != 0:
        raise RuntimeError(f"docker {args[0]} fallo: {r.stderr.decode('utf-8', 'replace')[:300]}")
    return r


class RagLocal:
    def __init__(self, corpus: Path | None = None, conservar: bool = False):
        self.corpus = corpus or (entorno.RAIZ_CHATBOT / "rag" / "corpus")
        self.clave = secrets.token_urlsafe(18)
        self.conservar = conservar
        self.sesion = None
        self.cache: dict[str, list[dict]] = {}
        self.meta: dict = {}

    # ------------------------------------------------------------------ ciclo de vida
    def __enter__(self):
        try:
            return self._iniciar()
        except BaseException:
            _docker("rm", "-f", "-v", CONTENEDOR, check=False)
            raise

    def _iniciar(self):
        _docker("rm", "-f", CONTENEDOR, check=False)
        _docker("run", "-d", "--name", CONTENEDOR, "-e", f"POSTGRES_PASSWORD={self.clave}", "-e", f"POSTGRES_DB={BASE}",
                "-p", f"127.0.0.1:{PUERTO}:5432", IMAGEN)
        self._esperar()
        for m in MIGRACIONES:
            sql = (entorno.RAIZ_CHATBOT / "migrations" / m).read_bytes()
            r = _docker("exec", "-i", CONTENEDOR, "psql", "-U", "postgres", "-d", BASE, "-v", "ON_ERROR_STOP=1", "-q", entrada=sql, check=False)
            if r.returncode != 0:
                raise RuntimeError(f"migracion {m} fallo: {r.stderr.decode('utf-8', 'replace')[:300]}")
        self._cargar()
        motor = create_engine(f"postgresql+psycopg2://postgres:{self.clave}@127.0.0.1:{PUERTO}/{BASE}")
        self.sesion = sessionmaker(bind=motor)()
        return self

    def __exit__(self, *exc):
        if self.sesion is not None:
            self.sesion.close()
        if not self.conservar:
            _docker("rm", "-f", "-v", CONTENEDOR, check=False)

    def _esperar(self) -> None:
        for _ in range(60):
            r = _docker("exec", CONTENEDOR, "pg_isready", "-U", "postgres", "-d", BASE, check=False)
            if r.returncode == 0:
                time.sleep(2)  # el init crea la base y reinicia el servidor una vez
                r2 = _docker("exec", CONTENEDOR, "pg_isready", "-U", "postgres", "-d", BASE, check=False)
                if r2.returncode == 0:
                    return
            time.sleep(1)
        raise RuntimeError("Postgres local no arranco")

    # ------------------------------------------------------------------ carga del corpus
    def _cargar(self) -> None:
        sys.path.insert(0, str(entorno.RAIZ_CHATBOT / "rag"))
        import ingesta  # noqa: E402  (parser del corpus; sus imports pesados son perezosos)
        frags, shas = ingesta.cargar_corpus(self.corpus)
        con = psycopg2.connect(host="127.0.0.1", port=PUERTO, dbname=BASE, user="postgres", password=self.clave)
        try:
            cur = con.cursor()
            ids = {}
            for nombre, sha in shas.items():
                delf = [f for f in frags if f.documento == nombre]
                fechas = [ingesta.fecha_iso(f.meta["fecha"]) for f in delf if ingesta.fecha_iso(f.meta["fecha"])]
                fecha = max(fechas, default=None)
                cur.execute(
                    "INSERT INTO rag_documentos (nombre, titulo, fuente, tipo_fuente, fecha_fuente, vigente_desde, version, sha256) "
                    "VALUES (%s,%s,%s,%s,%s,%s,%s,%s) RETURNING id",
                    (nombre, ingesta.TITULOS.get(nombre, nombre), "varias (ver cada fragmento)", "mixta", fecha, fecha, VERSION_CORPUS, sha))
                ids[nombre] = cur.fetchone()[0]
            for f in frags:
                m = f.meta
                cur.execute(
                    "INSERT INTO rag_fragmentos (documento_id, fragmento_id, orden, texto, tokens, fuente, ruta, fecha_fuente, vigencia, "
                    "version_fuente, tema, sha256, embedding, modelo_embedding, activo) "
                    "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s::vector,%s,true)",
                    (ids[f.documento], f.fragmento_id, f.orden, f.texto, f.tokens_estimados, m["fuente"], m["ruta"],
                     ingesta.fecha_iso(m["fecha"]), m["vigencia"], m["version"], m["tema"], f.hash("sin-embedding"), CERO, "sin-embedding"))
            con.commit()
        finally:
            con.close()
        self.meta = {
            "fragmentos": len(frags), "documentos": len(shas),
            "sha256_corpus": hashlib.sha256("".join(f"{k}:{v}" for k, v in sorted(shas.items())).encode()).hexdigest(),
            "fragmentos_ids": [f.fragmento_id for f in frags],
        }

    # ------------------------------------------------------------------ consulta
    def buscar(self, pregunta: str) -> list[dict]:
        """`buscar_fragmentos` real del backend (mismas reglas: solo lectura, timeout, top-5). Con cache por pregunta."""
        if pregunta in self.cache:
            return self.cache[pregunta]
        from services.orquestador import rag
        from sqlalchemy import text
        try:
            self.sesion.execute(text("SET TRANSACTION READ ONLY"))
            r = rag.buscar_fragmentos(self.sesion, pregunta)
        finally:
            self.sesion.rollback()
        self.cache[pregunta] = r
        return r
