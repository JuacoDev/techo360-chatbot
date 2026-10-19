-- Verificacion POSTERIOR a la migracion 0005 (solo SELECT).
-- No imprime texto de mensajes ni de fragmentos: solo conteos, checksums e indicadores.

-- 1) Mismas cifras que verificar_0005_antes.sql. ESPERADO: IDENTICAS (filas y checksums).
SELECT (SELECT count(*) FROM conversaciones) AS conversaciones,
       (SELECT md5(coalesce(string_agg(concat_ws('|', id, usuario_id, consentimiento_entrenamiento, fecha), E'\n' ORDER BY id), ''))
          FROM conversaciones) AS checksum_conversaciones,
       count(*) AS mensajes,
       md5(coalesce(string_agg(concat_ws('|', id, conversacion_id, rol, contenido, estado, intentos), E'\n' ORDER BY id), '')) AS checksum_mensajes
  FROM mensajes;

-- 2) Tablas e indice nuevos. ESPERADO: 3 filas.
SELECT c.relname, c.relkind FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace
 WHERE n.nspname = 'public' AND c.relname IN ('rag_documentos', 'rag_fragmentos', 'idx_rag_fragmentos_embedding_hnsw')
 ORDER BY c.relname;

-- 3) Tipo del embedding y extension. ESPERADO: vector(384) y la extension instalada.
SELECT format_type(atttypid, atttypmod) AS embedding_tipo FROM pg_attribute
 WHERE attrelid = 'public.rag_fragmentos'::regclass AND attname = 'embedding';
SELECT extname, extversion FROM pg_extension WHERE extname = 'vector';

-- 4) Tablas vacias antes de cargar el corpus (la carga es 6.8). ESPERADO: 0 y 0.
SELECT (SELECT count(*) FROM rag_documentos) AS documentos, (SELECT count(*) FROM rag_fragmentos) AS fragmentos;

-- 5) Restricciones. ESPERADO: rag_documentos_vigencia_check, rag_fragmentos_documento_fragmento_uq,
--    rag_fragmentos_tokens_check (ademas de las pk, fk y unique).
SELECT conrelid::regclass AS tabla, conname FROM pg_constraint
 WHERE conrelid IN ('public.rag_documentos'::regclass, 'public.rag_fragmentos'::regclass) ORDER BY 1, 2;
