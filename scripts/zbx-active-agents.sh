#!/usr/bin/env bash
# zbx-active-agents.sh — qué agents ACTIVOS están reportando, sin GUI.
#
# Los agents activos llaman al server (no al revés), así que `zabbix_get`
# no sirve: se verifica por datos recibidos. Lista hosts con ítems
# Zabbix-agent-activo (type 7) habilitados, cantidad y hace cuántos
# segundos llegó el último dato.
#
# Uso: ./scripts/zbx-active-agents.sh   (en el host del stack)
#
# Variables opcionales: PGCONTAINER (defecto zabbix-postgres),
#   PGUSER/PGDATABASE (defecto zabbix/zabbix).
set -euo pipefail

PGCONTAINER="${PGCONTAINER:-zabbix-postgres}"
PGUSER="${PGUSER:-zabbix}"
PGDATABASE="${PGDATABASE:-zabbix}"
NOW=$(date +%s)

docker exec "$PGCONTAINER" psql -U "$PGUSER" -d "$PGDATABASE" -tA -F'|' \
  -c "SELECT h.host, count(i.itemid),
             COALESCE(max(hu.clock), 0)
      FROM hosts h
      JOIN items i ON i.hostid = h.hostid AND i.type = 7 AND i.status = 0
      LEFT JOIN history_uint hu ON hu.itemid = i.itemid
      WHERE h.status = 0 AND h.flags = 0
      GROUP BY h.host ORDER BY 1;" |
while IFS='|' read -r host nitems clock; do
  if [ "${clock:-0}" -eq 0 ]; then
    echo "$host | active_items:$nitems | SIN DATOS (revisar ServerActive/apagado)"
  else
    echo "$host | active_items:$nitems | ultimo dato hace $((NOW - clock))s"
  fi
done
