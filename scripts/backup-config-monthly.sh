#!/usr/bin/env bash
# backup-config-monthly.sh — Respaldo mensual SOLO-configuración de Zabbix, por sitio.
#
# Genera un volcado de configuración (sin history/trends) y lo deja listo
# para subir a Drive a la carpeta del cliente. No incluye historial: el
# resultado pesa unos pocos MB comprimido.
#
# Uso:
#   SITE=site-a scripts/backup-config-monthly.sh
#   SITE=site-b scripts/backup-config-monthly.sh
#   # Solo host nativo pre-migración (site-b vieja 198.51.100.38):
#   SITE=site-b DB_TYPE=mysql scripts/backup-config-monthly.sh
#
# Variables de entorno (todas opcionales):
#   SITE            Sitio a respaldar (por defecto: site-a). Acepta cualquier
#                   cliente futuro en minúsculas, p. ej. site-a, site-b.
#   DB_TYPE         postgres | mysql | auto (por defecto: postgres, el stack
#                   ya migrado; usar mysql SOLO en host nativo pre-migración,
#                   auto detecta postgres de compose y si no responde aborta
#                   en vez de asumir mysql).
#   DATA_DIR        Directorio de datos (por defecto: /opt/monitoring/data).
#   BKP_DIR         Directorio de volcados
#                   (por defecto: ${DATA_DIR}/bkp-pre-docker).
#   MYSQL_CNF       Archivo de credenciales solo-lectura para diagnóstico
#                   MySQL (por defecto: ~/.my.cnf). Nunca se muestra su
#                   contenido ni se pasa la clave por línea de comandos.
#   MYSQL_DB        Base MySQL origen (por defecto: zabbix).
#   PGUSER / PGDATABASE / PGCONTAINER
#                   Usuario, base y contenedor Postgres (por defecto:
#                   zabbix / zabbix / zabbix-postgres). Se accede vía
#                   `docker exec` al contenedor (postgres no publica
#                   puertos al host), así no hace falta clave: rige el
#                   pg_hba del contenedor. Nunca por línea de comandos
#                   ni por pantalla.
#   RETENTION_LOCAL Copias rotativas a conservar en disco, sin contar la
#                   copia mensual YYYYMM (por defecto: 3).
#   COMPOSE_FILE    Compose a inspeccionar en modo auto
#                   (por defecto: <repo>/docker/docker-compose.yml).
#
# Salidas en BKP_DIR:
#   zbx-config-<site>-<AAAAMMDD-HHMM>.sql.gz  Copia rotativa (retención local).
#   zbx-config-<site>-<AAAAMM>.sql.gz         Copia mensual (se conserva).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SITE="${SITE:-site-a}"
DB_TYPE="${DB_TYPE:-postgres}"
DATA_DIR="${DATA_DIR:-/opt/monitoring/data}"
BKP_DIR="${BKP_DIR:-${DATA_DIR}/bkp-pre-docker}"
MYSQL_CNF="${MYSQL_CNF:-$HOME/.my.cnf}"
MYSQL_DB="${MYSQL_DB:-zabbix}"
PGUSER="${PGUSER:-zabbix}"
PGDATABASE="${PGDATABASE:-zabbix}"
PGCONTAINER="${PGCONTAINER:-zabbix-postgres}"
RETENTION_LOCAL="${RETENTION_LOCAL:-3}"
COMPOSE_FILE="${COMPOSE_FILE:-$ROOT/docker/docker-compose.yml}"

# Tablas de historial/tendencias: siempre excluidas (respaldo solo-config).
# Son 7: 5 de history + 2 de trends.
HISTORY_TABLES="history history_uint history_str history_text history_log trends trends_uint"

# Validación mínima del nombre de sitio (genérico para clientes futuros).
if [[ ! "$SITE" =~ ^[a-z0-9-]+$ ]]; then
  echo "ERROR: SITE inválido: '$SITE' (usar minúsculas, ej. site-a, site-b)." >&2
  exit 1
fi

# Detección del motor: el stack ya está en postgres. Solo se usa mysql
# con DB_TYPE=mysql explícito en host nativo pre-migración. En modo auto,
# si el postgres de compose no responde se aborta (no se asume mysql).
detect_db_type() {
  if [[ "$DB_TYPE" != "auto" ]]; then
    echo "$DB_TYPE"
    return
  fi
  if docker exec "$PGCONTAINER" \
      pg_isready -U "$PGUSER" >/dev/null 2>&1; then
    echo "postgres"
  else
    echo "ERROR: postgres de compose no responde y DB_TYPE=auto; el stack es postgres. Para host nativo pre-migración usar DB_TYPE=mysql explícito." >&2
    exit 1
  fi
}

ENGINE="$(detect_db_type)"
if [[ "$ENGINE" != "mysql" && "$ENGINE" != "postgres" ]]; then
  echo "ERROR: DB_TYPE inválido: '$DB_TYPE' (usar mysql|postgres|auto)." >&2
  exit 1
fi

STAMP="$(date +%Y%m%d-%H%M)"
YYYYMM="$(date +%Y%m)"
mkdir -p "$BKP_DIR"
WORK="$BKP_DIR/zbx-config-${SITE}-${STAMP}.sql.gz"
MONTHLY="$BKP_DIR/zbx-config-${SITE}-${YYYYMM}.sql.gz"

echo "=== Respaldo mensual solo-config: sitio=$SITE motor=$ENGINE ==="

if [[ "$ENGINE" == "mysql" ]]; then
  # Credenciales solo vía archivo --defaults-extra-file (nunca en CLI).
  if [[ ! -r "$MYSQL_CNF" ]]; then
    echo "ERROR: no se puede leer MYSQL_CNF=$MYSQL_CNF" >&2
    exit 1
  fi
  IGNORES=()
  for t in $HISTORY_TABLES; do
    IGNORES+=(--ignore-table="${MYSQL_DB}.${t}")
  done
  # Esquema completo (sin datos) + datos de config (sin CREATE, sin history).
  {
    mysqldump --defaults-extra-file="$MYSQL_CNF" \
      --single-transaction --quick --no-tablespaces \
      --no-data "$MYSQL_DB"
    mysqldump --defaults-extra-file="$MYSQL_CNF" \
      --single-transaction --quick --no-tablespaces \
      --no-create-info "${IGNORES[@]}" "$MYSQL_DB"
  } | gzip > "$WORK"
else
  # Vía docker exec al contenedor (sin publicar puertos, sin clave en CLI).
  # --exclude-table-data: conserva el CREATE TABLE pero omite las filas
  # (equivalente al --ignore-table de datos de MySQL en un solo volcado).
  # Validado en site-a 2026-09-19: DB 3313 MB -> 6.9M gz en 2.3s.
  EXCLUDES=()
  for t in $HISTORY_TABLES; do
    EXCLUDES+=(--exclude-table-data="$t")
  done
  docker exec "$PGCONTAINER" pg_dump -U "$PGUSER" -d "$PGDATABASE" \
    --no-owner --no-privileges "${EXCLUDES[@]}" | gzip > "$WORK"
fi

# Puerta de integridad: el .gz debe estar sano antes de seguir.
gzip -t "$WORK"
echo "OK integridad gzip: $WORK"

# Tamaño esperado: pocos MB (solo-config, sin historial).
ls -lh "$WORK"

# Validación de conteos: un respaldo con 0 hosts es inútil, se aborta.
if [[ "$ENGINE" == "mysql" ]]; then
  HOSTS="$(mysql --defaults-extra-file="$MYSQL_CNF" -NBe \
    "SELECT COUNT(*) FROM hosts;" "$MYSQL_DB")"
  ITEMS="$(mysql --defaults-extra-file="$MYSQL_CNF" -NBe \
    "SELECT COUNT(*) FROM items;" "$MYSQL_DB")"
else
  HOSTS="$(docker exec "$PGCONTAINER" psql -U "$PGUSER" -d "$PGDATABASE" -tAc \
    "SELECT COUNT(*) FROM hosts;")"
  ITEMS="$(docker exec "$PGCONTAINER" psql -U "$PGUSER" -d "$PGDATABASE" -tAc \
    "SELECT COUNT(*) FROM items;")"
fi
echo "Conteos en origen: hosts=$HOSTS items=$ITEMS"
if [[ "$HOSTS" -eq 0 ]]; then
  echo "ERROR: la base origen tiene 0 hosts; respaldo descartado." >&2
  exit 1
fi
if [[ "$ITEMS" -eq 0 ]]; then
  echo "AVISO: la base origen tiene 0 items; revisar antes de subir a Drive."
fi

# Copia mensual YYYYMM (idempotente dentro del mes) + retención local.
cp -p "$WORK" "$MONTHLY"
echo "OK copia mensual: $MONTHLY"
# Sello de éxito: fecha UTC + archivo + tamaño. Es lo que vigila el
# chequeo mensual (ver docs/recupero.md §5): si el sello tiene más de
# 35 días, el respaldo no está corriendo.
printf '%s %s %s\n' "$(date -u +%FT%TZ)" "$MONTHLY" "$(stat -c %s "$MONTHLY")" \
  > "$BKP_DIR/.last-backup-$SITE.ok"
echo "OK sello: $BKP_DIR/.last-backup-$SITE.ok"

# Reporte al propio Zabbix (trapper en el host "Zabbix server"): estado 1
# y antigüedad 0 días. El trigger `nodata(...,37d)` avisa si el respaldo
# deja de correr. Si el envío falla, no rompe el backup.
if command -v zabbix_sender >/dev/null 2>&1; then
  zabbix_sender -z 127.0.0.1 -p 10051 -s "Zabbix server" \
    -k zbx.backup.status -o 1 >/dev/null 2>&1 \
    || echo "AVISO: no se pudo reportar zbx.backup.status"
  zabbix_sender -z 127.0.0.1 -p 10051 -s "Zabbix server" \
    -k zbx.backup.age_days -o 0 >/dev/null 2>&1 \
    || echo "AVISO: no se pudo reportar zbx.backup.age_days"
fi
# Poda: conserva las N copias rotativas más nuevas; la mensual nunca se poda.
# shellcheck disable=SC2012
ls -1t "$BKP_DIR"/zbx-config-"$SITE"-*.sql.gz 2>/dev/null \
  | grep -vE "[0-9]{6}\.sql\.gz$" \
  | tail -n +"$((RETENTION_LOCAL + 1))" \
  | xargs -r rm --
echo "OK retención local: $RETENTION_LOCAL copias rotativas + mensual $YYYYMM."

# Paso siguiente: subir a Drive (manual o con agente). Sin credenciales
# aquí: solo se imprime el destino y un ejemplo a adaptar.
echo ""
echo "Destino Drive: projects/CLIENTES/${SITE}/zbx-backups/${YYYYMM}/"
echo "Subir ${MONTHLY} a esa carpeta (manual o con rclone/agente)."
echo "Ejemplo a adaptar con google-agent:"
echo "  google-agent files upload \"$MONTHLY\" --dest \"projects/CLIENTES/${SITE}/zbx-backups/${YYYYMM}/\""
echo ""
echo "=== Listo: $MONTHLY ==="
