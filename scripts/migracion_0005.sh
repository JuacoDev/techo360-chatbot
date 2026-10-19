#!/usr/bin/env sh
# Migracion 0005 (tablas del RAG curado) contra postgres-vector.
#
#   scripts/migracion_0005.sh --dry-run   # ejecuta TODO y termina con ROLLBACK (no cambia nada)
#   scripts/migracion_0005.sh --aplicar   # ejecuta y hace COMMIT (requiere autorizacion)
#   scripts/migracion_0005.sh --reversa   # ejecuta 0005_..._down.sql (requiere autorizacion)
#
# Variables: CONTENEDOR (por defecto techo360-postgres-vector). Las credenciales NO se
# pasan aqui: psql corre DENTRO del contenedor con $POSTGRES_USER/$POSTGRES_DB del propio
# contenedor (no se imprimen).
#
# Antes de --aplicar (NO lo hace este script):
#   1. Autorizacion explicita del responsable.
#   2. Respaldo de postgres-vector FUERA de la rotacion (scripts/backup-db.sh de
#      techo360-infra), `gzip -t` OK y sha256 anotado; copia verificada en otra maquina.
#   3. migrations/verificar_0005_antes.sql (solo lectura) y --dry-run sin errores.
# Despues: migrations/verificar_0005_despues.sql.
set -eu

RAIZ=$(cd "$(dirname "$0")/.." && pwd)
CONTENEDOR=${CONTENEDOR:-techo360-postgres-vector}
MIG="$RAIZ/migrations/0005_rag_documentos_fragmentos.sql"
DOWN="$RAIZ/migrations/0005_rag_documentos_fragmentos_down.sql"

psql_en_contenedor() {
    docker exec -i "$CONTENEDOR" sh -c 'psql -X -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB"'
}

case "${1:-}" in
    --dry-run)
        # Igual que --aplicar, pero el COMMIT final se cambia por ROLLBACK.
        grep -q '^COMMIT;' "$MIG" || { echo "La migracion no termina en COMMIT; se aborta" >&2; exit 1; }
        sed 's/^COMMIT;/ROLLBACK;/' "$MIG" | psql_en_contenedor
        echo "dry-run: terminado con ROLLBACK (sin cambios)"
        ;;
    --aplicar)
        psql_en_contenedor < "$MIG"
        echo "aplicada: correr migrations/verificar_0005_despues.sql"
        ;;
    --reversa)
        psql_en_contenedor < "$DOWN"
        echo "reversa aplicada"
        ;;
    *)
        echo "uso: $0 --dry-run | --aplicar | --reversa" >&2
        exit 2
        ;;
esac
