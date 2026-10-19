-- ============================================================
-- Reversa de la migracion 0005 (tablas del RAG curado)
-- ============================================================
-- Los datos de rag_documentos / rag_fragmentos SE PIERDEN (la ingesta los regenera desde
-- rag/corpus/; respaldar igual antes si ya se cargaron). NO se elimina la extension `vector`:
-- puede existir desde antes (la crea el init de la imagen) y otros objetos podrian usarla.
-- Idempotente. Si un backend ya consulta estas tablas, apagar primero esa funcion (paso 6.6).
-- ============================================================

BEGIN;

SET LOCAL lock_timeout = '3s';

DROP INDEX IF EXISTS idx_rag_fragmentos_embedding_hnsw;
DROP TABLE IF EXISTS rag_fragmentos;
DROP TABLE IF EXISTS rag_documentos;

COMMIT;
