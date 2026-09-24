# Checklist de salud zbx-in-docker (pre-servicio / post-reboot / post-cambio)

Corre en el host, en este orden. Todo tiene que dar verde antes de cantar
victoria. Tiempos: ~5 min.

## 1. Un solo mundo (nativo muerto)

```bash
# Cero procesos fuera de docker (el truco cgroup; pgrep solo MIENTE porque
# container y nativo se llaman igual):
for p in $(pgrep -f 'zabbix_server:|mysqld|php-fpm'); do
  tr '\0' ' ' < /proc/$p/cmdline 2>/dev/null | grep -q 'pgrep\|for p in' && continue
  grep -qa docker /proc/$p/cgroup 2>/dev/null || echo "HOST-PROC: $p"
done
# Esperado: solo pools php-fpm si existen... ideal: nada salvo tu propio shell.
# Si aparece algo: matar + enmascarar la unidad (systemctl mask <unidad>).

systemctl is-enabled zabbix-server nginx mysql docker
# Esperado: masked, masked, disabled (o masked), enabled
```

## 2. Stack (docker)

```bash
sudo docker ps --format '{{.Names}}|{{.Status}}'
# Esperado: los 5 Up; postgres y web con (healthy).
# OJO: "Up" en zbx-nginx no alcanza — si reinicia en loop, ver punto 3.

sudo docker inspect zabbix-server zabbix-postgres zabbix-web zbx-nginx zabbix-agent \
  --format '{{.Name}} restarts={{.RestartCount}}'
# Esperado: 0 (post-boot). Si alguno suma restarts, leer su log.
```

## 3. Web de verdad (no solo Up)

```bash
curl -sk -o /dev/null -w 'front %{http_code}\n' https://127.0.0.1/
curl -sk https://127.0.0.1/api_jsonrpc.php -H 'Content-Type: application/json-rpc' \
  -d '{"jsonrpc":"2.0","method":"apiinfo.version","params":{},"id":1}'
# Esperado: front 200 + {"result":"7.4.x"}.
# Trampas vistas:
#  - exit 128 + "address already in use" = nginx nativo robó el 80/443
#    → stop+mask nativo, `docker compose up -d --force-recreate nginx`.
#  - "host not found in upstream zabbix-web" en loop = container con red
#    corrupta → NO sirve `docker start`; recrear con compose.
```

## 4. Datos fluyendo (no solo procesos)

```sql
-- Cola (vía API Latest data o DB):
--   zabbix[queue] < 100 y zabbix[queue,10m] = 0
--   zabbix[preprocessing_queue] ~ 0
-- Problemas abiertos con sentido:
select t.description, h.host, count(*) from problem p
join triggers t on t.triggerid=p.objectid
join functions f on f.triggerid=t.triggerid
join items i on i.itemid=f.itemid
join hosts h on h.hostid=i.hostid
where p.source=0 and p.r_eventid is null group by 1,2 order by 3 desc;
-- Esperado: solo fallas reales de equipos (puertos con nombre, fibers).
-- Sospechoso: N problemas mismo-segundo en varios hosts = artifact/trigger.
-- Verificar un gráfico testigo por nodo (ej. MKT 601 - All VLANs) con datos
-- de los últimos 15 min.
```

## 5. Disco y backups (rollback mínimo)

```bash
df -h /opt/monitoring   # < 80%
ls -la /opt/monitoring/zbx-in-docker/docker/.env*
# .env existe + .bak previo a cada cambio de tuning.
ls -la /opt/monitoring/bkp-pre-docker/
# Existen dumps pre-docker (2026-09-12/14): config + full + schema.
# ANTES de cada cambio gordo, sumar un pg_dump fresco de la base ACTUAL:
```

Rollback mínimo antes de CUALQUIER cambio (tuning, template, upgrade):

```bash
cd /opt/monitoring/zbx-in-docker/docker
cp .env .env.bak.$(date +%Y%m%d_%H%M%S)
sudo docker exec zabbix-postgres pg_dump -U zabbix zabbix \
  | gzip > /opt/monitoring/pg-backup-$(date +%Y%m%d_%H%M%S).sql.gz
```

Restaurar = `docker compose down`, volver `.env`, `pg_restore`/recrear
volumen desde el dump, `docker compose up -d`. Sin dump no hay rollback.

## 6. Red persistente (post-reboot sí o sí)

```bash
ip route show | grep -E '198.51.100.0|192.0.2.60'   # sin "via 192.0.2.60"
ping -c2 198.51.100.212; ping -c2 192.0.2.60; ping -c2 203.0.113.11
```

## 7. Acceso de gestión

- Probar directo Y por salto (`-J`). Si el directo falla y el salto anda,
  es bloqueo por origen en el tránsito: un intento limpio cada varios
  minutos, NUNCA ráfagas (parecen escaneo y alargan el shun).

## 8. Item nuevo que no grafica (caché de config)

Si un item recién creado (estado 0, sin error) no recibe datos en 5 min
(`item_rtdata.mtime` en epoch) mientras el resto sí:

```bash
sudo docker exec zabbix-server zabbix_server -R config_cache_reload
# esperar 3 min; si sigue igual:
sudo docker restart zabbix-server   # reconstruye la caché (gap ~1 min)
```

Visto post-era-dos-servers: la caché quedaba sorda a inserts nuevos hasta el
restart. Verificar con `mtime` del item, no con "Up" del container.

## 9. Host nuevo invisible en búsquedas (name_upper)

Tras crear un host por API/frontend, verificar:

```sql
select hostid from hosts where name_upper='' or name_upper is null;
-- Si aparece: UPDATE hosts SET name_upper = UPPER(name) WHERE ...;
```

En esta instancia la API no rellena `name_upper` (columna que usa el
buscador) y el host existe pero no filtra. Solo afecta altas nuevas.

