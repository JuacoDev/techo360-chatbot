-- Verificacion POSTERIOR a la migracion 0003 (solo SELECT).

-- 1) Columna: uuid, NOT NULL, default gen_random_uuid(). ESPERADO: 1 fila.
SELECT column_name, data_type, is_nullable, column_default
  FROM information_schema.columns
 WHERE table_schema = 'public' AND table_name = 'conversaciones' AND column_name = 'public_id';

-- 2) Todas las filas con UUID y sin repetidos. ESPERADO: sin_valor = 0, repetidos = 0,
--    total = el de verificar_0003_antes.sql (no se pierde ni se crea ninguna fila).
SELECT count(*) AS total,
       count(*) FILTER (WHERE public_id IS NULL) AS sin_valor,
       count(*) - count(DISTINCT public_id) AS repetidos
  FROM conversaciones;

-- 3) Indice unico. ESPERADO: 1 fila (uq_conversaciones_public_id).
SELECT indexname, indexdef FROM pg_indexes
 WHERE schemaname = 'public' AND tablename = 'conversaciones' AND indexname = 'uq_conversaciones_public_id';

-- 4) Los mensajes siguen enlazados igual (mismo total que antes).
SELECT count(*) AS mensajes FROM mensajes;
