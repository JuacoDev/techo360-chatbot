-- Verificacion PREVIA a la migracion 0004 (solo SELECT; no usa las columnas nuevas).
-- No imprime texto de mensajes: solo conteos, checksums e indicadores.

-- 1) Totales y checksum de las columnas EXISTENTES (id, conversacion_id, rol, contenido, estado, intentos).
--    Guardar estas cifras: verificar_0004_despues.sql debe devolver EXACTAMENTE las mismas.
SELECT (SELECT count(*) FROM conversaciones) AS conversaciones,
       count(*) AS mensajes,
       count(*) FILTER (WHERE rol = 'usuario') AS de_usuario,
       count(*) FILTER (WHERE rol = 'asistente') AS del_asistente,
       md5(coalesce(string_agg(concat_ws('|', id, conversacion_id, rol, contenido, estado, intentos), E'\n' ORDER BY id), '')) AS checksum
  FROM mensajes;

-- 2) Columnas actuales de mensajes (lista, sin datos).
SELECT column_name, data_type, is_nullable
  FROM information_schema.columns
 WHERE table_schema = 'public' AND table_name = 'mensajes'
 ORDER BY ordinal_position;

-- 3) La migracion aun NO esta aplicada: debe devolver 0 filas.
SELECT column_name FROM information_schema.columns
 WHERE table_schema = 'public' AND table_name = 'mensajes'
   AND column_name IN ('version_contrato', 'modelo', 'modelo_digest', 'version_prompt', 'done_reason',
                       'tokens_prompt', 'tokens_respuesta', 'duracion_ms', 'contexto_ids', 'contexto',
                       'validacion_cifras', 'regeneraciones', 'grafica');

-- 4) Transacciones abiertas que podrian bloquear el ALTER TABLE: lo ideal es 0 filas.
--    No se muestra el texto de la consulta (podria contener mensajes de usuarios).
SELECT pid, state, now() - xact_start AS transaccion_abierta_hace,
       (query ILIKE '%mensajes%') AS menciona_mensajes
  FROM pg_stat_activity
 WHERE datname = current_database()
   AND pid <> pg_backend_pid()
   AND state IN ('idle in transaction', 'active')
   AND xact_start IS NOT NULL
 ORDER BY xact_start;
