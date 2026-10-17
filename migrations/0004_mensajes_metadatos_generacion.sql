-- ============================================================
-- Migracion 0004 -- metadatos de generacion en mensajes (Fase 2, paso 2.8)
-- ============================================================
-- Destino: postgres-vector (DATABASE_VECTOR_URL), tabla public.mensajes.
-- Especificacion: claude/fase2-7-migraciones.md, seccion 2.
-- Aplicar SOLO con autorizacion explicita del responsable y una copia de seguridad
-- previa. Procedimiento igual al de 0002: psql -v ON_ERROR_STOP=1 (sin -1: el archivo trae
-- su BEGIN/COMMIT), dentro del contenedor de la base.
--
-- Sigue el patron de 0002: idempotente (se puede re-ejecutar) y en una sola transaccion
-- (si algo falla, no queda nada a medias).
--
-- Que hace:
--   1. 13 columnas nuevas en mensajes, todas NULABLES salvo regeneraciones (NOT NULL con
--      valor constante 0). No reescribe la tabla (ADD COLUMN con default constante, PG >= 11)
--      ni cambia ningun dato: los mensajes existentes quedan con NULL (y regeneraciones = 0).
--        version_contrato   SMALLINT   1 o 2; NULL si no se conoce
--        modelo             TEXT       tag del modelo, p. ej. techo360-chatbot:v3.3
--        modelo_digest      TEXT       digest del modelo si Ollama lo devolvio
--        version_prompt     TEXT       id del system prompt, p. ej. sp-0.4.0-1
--        done_reason        TEXT       stop, length, etc.
--        tokens_prompt      INTEGER    prompt_eval_count
--        tokens_respuesta   INTEGER    eval_count
--        duracion_ms        INTEGER    duracion total de la generacion
--        contexto_ids       TEXT[]     ids de contexto entregados al modelo
--        contexto           JSONB      contexto en forma compacta (fase2-2 seccion 7)
--        validacion_cifras  JSONB      {"estado": ok|marcada|regenerada|abstencion, "no_validadas": [...]}
--        regeneraciones     SMALLINT   0 o 1 (se regenera una sola vez)
--        grafica            JSONB      {"spec": {...}, "valida": bool, "motivo": "..."}
--   2. Tres restricciones: regeneraciones entre 0 y 1; contexto de a lo sumo 64 KiB;
--      validacion_cifras, si existe, trae la clave "estado".
--   3. Sin indices nuevos (las consultas por estos campos son de analisis, no de la aplicacion).
--
-- Compatibilidad: aditiva. El backend/chatbot que no conoce las columnas sigue funcionando.
-- ORDEN OBLIGATORIO: aplicar 0004 ANTES de desplegar un backend cuyo modelo ORM las mapee.
--
-- Bloqueos: el primer ALTER TABLE pide ACCESS EXCLUSIVE sobre mensajes. Con pocas filas
-- tarda milisegundos, PERO si hay una transaccion abierta sobre mensajes el ALTER espera y
-- encola las consultas nuevas. Por eso fija lock_timeout = 3 s: si no consigue el bloqueo,
-- ABORTA sin cambiar nada y se reintenta (antes se comprueba que no haya transacciones largas).
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

ALTER TABLE mensajes ADD COLUMN IF NOT EXISTS version_contrato SMALLINT;
ALTER TABLE mensajes ADD COLUMN IF NOT EXISTS modelo TEXT;
ALTER TABLE mensajes ADD COLUMN IF NOT EXISTS modelo_digest TEXT;
ALTER TABLE mensajes ADD COLUMN IF NOT EXISTS version_prompt TEXT;
ALTER TABLE mensajes ADD COLUMN IF NOT EXISTS done_reason TEXT;
ALTER TABLE mensajes ADD COLUMN IF NOT EXISTS tokens_prompt INTEGER;
ALTER TABLE mensajes ADD COLUMN IF NOT EXISTS tokens_respuesta INTEGER;
ALTER TABLE mensajes ADD COLUMN IF NOT EXISTS duracion_ms INTEGER;
ALTER TABLE mensajes ADD COLUMN IF NOT EXISTS contexto_ids TEXT[];
ALTER TABLE mensajes ADD COLUMN IF NOT EXISTS contexto JSONB;
ALTER TABLE mensajes ADD COLUMN IF NOT EXISTS validacion_cifras JSONB;
ALTER TABLE mensajes ADD COLUMN IF NOT EXISTS regeneraciones SMALLINT NOT NULL DEFAULT 0;
ALTER TABLE mensajes ADD COLUMN IF NOT EXISTS grafica JSONB;

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'mensajes_regeneraciones_check') THEN
        ALTER TABLE mensajes ADD CONSTRAINT mensajes_regeneraciones_check
            CHECK (regeneraciones BETWEEN 0 AND 1);
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'mensajes_contexto_tamano_check') THEN
        ALTER TABLE mensajes ADD CONSTRAINT mensajes_contexto_tamano_check
            CHECK (contexto IS NULL OR pg_column_size(contexto) <= 65536);
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'mensajes_validacion_cifras_estado_check') THEN
        ALTER TABLE mensajes ADD CONSTRAINT mensajes_validacion_cifras_estado_check
            CHECK (validacion_cifras IS NULL OR validacion_cifras ? 'estado');
    END IF;
END
$$;

COMMIT;
