-- ============================================================
-- Reversa de la migracion 0002 (estados de mensajes)
-- ============================================================
-- Quita indices, restricciones y las 4 columnas nuevas (estado, error_detalle,
-- actualizado_en, intentos). Los DATOS de mensajes (44 filas hoy) NO se tocan; solo se
-- pierde la informacion de estado: los 6 mensajes sin respuesta vuelven a ser
-- indistinguibles, como antes de 0002.
-- Idempotente. Ejecutar solo si hay que deshacer la fase C; ANTES, apagar el interruptor
-- CHATBOT_BLOQUEO_PENDIENTES y revertir backend y frontend: el backend nuevo consulta
-- estas columnas y dejaria de funcionar sin ellas.
-- Mismo lock_timeout que la migracion: si hay transacciones abiertas sobre mensajes,
-- aborta sin cambiar nada y se reintenta.
-- ============================================================

BEGIN;

SET LOCAL lock_timeout = '3s';

DROP INDEX IF EXISTS idx_mensajes_estado_actualizado;
DROP INDEX IF EXISTS uq_mensajes_un_sin_resolver_por_conversacion;

ALTER TABLE mensajes DROP CONSTRAINT IF EXISTS mensajes_error_detalle_largo_check;
ALTER TABLE mensajes DROP CONSTRAINT IF EXISTS mensajes_estado_rol_check;
ALTER TABLE mensajes DROP CONSTRAINT IF EXISTS mensajes_estado_check;

ALTER TABLE mensajes DROP COLUMN IF EXISTS intentos;
ALTER TABLE mensajes DROP COLUMN IF EXISTS actualizado_en;
ALTER TABLE mensajes DROP COLUMN IF EXISTS error_detalle;
ALTER TABLE mensajes DROP COLUMN IF EXISTS estado;

COMMIT;
