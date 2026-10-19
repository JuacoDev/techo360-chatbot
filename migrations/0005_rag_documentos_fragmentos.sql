-- ============================================================
-- Migracion 0005 -- tablas del RAG curado (Fase 6, paso 6.3)
-- ============================================================
-- Destino: postgres-vector (DATABASE_VECTOR_URL), esquema public.
-- Especificacion: claude/fase2-7-migraciones.md, seccion 3 (con los ajustes de abajo).
-- NO SE APLICA EN PRODUCCION hasta el paso 6.8 [AUT]: requiere autorizacion explicita, respaldo
-- previo de postgres-vector fuera de la rotacion y verificar_0005_antes.sql guardado.
-- Procedimiento igual al de 0002-0004: psql -v ON_ERROR_STOP=1 (sin -1: el archivo trae su
-- BEGIN/COMMIT), dentro del contenedor de la base; ver scripts/migracion_0005.sh.
--
-- Que hace (todo ADITIVO: no toca conversaciones, mensajes ni ningun dato existente):
--   1. Asegura la extension pgvector (CREATE EXTENSION IF NOT EXISTS vector): la imagen es
--      pgvector/pgvector:pg16 y su init ya la crea en un volumen nuevo; si ya existe, no hace nada.
--   2. rag_documentos: un registro por documento del corpus aprobado (archivo de rag/corpus/).
--   3. rag_fragmentos: un registro por fragmento, con su texto, su embedding vector(384)
--      (modelo multilingual-e5-small, medido en 6.2) y los metadatos de fuente y vigencia
--      que el plan exige (fuente, ruta, fecha, vigencia, version, tema).
--   4. Un indice HNSW (coseno) sobre el embedding. Justificacion de tamano: el corpus aprobado
--      tiene decenas de fragmentos (45 en la primera ingesta); a esa escala el planificador usa
--      un barrido exacto y el indice NO cambia los resultados. Se crea para no tener que
--      reindexar si el corpus crece a cientos de fragmentos. IVFFlat se descarta: necesita
--      datos para entrenar sus listas y con tan pocas filas pierde recall.
--
-- Ajustes respecto de la especificacion de 2.7 (todos aditivos, para poder registrar la
-- procedencia POR FRAGMENTO, que es lo que pide el plan 6.2):
--   * rag_documentos agrega `nombre` UNIQUE (el archivo del corpus) para que la ingesta sea
--     idempotente; `sha256` sigue UNIQUE pero se ACTUALIZA si el archivo cambia.
--   * rag_fragmentos agrega `fragmento_id` (id estable dentro del documento) con
--     UNIQUE (documento_id, fragmento_id) en lugar de UNIQUE (documento_id, orden); `orden` queda
--     como posicion de lectura. Agrega fuente/ruta/fecha_fuente/vigencia/version_fuente/tema,
--     `sha256` por fragmento (hash del texto embebido + modelo + metadatos), y `activo`
--     (un fragmento que sale del corpus se DESACTIVA, no se borra).
--   * `aprobado_por` / `aprobado_en` quedan NULL hasta que el responsable apruebe el contenido
--     extraido; la recuperacion debe filtrar por activo y por vigencia.
--
-- Sin datos personales y sin cifras por municipio (regla del plan: los datos numericos van por SQL).
-- Bloqueos: solo CREATE TABLE/INDEX sobre tablas nuevas; no toma bloqueos sobre tablas existentes.
-- ============================================================

BEGIN;

SET LOCAL lock_timeout = '3s';

DO $$
BEGIN
    IF to_regclass('public.mensajes') IS NULL OR to_regclass('public.conversaciones') IS NULL THEN
        RAISE EXCEPTION 'No existen public.conversaciones/mensajes: esta no es la base postgres-vector';
    END IF;
END
$$;

CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS rag_documentos (
    id             BIGSERIAL PRIMARY KEY,
    nombre         TEXT NOT NULL UNIQUE,
    titulo         TEXT NOT NULL,
    fuente         TEXT,
    tipo_fuente    TEXT,
    fecha_fuente   DATE,
    vigente_desde  DATE,
    vigente_hasta  DATE,
    version        TEXT,
    sha256         TEXT NOT NULL UNIQUE,
    aprobado_por   TEXT,
    aprobado_en    TIMESTAMPTZ,
    activo         BOOLEAN NOT NULL DEFAULT true,
    creado_en      TIMESTAMPTZ NOT NULL DEFAULT now(),
    actualizado_en TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT rag_documentos_vigencia_check
        CHECK (vigente_hasta IS NULL OR vigente_desde IS NULL OR vigente_hasta >= vigente_desde)
);

CREATE TABLE IF NOT EXISTS rag_fragmentos (
    id               BIGSERIAL PRIMARY KEY,
    documento_id     BIGINT NOT NULL REFERENCES rag_documentos (id) ON DELETE CASCADE,
    fragmento_id     TEXT NOT NULL,
    orden            INTEGER NOT NULL,
    texto            TEXT NOT NULL,
    tokens           INTEGER,
    fuente           TEXT NOT NULL,
    ruta             TEXT NOT NULL,
    fecha_fuente     DATE,
    vigencia         TEXT,
    version_fuente   TEXT,
    tema             TEXT,
    sha256           TEXT NOT NULL,
    embedding        vector(384) NOT NULL,
    modelo_embedding TEXT NOT NULL,
    activo           BOOLEAN NOT NULL DEFAULT true,
    creado_en        TIMESTAMPTZ NOT NULL DEFAULT now(),
    actualizado_en   TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT rag_fragmentos_documento_fragmento_uq UNIQUE (documento_id, fragmento_id),
    CONSTRAINT rag_fragmentos_tokens_check CHECK (tokens IS NULL OR tokens > 0)
);

CREATE INDEX IF NOT EXISTS idx_rag_fragmentos_documento_id ON rag_fragmentos (documento_id);
CREATE INDEX IF NOT EXISTS idx_rag_fragmentos_embedding_hnsw
    ON rag_fragmentos USING hnsw (embedding vector_cosine_ops) WITH (m = 16, ef_construction = 64);

-- Comprobacion final: si algo no quedo como se espera, ROLLBACK de toda la migracion.
DO $$
BEGIN
    IF to_regclass('public.rag_documentos') IS NULL OR to_regclass('public.rag_fragmentos') IS NULL THEN
        RAISE EXCEPTION '0005: faltan las tablas rag_*';
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'vector') THEN
        RAISE EXCEPTION '0005: la extension vector no esta instalada';
    END IF;
    IF (SELECT format_type(atttypid, atttypmod) FROM pg_attribute
         WHERE attrelid = 'public.rag_fragmentos'::regclass AND attname = 'embedding') <> 'vector(384)' THEN
        RAISE EXCEPTION '0005: embedding no es vector(384)';
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_indexes WHERE schemaname = 'public' AND indexname = 'idx_rag_fragmentos_embedding_hnsw') THEN
        RAISE EXCEPTION '0005: falta el indice HNSW';
    END IF;
END
$$;

COMMIT;
