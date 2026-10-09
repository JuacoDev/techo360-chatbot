-- ============================================================
-- Migracion 0003 -- identificador publico opaco de conversaciones
-- ============================================================
-- Destino: postgres-vector (DATABASE_VECTOR_URL), tabla public.conversaciones.
-- Aplicar SOLO con el "autorizo" explicito del responsable y una copia de seguridad
-- previa verificada (fuera de la rotacion, `gzip -t` y sha256 anotado). Probar antes
-- con scripts/migracion_0003.sh --dry-run (ejecuta todo y hace ROLLBACK).
--
-- Sigue el patron de 0001/0002: idempotente (se puede re-ejecutar) y en una sola
-- transaccion (si algo falla, no queda nada a medias).
--
-- Por que: el id de conversaciones es BIGSERIAL (entero secuencial) y viaja en la URL
-- de la API (/chatbot/conversaciones/{id}/...): es facil de enumerar. public_id es un
-- UUID v4 aleatorio que la API expone y acepta en su lugar. La autorizacion sigue
-- siendo el filtro por usuario_id del backend; public_id solo evita la enumeracion.
--
-- Patron "expandir y luego contraer" (compatible hacia atras):
--   EXPANDIR (esta migracion): columna nueva con valor por defecto. El backend ANTERIOR
--     no la conoce y sigue funcionando; las filas nuevas reciben su UUID de la BD.
--   CONTRAER (fase posterior, NO aqui): cuando todos los clientes usen public_id, la API
--     deja de aceptar y devolver el id entero. El id interno (PK y FK de mensajes) se
--     queda: solo deja de ser publico. Ver docs de la PR.
--
-- Requisitos: PostgreSQL >= 13 (gen_random_uuid() es nativo, sin pgcrypto). Produccion:
-- PostgreSQL 16.14 (pgvector/pgvector:pg16), comprobado en solo lectura el 2026-10-09.
--
-- Bloqueos: ADD COLUMN con un DEFAULT volatil (gen_random_uuid) REESCRIBE la tabla bajo
-- ACCESS EXCLUSIVE. Con 9 filas (2026-10-09) son milisegundos, PERO si hay una
-- transaccion abierta sobre conversaciones el ALTER espera y encola las consultas
-- nuevas: por eso lock_timeout = 3 s (si no consigue el bloqueo, ABORTA sin cambios y se
-- reintenta). CREATE UNIQUE INDEX (no CONCURRENTLY: va dentro de la transaccion; con
-- pocas filas es inmediato).
-- ============================================================

BEGIN;

SET LOCAL lock_timeout = '3s';

DO $$
BEGIN
    IF to_regclass('public.conversaciones') IS NULL THEN
        RAISE EXCEPTION 'No existe public.conversaciones: esta no es la base postgres-vector';
    END IF;
END
$$;

-- 1) Columna nueva. En la primera ejecucion llena TODAS las filas existentes.
ALTER TABLE conversaciones ADD COLUMN IF NOT EXISTS public_id UUID NOT NULL DEFAULT gen_random_uuid();

-- 2) Idempotencia ante un estado parcial (columna creada a mano sin default o con
--    nulos): no hace nada si la 1) ya la dejo bien.
ALTER TABLE conversaciones ALTER COLUMN public_id SET DEFAULT gen_random_uuid();
UPDATE conversaciones SET public_id = gen_random_uuid() WHERE public_id IS NULL;
ALTER TABLE conversaciones ALTER COLUMN public_id SET NOT NULL;

-- 3) Unicidad (un UUID v4 repetido es practicamente imposible; el indice lo garantiza
--    y ademas es el que usa la busqueda por public_id).
CREATE UNIQUE INDEX IF NOT EXISTS uq_conversaciones_public_id ON conversaciones (public_id);

-- 4) Comprobacion final dentro de la transaccion: si algo no cuadra, ABORTA.
DO $$
DECLARE
    sin_valor integer;
    repetidos integer;
BEGIN
    SELECT count(*) INTO sin_valor FROM conversaciones WHERE public_id IS NULL;
    SELECT count(*) - count(DISTINCT public_id) INTO repetidos FROM conversaciones;
    IF sin_valor <> 0 OR repetidos <> 0 THEN
        RAISE EXCEPTION 'public_id inconsistente: % sin valor, % repetidos; se aborta sin cambios', sin_valor, repetidos;
    END IF;
END
$$;

COMMIT;
