-- Verificacion PREVIA a la migracion 0003 (solo SELECT; usar sesion de solo lectura:
-- SET default_transaction_read_only = on; SHOW default_transaction_read_only;).

-- 1) Version: >= 13 (gen_random_uuid nativo). ESPERADO: PostgreSQL 16.x.
SELECT version();

-- 2) La columna todavia NO existe (0 filas) -- si aparece, la migracion solo completara lo que falte.
SELECT column_name, data_type, is_nullable, column_default
  FROM information_schema.columns
 WHERE table_schema = 'public' AND table_name = 'conversaciones' AND column_name = 'public_id';

-- 3) Filas a las que se les asignara UUID (ESPERADO 2026-10-09: 9 conversaciones, max id 40).
SELECT count(*) AS conversaciones, max(id) AS max_id FROM conversaciones;

-- 4) Transacciones abiertas que tocan conversaciones (deben ser 0 para no esperar el bloqueo).
SELECT pid, state, xact_start, left(query, 80) AS consulta
  FROM pg_stat_activity
 WHERE datname = current_database() AND xact_start IS NOT NULL AND pid <> pg_backend_pid();
