# Recuperación ante desastres — zbx-in-docker (genérico por sitio)

Guía genérica de reconstrucción para cualquier sitio que opere con este
repositorio. El repositorio es idéntico para todos los clientes; lo que
diferencia a cada sitio vive fuera del repositorio, en el host y en la
bóveda de secretos.

> Convención: en el cuerpo se utilizan marcadores como `<SERVER_NAME>`,
> `<IP-PROD>` o `<DATA_DIR>`. Los valores reales de cada sitio aparecen
> únicamente en el Anexo, a modo de ejemplo documentado. Nunca se escriben
> secretos (contraseñas, claves privadas, tokens) en este documento.

## 1. Reconstrucción desde cero

Requisitos base del host nuevo: Ubuntu 24.04, Docker 24 o superior
(con el complemento Compose v2) y acceso a la bóveda de secretos del sitio.

1. **Instalar dependencias base.** Ubuntu 24.04 actualizado, Docker 24+,
   `git` y `gzip` disponibles.
2. **Clonar el repositorio.**
   ```bash
   git clone <URL-REPO> /opt/monitoring/zbx-in-docker
   cd /opt/monitoring/zbx-in-docker
   git checkout <RAMA-O-TAG-PINNEADO>
   ```
3. **Recrear `docker/.env` desde la bóveda.** Copiar la plantilla
   (`docker/.env.example`) y completar exclusivamente desde la bóveda,
   sin inventar valores. Variables relevantes:
   `POSTGRES_PASSWORD`, `SERVER_NAME`, `DATA_DIR=/opt/monitoring/data`,
   `HTTP_BIND_IP` / `HTTP_PORT` / `HTTPS_BIND_IP` / `HTTPS_PORT`
   y las de afinado `ZBX_*`. Verificar que no queden advertencias de
   variables indefinidas con `docker compose config`.
4. **Restaurar certificados en `${DATA_DIR}/certs`.** Copiar `fullchain.pem`
   (permiso `644`) y `privkey.pem` (permiso `600`, propiedad `root`) desde
   la copia externa. Nunca generar una clave nueva salvo que se trate de
   una reemisión deliberada. Ver `docs/seguridad-secretos.md`.
5. **Restaurar `DATA_DIR`.** Incluye el volumen de Postgres
   (`${DATA_DIR}/postgres`) y el directorio de respaldo
   (`${DATA_DIR}/bkp-pre-docker` o la ruta equivalente del sitio según
   el Anexo). Si se restaura a partir de un volcado `pg_dump`, colocarlo
   en el directorio de respaldo y seguir el procedimiento de importación
   del runbook correspondiente.
6. **Levantar la pila.**
   ```bash
   cd docker && docker compose up -d
   docker compose ps
   docker compose config   # puerta: salida 0, sin advertencias
   ```
7. **Puerta de versión de API.** Confirmar que la API responde con la
   versión esperada y el nivel de esquema obligatorio:
   ```bash
   curl -s http(s)://<SERVER_NAME>/api_jsonrpc.php \
     -H 'Content-Type: application/json' \
     -d '{"jsonrpc":"2.0","method":"apiinfo.version","id":1,"params":{}}'
   ```
   Comparar contra la versión documentada en el runbook del sitio.
8. **Puerta de conteos.** Verificar cantidades de `hosts`, `items`,
   `triggers` y reglas de descubrimiento contra los valores esperados del
   sitio (ver runbooks y `docs/migracion-checklist.md`). Cualquier
   diferencia sin explicación documentada detiene el corte.
9. **Reapuntar el objeto `Zabbix server`.** Actualizar su interfaz a los
   valores DNS/IP internos del despliegue Docker y confirmar que queda
   disponible (`available=1`) en unos dos minutos. Procedimiento exacto
   en `docs/migracion-checklist.md` (§9) y en cada runbook.

## 2. Qué vive en cada lugar

| Elemento | Dónde vive | En git | Notas |
|---|---|---|---|
| Compose genérico y plantillas (`docker/docker-compose.yml`, `docker/nginx/*.template`) | Repositorio | Sí | Idéntico para todos los sitios; la variación por sitio se resuelve por variables de entorno |
| Runbooks y documentación (`docs/`) | Repositorio | Sí | Genéricos; el Anexo conserva los datos específicos de cada sitio |
| `docker/.env` (con `POSTGRES_PASSWORD`, `SERVER_NAME`, `ZBX_*`) | Solo en el host y en la bóveda | No (ignorado por git) | Sin este archivo no hay reconstrucción fiel; su única copia válida fuera del host está en la bóveda |
| `data/postgres` (volumen de base de datos) | Solo en el host (`${DATA_DIR}/postgres`) | No | Volcado nocturno con `pg_dump` hacia el directorio de respaldo |
| `data/certs` (`fullchain.pem`, `privkey.pem`) | Solo en el host (`${DATA_DIR}/certs`) | No | `privkey.pem` con permiso `600`; montado de solo lectura en nginx |
| Volcados (`bkp-pre-docker/*.sql.gz`) | Solo en el host + copia externa | No | Comprobar integridad con `gzip -t` antes de importar |
| `pgloader-<cliente>.load` con contraseña real | Solo en el host, temporal | No | El repositorio conserva únicamente la plantilla genérica `docker/pgloader.load`; toda copia con credenciales reales se elimina tras la migración |

Regla de secretos: nunca incorporar al repositorio archivos `*.pem` ni
`*.key`, ni contraseñas ni tokens. Ver `docs/seguridad-secretos.md`:
la clave privada queda en `${DATA_DIR}/certs/privkey.pem` con permiso
`600`, y su contenido jamás se imprime en registros, incidencias ni
salidas de comandos.

## 3. Respaldo mínimo por sitio (lista de verificación)

Cada sitio debe cumplir estos cuatro puntos de forma permanente:

1. **Volcado nocturno de Postgres** con `pg_dump` hacia el directorio de
   respaldo del sitio, más **copia externa** (fuera del host) del volcado
   más reciente.
2. **Copia de `docker/.env` en la bóveda** (nunca en el repositorio).
   Debe permitir recrear el archivo variable por variable.
3. **Copia externa de los certificados** (`fullchain.pem` y
   `privkey.pem`), con nota de su fecha de emisión y caducidad.
4. **Retención de 7 días** de volcados en el host, verificados
   periódicamente con `gzip -t`.

Sin estos cuatro elementos no existe recuperación garantizada: solo
reinstalación con pérdida de configuración.

## 4. Si el servidor falla mañana

Respuesta directa:

- **Con repositorio genérico + `.env` + certificados + volcado disponibles
  fuera del host:** la reconstrucción sobre un host nuevo con Ubuntu 24.04
  y Docker 24+ toma **menos de 1 hora** (clonar, completar `.env` desde la
  bóveda, restaurar certificados y `DATA_DIR`, `compose up -d`, puertas de
  API y conteos, reapunte del objeto `Zabbix server`).
- **Sin copia externa de `.env`, certificados o volcado:** la
  reconstrucción exige generar contraseñas nuevas, reemitir certificados y
  volver a migrar desde los volcados nativos originales. Esto convierte un
  incidente de una hora en **varias horas de trabajo**, con riesgo de
  divergencia de configuración.

Por este motivo, las copias externas deben existir y estar verificadas
**antes** de la Fase 2 de cada sitio. Ningún corte a producción se da por
cerrado sin ellas.

## 5. Respaldo mensual solo-configuración a Drive (por cliente)

Una vez por mes, cada sitio genera un volcado **solo-configuración** con
`scripts/backup-config-monthly.sh` (variables `SITE`, `DB_TYPE`, `DATA_DIR`):

```bash
SITE=site-a scripts/backup-config-monthly.sh
```

El script excluye siempre las 7 tablas de historial/tendencias
(`history*`, `trends*`): en MySQL con `--ignore-table`, en Postgres con
`--exclude-table-data` (conserva el schema, omite las filas). El resultado
pesa pocos MB comprimido. Conserva 3 copias rotativas en el host más una
copia mensual `YYYYMM`, verifica integridad con `gzip -t`, valida conteos
de `hosts`/`items` y deja el sello `.last-backup-<SITE>.ok` con fecha UTC.

### Ejecución automática y chequeo (systemd)

El respaldo corre solo con un timer por sitio (unidad instanciada):

```bash
# Instalación (una vez por host, con sudo):
sudo cp systemd/zbx-backup@.service systemd/zbx-backup@.timer /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now zbx-backup@site-a.timer   # o @site-b en site-b

# Chequeo mensual (sin sudo):
systemctl list-timers 'zbx-backup@*' --all
cat /opt/monitoring/data/bkp-pre-docker/.last-backup-site-a.ok
journalctl -u 'zbx-backup@site-a.service' --since '35 days ago' | tail -5
ls -lh /opt/monitoring/data/bkp-pre-docker/zbx-config-site-a-$(date +%Y%m).sql.gz
```

Si el sello tiene más de 35 días o el timer figura fallido, el respaldo no
está corriendo. El aviso automático usa dos ítems trapper en el host
`Zabbix server` (`zbx.backup.status`, `zbx.backup.age_days`) más el trigger
`Backup mensual desactualizado` (`nodata(...,37d)`, Warning) hacia el
Telegram existente; el script los alimenta vía `zabbix_sender` del
contenedor agent2 en cada corrida. Gotcha: tras crear ítems por API, el
server puede tardar en verlos en caché (`cannot retrieve key ... from
configuration cache`) — `zabbix_server -R config_cache_reload`, y si
persiste, `compose restart zabbix-server`.

### Archivos por cliente

Lo genérico vive en `docker/`, `scripts/`, `systemd/` y `docs/`. Lo de cada
cliente vive en `overlays/<cliente>/` (p. ej.
`overlays/site-b/verify-site-b-migration.sh`) más su `.env`, certificados y
volcados en el host, fuera de git. Nada con nombre de cliente va en
`scripts/` raíz.

La copia mensual se sube a Drive a
`projects/CLIENTES/<SITE>/zbx-backups/YYYYMM/` (manual o con
rclone/agente; el script imprime el destino y el ejemplo). El historial
completo queda fuera de alcance: ante un desastre se reconstruye la
configuración, no las series históricas.

## Anexo A — Datos por sitio (ejemplos documentados)

| Sitio | Estado | `SERVER_NAME` (ejemplo) | `DATA_DIR` | Respaldo | Puertos / TLS |
|---|---|---|---|---|---|
| site-a | Migrado | `zabbix.example.com` | `/opt/monitoring/data` | `/opt/monitoring/bkp-pre-docker` | Producción en `80/443` con TLS |
| site-b | Migrado 2026-09-28 | `zabbix.example.org` | `/opt/monitoring/data` | `/opt/monitoring/data/bkp-pre-docker` | Corte completo a `198.51.100.38` (réplica de privadas `.113`/`198.51.100.32`); origen HTTP vía Cloudflare Flexible hasta Fase2 TLS |

Notas:

- site-a operó como migración en el lugar (`in-place`); su fila sirve como
  referencia de método ya validado, no como fuente de datos para otros
  sitios.
- site-b migra hacia una máquina virtual nueva: la Fase 1 expone el
  servicio por HTTP en un puerto alternativo, y la Fase 2 lo traslada a
  los puertos de producción con TLS a través de Cloudflare.

## Documentos relacionados

- `docs/runbook-migracion-site-a.md` — procedimiento de corte de site-a.
- `docs/runbook-migracion-site-b.md` — procedimiento de corte de site-b.
- `docs/tls-letsencrypt-direct.md` — TLS con Let's Encrypt directo.
- `docs/tls-cloudflare-origin.md` — TLS con origen Cloudflare.
- `docs/migracion-checklist.md` — lista de verificación posterior a la
  migración (puertas de API, conteos, reapunte del objeto
  `Zabbix server`).
- `docs/seguridad-secretos.md` — manejo de secretos y claves privadas.
