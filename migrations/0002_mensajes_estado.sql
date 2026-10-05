-- ============================================================
-- Migracion 0002 -- estados de los mensajes del chatbot (Fase C)
-- ============================================================
-- Destino: postgres-vector (DATABASE_VECTOR_URL), tabla public.mensajes.
-- Aplicar SOLO con el "autorizo" explicito del responsable y una copia de seguridad
-- previa (scripts/backup-db.sh). Ver COMANDOS_VPS.md (en techo360-fase-c, fuera de
-- los repos) para el procedimiento exacto.
--
-- Sigue el patron de 0001_conversaciones_mensajes.sql: idempotente (se puede
-- re-ejecutar) y en una sola transaccion (si algo falla, no queda nada a medias).
--
-- Que hace:
--   1. Columnas nuevas en mensajes (todas con valor por defecto: el backend ANTERIOR,
--      que no las conoce, sigue funcionando sin cambios):
--        estado          'pendiente' | 'procesando' | 'error' | 'respondido' | 'cancelado'
--                        (por defecto 'respondido')
--        error_detalle   motivo legible cuando estado = 'error' (max. 1000 caracteres)
--        actualizado_en  ultimo cambio de estado (para detectar 'procesando' colgados)
--        intentos        numero de veces que el mensaje paso a 'procesando'. Identifica
--                        QUE intento esta esperando al asistente: un RPC viejo (cancelado)
--                        que sigue vivo no puede cerrar ni marcar error el intento nuevo.
--   2. Backfill (SOLO la primera vez que se aplica): los 6 mensajes de usuario que hoy no
--      tienen respuesta (ids 26, 45, 48, 55, 56, 57; verificado contra produccion en solo
--      lectura el 2026-10-04) pasan a 'error'. El resto queda 'respondido' (por defecto).
--      Si se vuelve a ejecutar mas adelante NO toca nada: no volvera a marcar como error
--      mensajes que ya se reintentaron y respondieron.
--   3. Restricciones:
--        - estado solo admite los 5 valores.
--        - un mensaje del asistente SIEMPRE es 'respondido'.
--        - error_detalle de a lo sumo 1000 caracteres.
--        - INDICE UNICO PARCIAL: como maximo UN mensaje de usuario sin resolver
--          ('pendiente', 'procesando', 'error', 'cancelado') por conversacion. Es la
--          garantia, a nivel de BD y a prueba de carreras, de que no puede haber dos
--          pendientes en la misma conversacion.
--   4. Indice auxiliar para el barrido de 'pendiente'/'procesando' colgados.
--
-- Bloqueos: el primer ALTER TABLE pide ACCESS EXCLUSIVE sobre mensajes. Con ~44 filas
-- tarda milisegundos, PERO si hay una transaccion abierta sobre mensajes (por ejemplo
-- un chat esperando al asistente), el ALTER espera y encola todas las consultas nuevas
-- a la tabla. Por eso la migracion fija lock_timeout = 3 s: si no consigue el bloqueo,
-- ABORTA sin cambiar nada y se reintenta (ver COMANDOS_VPS.md: antes de aplicarla se
-- comprueba que no haya transacciones abiertas sobre mensajes).
-- ADD COLUMN con DEFAULT constante o now() (STABLE) no reescribe la tabla en PG >= 11
-- (produccion usa pgvector/pgvector:pg16).
-- ============================================================

BEGIN;

SET LOCAL lock_timeout = '3s';

DO $$
BEGIN
    IF to_regclass('public.mensajes') IS NULL THEN
        RAISE EXCEPTION 'No existe public.mensajes: esta no es la base postgres-vector';
    END IF;
END
$$;

-- Recordar, ANTES de agregar las columnas, si es la primera vez (decide el backfill).
SELECT set_config(
    'techo360.m0002_primera_vez',
    (NOT EXISTS (
        SELECT 1 FROM information_schema.columns
         WHERE table_schema = 'public' AND table_name = 'mensajes' AND column_name = 'estado'
    ))::text,
    true
);

ALTER TABLE mensajes ADD COLUMN IF NOT EXISTS estado TEXT NOT NULL DEFAULT 'respondido';
ALTER TABLE mensajes ADD COLUMN IF NOT EXISTS error_detalle TEXT;
ALTER TABLE mensajes ADD COLUMN IF NOT EXISTS actualizado_en TIMESTAMPTZ NOT NULL DEFAULT now();
ALTER TABLE mensajes ADD COLUMN IF NOT EXISTS intentos INTEGER NOT NULL DEFAULT 0;

-- Backfill de los 6 mensajes de usuario sin respuesta: SOLO la primera vez.
DO $$
DECLARE
    n integer;
BEGIN
    IF current_setting('techo360.m0002_primera_vez') = 'true' THEN
        UPDATE mensajes
           SET estado = 'error',
               error_detalle = 'Sin respuesta registrada (anterior a los estados)',
               actualizado_en = now()
         WHERE id IN (26, 45, 48, 55, 56, 57)
           AND rol = 'usuario'
           AND estado = 'respondido';

        SELECT count(*) INTO n
          FROM mensajes
         WHERE id IN (26, 45, 48, 55, 56, 57) AND rol = 'usuario' AND estado = 'error';
        IF n <> 6 THEN
            RAISE EXCEPTION 'Backfill inesperado: % de 6 mensajes quedaron en error; se aborta sin cambios', n;
        END IF;
    END IF;
END
$$;

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'mensajes_estado_check') THEN
        ALTER TABLE mensajes ADD CONSTRAINT mensajes_estado_check
            CHECK (estado IN ('pendiente', 'procesando', 'error', 'respondido', 'cancelado'));
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'mensajes_estado_rol_check') THEN
        ALTER TABLE mensajes ADD CONSTRAINT mensajes_estado_rol_check
            CHECK (rol = 'usuario' OR estado = 'respondido');
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'mensajes_error_detalle_largo_check') THEN
        ALTER TABLE mensajes ADD CONSTRAINT mensajes_error_detalle_largo_check
            CHECK (error_detalle IS NULL OR char_length(error_detalle) <= 1000);
    END IF;
END
$$;

CREATE UNIQUE INDEX IF NOT EXISTS uq_mensajes_un_sin_resolver_por_conversacion
    ON mensajes (conversacion_id)
 WHERE rol = 'usuario' AND estado IN ('pendiente', 'procesando', 'error', 'cancelado');

CREATE INDEX IF NOT EXISTS idx_mensajes_estado_actualizado
    ON mensajes (estado, actualizado_en)
 WHERE estado IN ('pendiente', 'procesando');

COMMIT;
