-- Verificacion PREVIA a la migracion 0002 (solo SELECT; no usa las columnas nuevas).

-- 1) Mensajes de usuario sin respuesta inmediata. Deben ser EXACTAMENTE 6:
--    ids 26, 45, 48, 55, 56, 57 (una fila por cada uno, en conversaciones 14, 17, 18, 20, 21, 22).
WITH ordenados AS (
    SELECT id, conversacion_id, rol, left(contenido, 50) AS inicio, fecha,
           lead(rol) OVER (PARTITION BY conversacion_id ORDER BY fecha, id) AS siguiente
      FROM mensajes
)
SELECT id, conversacion_id, inicio, fecha
  FROM ordenados
 WHERE rol = 'usuario' AND (siguiente IS NULL OR siguiente = 'usuario')
 ORDER BY id;

-- 2) Totales. Esperado hoy: 13 conversaciones, 44 mensajes (25 de usuario, 19 del asistente).
SELECT (SELECT count(*) FROM conversaciones) AS conversaciones,
       count(*) AS mensajes,
       count(*) FILTER (WHERE rol = 'usuario') AS de_usuario,
       count(*) FILTER (WHERE rol = 'asistente') AS del_asistente
  FROM mensajes;

-- 3) La migracion aun NO esta aplicada: debe devolver 0 filas.
SELECT column_name FROM information_schema.columns
 WHERE table_schema = 'public' AND table_name = 'mensajes'
   AND column_name IN ('estado', 'error_detalle', 'actualizado_en', 'intentos');

-- 4) Transacciones abiertas o sesiones que podrian bloquear el ALTER TABLE: lo ideal es
--    0 filas (si hay alguna "idle in transaction" sobre mensajes, esperar o reintentar;
--    la migracion tiene lock_timeout de 3 s y aborta sin cambiar nada si no obtiene el bloqueo).
SELECT pid, state, now() - xact_start AS transaccion_abierta_hace, left(query, 80) AS consulta
  FROM pg_stat_activity
 WHERE datname = current_database()
   AND pid <> pg_backend_pid()
   AND state IN ('idle in transaction', 'active')
   AND xact_start IS NOT NULL
 ORDER BY xact_start;
