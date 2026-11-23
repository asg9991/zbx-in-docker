#!/usr/bin/env bash
# Verificación de coherencia de la capa de observabilidad.
# Corre en ~20 s y es lo que debería ejecutarse antes de cada commit/deploy.
set -uo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
fail=0

ok()   { printf "  ok   %s\n" "$1"; }
bad()  { printf "  FALLA %s\n" "$1"; fail=1; }

echo "== compose"
if (cd docker && docker compose -f docker-compose.yml -f docker-compose.lab.yml \
     -f docker-compose.observability.yml --profile lab --profile observability \
     config --quiet 2>/dev/null); then ok "config válido"; else bad "config inválido"; fi

echo "== generadores sincronizados"
python3 scripts/gen_queries.py --check >/dev/null 2>&1 && ok "consultas" || bad "consultas desincronizadas"
python3 scripts/nav_links.py --check >/dev/null 2>&1 && ok "navegación" || bad "navegación inconsistente"

echo "== contexto"
python3 scripts/digest.py --check >/dev/null 2>&1 && ok "clases + servicios" || bad "contexto inválido"

echo "== clasificador"
if python3 scripts/evaluar_clasificador.py >/tmp/check_clasificador.txt 2>&1; then
  ok "$(grep -m1 RETENCIÓN /tmp/check_clasificador.txt | sed 's/^ *//')"
else
  bad "precisión bajo el umbral (ver scripts/evaluar_clasificador.py)"
fi

echo "== disco"
bash scripts/check_disk.sh >/dev/null 2>&1 && ok "espacio suficiente" || bad "poco espacio libre (scripts/check_disk.sh)"

echo "== dashboards servidos"
if command -v curl >/dev/null; then
  # UIDs desde los dashboards presentes: sirve en lab y en un cliente, sin
  # listas hardcodeadas que se desactualizan.
  UIDS=$(python3 - <<'PY_UIDS'
import json, pathlib
for f in sorted(pathlib.Path("docker/observability/grafana/dashboards").rglob("*.json")):
    uid = json.loads(f.read_text()).get("uid")
    if uid:
        print(uid)
PY_UIDS
)
  [ -n "$UIDS" ] || bad "no se pudieron listar los dashboards"
  GHOST="${GRAFANA_ROOT_URL:-$(grep -m1 '^GRAFANA_ROOT_URL=' docker/.env 2>/dev/null | cut -d= -f2)}"
  GHOST="${GHOST:-http://127.0.0.1/grafana/}"
  GBASE="${GHOST%/}"
  T=$(grep -m1 '^GF_READ_TOKEN=' docker/.env 2>/dev/null | cut -d= -f2 || true)
  if [ -n "$T" ]; then
    AUTH=(-H "Authorization: Bearer $T")
  else
    U=$(grep -m1 '^GF_ADMIN_USER=' docker/.env 2>/dev/null | cut -d= -f2)
    P=$(grep -m1 '^GF_ADMIN_PASSWORD=' docker/.env 2>/dev/null | cut -d= -f2)
    B=$(printf '%s:%s' "$U" "$P" | base64 -w0)
    AUTH=(-H "Authorization: Basic $B")
  fi
  for uid in $UIDS; do
    code=$(curl -s -o /dev/null -w '%{http_code}' "${AUTH[@]}" "$GBASE/d/$uid")
    [ "$code" = "200" ] && ok "$uid" || bad "$uid ($code)"
  done
fi

echo
[ "$fail" = "0" ] && echo "TODO OK" || echo "HAY FALLAS"
exit "$fail"
