-- ============================================================
-- Reversa de la migracion 0004 (metadatos de generacion en mensajes)
-- ============================================================
-- Los datos de estas columnas SE PIERDEN: respaldar antes si ya se escribieron metadatos.
-- Primero las restricciones; despues las columnas, en orden inverso. Idempotente.
-- Si un backend ya mapea estas columnas, revertirlo (o apagar su interruptor) ANTES.
-- ============================================================

BEGIN;

SET LOCAL lock_timeout = '3s';

ALTER TABLE mensajes DROP CONSTRAINT IF EXISTS mensajes_validacion_cifras_estado_check;
ALTER TABLE mensajes DROP CONSTRAINT IF EXISTS mensajes_contexto_tamano_check;
ALTER TABLE mensajes DROP CONSTRAINT IF EXISTS mensajes_regeneraciones_check;

ALTER TABLE mensajes DROP COLUMN IF EXISTS grafica;
ALTER TABLE mensajes DROP COLUMN IF EXISTS regeneraciones;
ALTER TABLE mensajes DROP COLUMN IF EXISTS validacion_cifras;
ALTER TABLE mensajes DROP COLUMN IF EXISTS contexto;
ALTER TABLE mensajes DROP COLUMN IF EXISTS contexto_ids;
ALTER TABLE mensajes DROP COLUMN IF EXISTS duracion_ms;
ALTER TABLE mensajes DROP COLUMN IF EXISTS tokens_respuesta;
ALTER TABLE mensajes DROP COLUMN IF EXISTS tokens_prompt;
ALTER TABLE mensajes DROP COLUMN IF EXISTS done_reason;
ALTER TABLE mensajes DROP COLUMN IF EXISTS version_prompt;
ALTER TABLE mensajes DROP COLUMN IF EXISTS modelo_digest;
ALTER TABLE mensajes DROP COLUMN IF EXISTS modelo;
ALTER TABLE mensajes DROP COLUMN IF EXISTS version_contrato;

COMMIT;
