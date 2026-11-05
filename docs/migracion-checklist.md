# Migración Zabbix nativo → Docker — checklist post-migración (lecciones de una migración real, 2026-09-15/16)

Todo lo que se dio por asumido y mordió. Verificar uno por uno antes de dar la
migración por cerrada.

## 1. Un solo server en pie

- `ps aux | grep zabbix_server` debe mostrar SOLO procesos del container.
  `systemctl is-active` MIENTE si el nativo se lanzó con `--foreground` a mano:
  aparece `inactive` con el proceso vivo igual.
- Separar nativo vs docker por cgroup (mismo nombre de proceso):
  `for p in $(pgrep -f 'zabbix_server:'); do grep -qa docker /proc/$p/cgroup 2>/dev/null || echo $p; done`
  Lo que imprima es nativo → `sudo kill` uno por uno (matar solo el padre
  deja huérfanos).
- Enmascarar para que no vuelva en reboot: `sudo systemctl mask zabbix-server`
  (el `disable` solo no alcanza si alguien lo levanta a mano).
- Dar de baja el motor viejo: si era MySQL (`zabbix-server-mysql`),
  `sudo systemctl disable --now mysql` (libera ~1.4 GB) una vez confirmado
  que ninguna otra app lo usa (`sudo mysql -e 'SHOW DATABASES;'`).

## 2. Una sola base

- Docker usa Postgres (`postgres:15`, red `backend`, volumen `${DATA_DIR}`).
- Confirmar que ningún conf nativo (`/etc/zabbix/zabbix_server.conf`) apunta
  a la base del container (`DBHost`/`DBName`). Dos servers contra la misma DB
  = doble polleo, tareas fantasma, estados inconsistentes.

## 3. Red persistente

- VLANs/SVs en `/etc/netplan/50-cloud-init.yaml` (Ubuntu 24.04, requiere root
  para leer). Toda ruta borrada en vivo (`ip route del`) hay que borrarla
  TAMBIÉN del yaml, si no vuelve en el próximo `netplan apply`/reboot.
- Verificar post-reboot: `ip route show` limpio + ping a cada segmento.

## 4. Boot

- `systemctl is-enabled docker` → `enabled`.
- Compose con `restart: unless-stopped` en todos los servicios.
- Unidades nativas enmascaradas (punto 1).

## 5. Acceso de gestión

- No hacer ráfagas de reintentos SSH/TCP contra el server (tienen la firma de
  un escaneo y pueden gatillar shuns temporales en el camino).
- Si el directo falla pero el salto por otro server de la misma red anda,
  es bloqueo por IP/origen en el tránsito, no caída del server. Un solo
  intento limpio cada varios minutos; el resto por el salto.

## 6. Monitoreo post-migración (primeras 48 h)

- `Administration → Queue`: sin `temporarily disabling`.
- Comparar `ps aux` dentro del container (pingers/pollers) contra el
  `zabbix_server.conf` nativo previo y replicar `StartPingers`, `CacheSize`,
  `ValueCacheSize` vía `ZBX_*` (ver Tuning en `docs/instalacion.md`).
- Revisar triggers con tormentas same-second en varios hosts a la vez: casi
  siempre es artifact o trigger ingenuo (`<>1` sin histéresis), no corte real.
- Verificar que cada LLD rule corre (delay `0` en reglas custom puede
  significar que nunca se re-ejecuta sola).


## 7. Esquema post-migración (MySQL→Postgres)

- Comparar defaults contra el esquema stock (`database/postgresql/schema.sql`
  del tarball oficial): lo de pgloader trae estructura ok pero puede soltar
  `DEFAULT`. Verificado en producción: 63 columnas afectadas.
- Tras altas por API, verificar `hosts.name_upper` (ver §9 del checklist de
  servicio).
## 8. Dashboards: backup antes de tocar por API

- `dashboard.update` REEMPLAZA páginas/widgets, no suma: un update parcial
  BORRA el resto (los cambios de dashboard no quedan en auditlog).
- Antes de cualquier mutación: exportar `configuration.export` (dashboard 1)
  o `pg_dump` de las tablas `dashboard*`/`widget*`.
- La base vieja (MySQL del host, si existe) guarda el layout original:
  `widget` + `widget_field` por `dashboard_pageid`.
- Lección 2026-09: 12 páginas borradas, reconstruidas desde logs nginx
  (`chart2?graphid=` + referrer `page=`) + base vieja. Verificar páginas
  hermanas después de cada mutación, no solo la tocada.
- Ritual obligatorio: GET completo → backup JSON con fecha → modificar →
  PUT → verificar conteo de widgets POR PÁGINA (no solo total). Los widgets
  vacíos (solo `reference`) pueden caerse en silencio en el round-trip.

## 9. Gates de migración config-only (corte 2026-09-28 a 198.51.100.38)

> La migración previa es referencia de método lab-validada solamente; estos gates se ejecutan
> exclusivamente sobre dumps y stack del sitio a migrar.

- Conteos post-migracion (tras `docker compose up -d` y auto-migracion 7000000->7040011):
  corte 2026-09-28: `hosts` habilitados **26**, `templates` **349**,
  `items` **24125**, `triggers` **9878**, `tables` **207**,
  `dbversion.mandatory` **7040000**. (Baseline previo: 32/26529/11086 por
  hosts dados de baja por el equipo — el gate compara contra fresh dump,
  no contra baseline viejo.)
  Cualquier delta sin explicacion documentada (alta/baja del equipo) => Rollback y comparar contra fresh dump.
- `Administration → Queue`: **cero items delayed >30 segundos** tras 5 min de up; preprocessing workers no saturados; sin `temporarily disabling` en `docker logs zabbix-server` (gate: `grep -c "temporarily disabling" == 0`).
- `docker compose config` gate (pre-corte y post-corte): `docker compose -f docker/docker-compose.yml config` exit 0, sin warnings de variables indefinidas, imagenes resuelven a `7.4.13`/`postgres:15`, puertos via `HTTP_BIND_IP`/`HTTPS_BIND_IP` (SSH siempre `:14422`; HTTP Fase 1 `:8080`, Fase 2 `:80/443`).
- `name_upper` tras altas por API: `SELECT host FROM hosts WHERE name_upper='';` debe dar 0 filas. Si no, `UPDATE hosts SET name_upper=upper(name) WHERE name_upper='';` antes de dar por cerrada la migracion (rompe busqueda si queda vacio).
- Repoint `Zabbix server`: `UPDATE interface SET dns='zabbix-agent', useip=0 WHERE hostid=(SELECT hostid FROM hosts WHERE host='Zabbix server') AND type=1;` — en ~2 min verificar con `SELECT i.available FROM interface i JOIN hosts h ON h.hostid=i.hostid WHERE h.host='Zabbix server' AND i.type=1;` (-> 1). Ojo 7.4: `available` vive en `interface`, no en `hosts`.
- API gate: `curl .../api_jsonrpc.php -d '{"method":"apiinfo.version"}'` -> `7.4.13`; `dbversion.mandatory` -> `7040000`; `gzip -t` OK en ambos dumps antes de pgloader; `c_sysmaps_elements_2` como unico error FK aceptado.

## 10. Validacion pre-corte — lab dry-run obligatorio

- Lab dry-run verde antes de la ventana: stremear dumps frescos del sitio por SSH :14422 al lab → MySQL temporal `mysql:8.0 --default-authentication-plugin=mysql_native_password` → pgloader `workers=4 concurrency=2` → `zabbix-server:7.4.13` → capturar `docker logs zabbix-server | grep -i "upgrade\|database"` (7000000->7040011) y conteos contra fresh dump (corte 2026-09-28: 207 tablas, 26 hosts, 349 templates, 24125 items, 9878 triggers). Gate: 0 errores pgloader salvo FK conocido, API 7.4.13, Queue limpia. Sin dry-run verde no se corta.

## 11. Triggers pgloader: la cola `changelog` (incidente site-a/site-b 2026-09-30, NO trasladar)

- pgloader trae datos pero **suelta triggers y funciones**: en site-a faltaron los 65
  triggers no-internos + 64 funciones (`SELECT count(*) FROM pg_trigger WHERE NOT
  tgisinternal` → 0; en stock/lab → 65). Comparar contra
  `create.sql.gz` de la imagen (`zabbix/zabbix-server-pgsql:alpine-7.4.13`).
- 63 de esos triggers NO son auditoría decorativa: escriben en la tabla
  `changelog` (`INSERT INTO changelog (object,objectid,operation,clock)`), que es
  **la cola por la que el syncer se entera de altas/cambios** (items→objeto 3,
  hosts→1, triggers→5, etc.). Los 2 restantes (`hosts_name_upper_*`) mantienen
  `hosts.name_upper` (ver §7/§9: búsquedas rotas si queda vacío).
- Sin triggers: la fila existe en DB (la API la lee perfecto, todo "se ve bien"),
  pero `changelog` queda vacío → el syncer nunca la carga en cache → el
  scheduler nunca la encola → el poller jamás la intenta. Síntoma exacto:
  `lastclock=0`, `state=0`, `error=""` eternos; `execute-now` muere con
  `cannot perform check now for itemid [X]: item is not in cache`; ni reload ni
  restart lo levantan. En site-a/site-b dockerizados nada creado por ~2 días fue
  agendado (descubrimientos, prototipos, items fijos, hasta un `agent.ping`
  canario), con pollers idle y cola en cero.
- Gate post-migración obligatorio (antes de dar por cerrada):
  1. `SELECT count(*) FROM pg_trigger WHERE NOT tgisinternal;` → **65**.
     Si da 0/corto: replay DDL stock (`CREATE FUNCTION public.changelog_*()` +
     `CREATE TRIGGER *_insert/_update/_delete`) en ventana y re-verificar conteo.
  2. Smoke test canario: crear 1 item trivial por API → `SELECT * FROM changelog
     ORDER BY clock DESC LIMIT 3;` debe mostrar su fila en segundos → esperar 2
     ciclos → `lastclock>0` → borrar el item. Sin fila en changelog, no cerrar.
- Si ya se operó sin triggers (caso site-a/site-b): las entidades creadas en el
  hueco nunca generaron changelog → tras el replay, hacer UN
  `config_cache_reload` (o restart en ventana) para carga completa y re-verificar
  con canario.
