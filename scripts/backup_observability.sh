#!/usr/bin/env bash
# Respaldo de la capa de observabilidad.
#
# Incluye lo que NO está en el repo: la base de Grafana (usuarios,
# preferencias). Dashboards y datasources vienen del repositorio.
# Loki no se respalda: su retención es corta y no es fuente de verdad.
#
# El archivo lo escribe Grafana como uid 472, así que el operador normalmente
# no puede leerlo: correr con sudo.
#
#   sudo ./scripts/backup_observability.sh [/ruta/de/backups]
#
# La copia usa la API de backup de SQLite (consistente con la base abierta).
# Un `cp` de un archivo vivo puede salir inconsistente: no se usa.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
D="${DATA_DIR:-$(grep -m1 '^DATA_DIR=' "$ROOT/docker/.env" 2>/dev/null | cut -d= -f2)}"
D="${D:-/opt/monitoring/data}"
DEST="${1:-$ROOT/backups}"
FECHA=$(date +%Y%m%d-%H%M)
DB="$D/grafana/grafana.db"
OUT="$DEST/grafana-$FECHA.db"

mkdir -p "$DEST"

if [ ! -f "$DB" ]; then
  echo "ERROR: no existe $DB"
  exit 1
fi

if [ ! -r "$DB" ]; then
  echo "ERROR: no se puede leer $DB (dueño $(stat -c '%u:%g' "$DB" 2>/dev/null || echo '?'))"
  echo "       Correr como root: sudo $0 $DEST"
  exit 1
fi

# Copia consistente. sqlite3 si está; si no, Python (stdlib), que no depende
# de nada instalado y sí garantiza consistencia.
if command -v sqlite3 >/dev/null; then
  sqlite3 "$DB" ".backup '$OUT'"
  sqlite3 "$OUT" "PRAGMA integrity_check;" | grep -qx ok \
    || { echo "ERROR: la copia no pasó integrity_check"; rm -f "$OUT"; exit 1; }
elif command -v python3 >/dev/null; then
  python3 - "$DB" "$OUT" <<'PY'
import sqlite3, sys
src, dst = sys.argv[1], sys.argv[2]
with sqlite3.connect(f"file:{src}?mode=ro", uri=True) as s, \
     sqlite3.connect(dst) as d:
    s.backup(d)
    if d.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
        sys.exit("ERROR: la copia no pasó integrity_check")
PY
else
  echo "ERROR: falta sqlite3 o python3 para hacer una copia consistente"
  exit 1
fi

gzip -f "$OUT"
echo "respaldo: $OUT.gz ($(du -h "$OUT.gz" | cut -f1))"
echo "para restaurar: ver docs/respaldo-observabilidad.md"
