#!/usr/bin/env bash
# Levanta el lab completo listo para demo: Zabbix + observabilidad + simulador
# con datos historicos. Uso:
#
#   ./scripts/demo-up.sh            # levanta y siembra 6 dias de logs
#   ./scripts/demo-up.sh --no-seed  # sin siembra (mas rapido)
#
# Requiere: docker compose v2, .env en docker/ con GF_ADMIN_PASSWORD y
# ZBX_API_TOKEN (ver docker/observability/README.md).

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT/docker"

SEED=1
[[ "${1:-}" == "--no-seed" ]] && SEED=0

COMPOSE=(docker compose
  -f docker-compose.yml
  -f docker-compose.lab.yml
  -f docker-compose.observability.yml
  --profile lab
  --profile observability)

echo "== 1/3 levantando el stack"
"${COMPOSE[@]}" up -d --build

echo "== 2/3 esperando servicios clave"
for _ in $(seq 1 40); do
  if docker run --rm --network zbx-in-docker_backend alpine:3.22 \
       wget -qO- http://loki:3100/ready 2>/dev/null | grep -qi ready; then
    break
  fi
  sleep 2
done

if [[ "$SEED" == "1" ]]; then
  echo "== 3/3 sembrando 6 dias de syslog (una sola vez)"
  "${COMPOSE[@]}" run --rm \
    -e LAB_BACKFILL_DAYS=6 -e LAB_BACKFILL_ONLY=1 lab-simulator \
    | grep -E "backfill|ERROR" || true
else
  echo "== 3/3 siembra omitida"
fi

echo
echo "Listo."
echo "  Cliente : http://127.0.0.1/grafana/d/estado-servicio"
echo "  Tecnico : http://127.0.0.1/grafana/d/tecnico-observabilidad"
echo "  Monitoreo: http://127.0.0.1/grafana/d/salud-monitoreo"
echo "  Usuario : admin  (password en docker/.env: GF_ADMIN_PASSWORD)"
