-- Verificacion PREVIA a la migracion 0005 (solo SELECT; no usa objetos nuevos).
-- No imprime texto de mensajes: solo conteos, checksums e indicadores.

-- 1) Totales y checksum de lo que 0005 NO debe tocar (conversaciones y mensajes).
--    Guardar estas cifras: verificar_0005_despues.sql debe devolver EXACTAMENTE las mismas.
SELECT (SELECT count(*) FROM conversaciones) AS conversaciones,
       (SELECT md5(coalesce(string_agg(concat_ws('|', id, usuario_id, consentimiento_entrenamiento, fecha), E'\n' ORDER BY id), ''))
          FROM conversaciones) AS checksum_conversaciones,
       count(*) AS mensajes,
       md5(coalesce(string_agg(concat_ws('|', id, conversacion_id, rol, contenido, estado, intentos), E'\n' ORDER BY id), '')) AS checksum_mensajes
  FROM mensajes;

-- 2) Objetos que 0005 crea: aun NO deben existir. ESPERADO: 0 filas.
SELECT c.relname FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace
 WHERE n.nspname = 'public' AND c.relname IN ('rag_documentos', 'rag_fragmentos', 'idx_rag_fragmentos_embedding_hnsw');

-- 3) Extension pgvector: si ya esta instalada, 0005 no la toca. Anotar el resultado.
SELECT extname, extversion FROM pg_extension WHERE extname = 'vector';
SELECT name, default_version, installed_version FROM pg_available_extensions WHERE name = 'vector';

-- 4) Transacciones abiertas que podrian demorar a 0005 (lo ideal: 0 filas). Sin texto de consultas.
SELECT pid, state, now() - xact_start AS transaccion_abierta_hace
  FROM pg_stat_activity
 WHERE datname = current_database() AND pid <> pg_backend_pid()
   AND state IN ('idle in transaction', 'active') AND xact_start IS NOT NULL
 ORDER BY xact_start;
