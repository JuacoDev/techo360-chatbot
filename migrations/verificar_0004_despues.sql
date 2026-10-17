-- Verificacion POSTERIOR a la migracion 0004 (solo SELECT).
-- No imprime texto de mensajes: solo conteos, checksums e indicadores.

-- 1) Mismas cifras que verificar_0004_antes.sql. ESPERADO: IDENTICAS (filas y checksum).
SELECT (SELECT count(*) FROM conversaciones) AS conversaciones,
       count(*) AS mensajes,
       count(*) FILTER (WHERE rol = 'usuario') AS de_usuario,
       count(*) FILTER (WHERE rol = 'asistente') AS del_asistente,
       md5(coalesce(string_agg(concat_ws('|', id, conversacion_id, rol, contenido, estado, intentos), E'\n' ORDER BY id), '')) AS checksum
  FROM mensajes;

-- 2) Las 13 columnas nuevas. ESPERADO: 13 filas.
SELECT column_name, data_type, is_nullable, column_default
  FROM information_schema.columns
 WHERE table_schema = 'public' AND table_name = 'mensajes'
   AND column_name IN ('version_contrato', 'modelo', 'modelo_digest', 'version_prompt', 'done_reason',
                       'tokens_prompt', 'tokens_respuesta', 'duracion_ms', 'contexto_ids', 'contexto',
                       'validacion_cifras', 'regeneraciones', 'grafica')
 ORDER BY column_name;

-- 3) Las filas existentes quedan con NULL en las 12 columnas nulables y regeneraciones = 0.
--    ESPERADO: todas las cuentas *_no_nulos = 0 y regeneraciones_distintas_de_0 = 0.
SELECT count(*) AS mensajes,
       count(version_contrato) AS version_contrato_no_nulos,
       count(modelo) AS modelo_no_nulos,
       count(modelo_digest) AS modelo_digest_no_nulos,
       count(version_prompt) AS version_prompt_no_nulos,
       count(done_reason) AS done_reason_no_nulos,
       count(tokens_prompt) AS tokens_prompt_no_nulos,
       count(tokens_respuesta) AS tokens_respuesta_no_nulos,
       count(duracion_ms) AS duracion_ms_no_nulos,
       count(contexto_ids) AS contexto_ids_no_nulos,
       count(contexto) AS contexto_no_nulos,
       count(validacion_cifras) AS validacion_cifras_no_nulos,
       count(grafica) AS grafica_no_nulos,
       count(*) FILTER (WHERE regeneraciones <> 0) AS regeneraciones_distintas_de_0
  FROM mensajes;

-- 4) Restricciones. ESPERADO: 3 filas.
SELECT conname FROM pg_constraint
 WHERE conrelid = 'public.mensajes'::regclass
   AND conname IN ('mensajes_regeneraciones_check', 'mensajes_contexto_tamano_check', 'mensajes_validacion_cifras_estado_check')
 ORDER BY conname;
