set -u
C=techo360-postgres-principal
run() {  # $1 = SQL (solo SELECT); psql por defecto del contenedor, sesion de solo lectura
  docker exec -e PGOPTIONS='-c default_transaction_read_only=on' "$C" psql -X -q -v ON_ERROR_STOP=1 -d techo360_principal -c "$1" 2>/dev/null && return 0
  docker exec -e PGOPTIONS='-c default_transaction_read_only=on' "$C" sh -c 'exec psql -X -q -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "${POSTGRES_DB:-techo360_principal}" -c "$0"' "$1"
}
echo "@@@ro"; run "SHOW default_transaction_read_only"
echo "@@@mapcalordb"; run "COPY (SELECT codigodivipola, namevar, yearm, valuevar, originvar, intervaloconfianza FROM public.mapcalordb WHERE namevar IN ('score_privacion','cobertura_acueducto','cobertura_alcantarillado','deficit_habitacional_cuantitativo','deficit_habitacional_cualitativo','densidad_poblacional') ORDER BY codigodivipola, namevar, yearm) TO STDOUT WITH CSV HEADER"
echo "@@@zonas_municipio"; run "COPY (SELECT m.codigo_municipio, m.codigo_departamento, m.nombre AS municipio, d.nombre AS departamento FROM public.zonas_municipio m LEFT JOIN public.zonas_departamento d ON d.codigo_departamento = m.codigo_departamento ORDER BY m.codigo_municipio) TO STDOUT WITH CSV HEADER"
echo "@@@fin"
