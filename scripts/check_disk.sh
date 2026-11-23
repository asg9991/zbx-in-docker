#!/usr/bin/env bash
# Verifica espacio libre para la capa de observabilidad.
# Pensado para cron/systemd en el host del sitio; también lo usa check_all.sh.
#
# En un cliente, la alerta real es un trigger de Zabbix sobre el item del
# filesystem (más confiable que este script):
#   vfs.fs.size[<fs>,pfree] < 20  -> WARNING
#   vfs.fs.size[<fs>,pfree] < 10  -> HIGH
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
D="${DATA_DIR:-$(grep -m1 '^DATA_DIR=' "$ROOT/docker/.env" 2>/dev/null | cut -d= -f2)}"
D="${D:-/opt/monitoring/data}"
UMBRAL="${1:-20}"

uso=$(df -P "$D" | awk 'NR==2 {gsub(/%/,"",$5); print $5}')
libre=$((100 - uso))
echo "DATA_DIR=$D  usado=${uso}%  libre=${libre}%  umbral=${UMBRAL}%"
if [ "$libre" -lt "$UMBRAL" ]; then
  echo "FALLA: libre por debajo del umbral"
  exit 1
fi
echo "ok"
