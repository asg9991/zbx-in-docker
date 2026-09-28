#!/usr/bin/env bash
# zbx-host-freshness.sh — frescura de datos por host sin esperar la GUI.
#
# Por cada host habilitado muestra: disponibilidad de interfaces y hace
# cuántos segundos llegó el último dato (agent activo/pasivo, SNMP, trapper).
#
# Uso:
#   ./scripts/zbx-host-freshness.sh [PATRON]   # ej: ./scripts/zbx-host-freshness.sh MXK
#   Sin argumento: todos los hosts habilitados (sin templates).
#
# Requiere: docker con acceso al contenedor postgres del compose.
# Variables opcionales: PGCONTAINER (defecto zabbix-postgres),
#   PGUSER/PGDATABASE (defecto zabbix/zabbix).
set -euo pipefail

PGCONTAINER="${PGCONTAINER:-zabbix-postgres}"
PGUSER="${PGUSER:-zabbix}"
PGDATABASE="${PGDATABASE:-zabbix}"
PATTERN="${1:-}"
PATTERN="%${PATTERN}%"
NOW=$(date +%s)

docker exec "$PGCONTAINER" psql -U "$PGUSER" -d "$PGDATABASE" -tA -F'|' \
  -c "SELECT h.host, COALESCE(string_agg(DISTINCT i.available::text, ','), '-'),
             COALESCE(max(hu.clock), 0)
      FROM hosts h
      LEFT JOIN interface i ON i.hostid = h.hostid
      LEFT JOIN items it ON it.hostid = h.hostid
      LEFT JOIN history_uint hu ON hu.itemid = it.itemid
      WHERE h.status = 0 AND h.flags = 0 AND h.host ILIKE '$PATTERN'
      GROUP BY h.host ORDER BY 1;" |
while IFS='|' read -r host avail clock; do
  if [ "${clock:-0}" -eq 0 ]; then
    echo "$host | if:$avail | sin datos uint (ver history* en GUI)"
  else
    echo "$host | if:$avail | ultimo dato hace $((NOW - clock))s"
  fi
done
