-- Verificacion POSTERIOR a la migracion 0002 (solo SELECT).

-- 1) Reparto por estado. ESPERADO hoy (44 mensajes):
--      error       | usuario   | 6
--      respondido  | asistente | 19
--      respondido  | usuario   | 19      => 38 respondido + 6 error
SELECT estado, rol, count(*) FROM mensajes GROUP BY estado, rol ORDER BY estado, rol;

-- 2) Los 6 en error: ids 26, 45, 48, 55, 56, 57 con 'Sin respuesta registrada (anterior a los estados)'.
SELECT id, conversacion_id, estado, error_detalle, intentos FROM mensajes WHERE estado <> 'respondido' ORDER BY id;

-- 3) Columnas nuevas (4 filas: actualizado_en, error_detalle, estado, intentos).
SELECT column_name, data_type, is_nullable, column_default
  FROM information_schema.columns
 WHERE table_schema = 'public' AND table_name = 'mensajes'
   AND column_name IN ('estado', 'error_detalle', 'actualizado_en', 'intentos')
 ORDER BY column_name;

-- 4) Restricciones nuevas (3 filas): mensajes_error_detalle_largo_check, mensajes_estado_check, mensajes_estado_rol_check.
SELECT conname, pg_get_constraintdef(oid) FROM pg_constraint
 WHERE conrelid = 'public.mensajes'::regclass
   AND conname IN ('mensajes_estado_check', 'mensajes_estado_rol_check', 'mensajes_error_detalle_largo_check')
 ORDER BY conname;

-- 5) Indices nuevos (2 filas): uq_mensajes_un_sin_resolver_por_conversacion (UNIQUE) e idx_mensajes_estado_actualizado.
SELECT indexname FROM pg_indexes
 WHERE schemaname = 'public' AND tablename = 'mensajes'
   AND indexname IN ('uq_mensajes_un_sin_resolver_por_conversacion', 'idx_mensajes_estado_actualizado') ORDER BY indexname;

-- 6) Ninguna conversacion con mas de un mensaje sin resolver: debe devolver 0 filas.
SELECT conversacion_id, count(*) FROM mensajes
 WHERE rol = 'usuario' AND estado IN ('pendiente', 'procesando', 'error', 'cancelado')
 GROUP BY conversacion_id HAVING count(*) > 1;

-- 7) Total intacto: 44 mensajes.
SELECT count(*) AS mensajes FROM mensajes;
