-- ============================================================
-- Reversa de la migracion 0003 (public_id de conversaciones)
-- ============================================================
-- Quita el indice unico y la columna public_id. Los DATOS de conversaciones y mensajes
-- NO se tocan; solo se pierden los UUID: cualquier public_id que un cliente tenga
-- guardado (p. ej. el estado del historial del navegador en /techobot/chat) deja de
-- servir y el chat vuelve a la lista con un aviso.
-- ANTES de ejecutarla: revertir el backend que expone/acepta public_id (el modelo
-- Conversacion lo lee y dejaria de funcionar sin la columna). El frontend con
-- `public_id ?? id` no necesita revertirse: vuelve a usar el id entero solo.
-- Idempotente. Mismo lock_timeout que la migracion.
-- ============================================================

BEGIN;

SET LOCAL lock_timeout = '3s';

DROP INDEX IF EXISTS uq_conversaciones_public_id;
ALTER TABLE conversaciones DROP COLUMN IF EXISTS public_id;

COMMIT;
