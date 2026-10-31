# Reactivar el monitoreo Proxmox en Zabbix (host 10817)

> **Estado**: pendiente de verificación. Los técnicos están haciendo migraciones
> en Proxmox; aplicar recién cuando el cluster esté quieto.
> **Origen**: task #64 del diario (proyecto site-a), 2026-10-21.
> **Alcance**: solo el host Zabbix `Proxmox` (hostid 10817), que monitorea el
> cluster Proxmox por HTTP. **No** incluye los hosts `PBS-NODE` (10882) y
> `pbs.example.com` (10883), que son los agentes internos de los servidores
> Proxmox del PBS y ya están funcionando.

## 1. Qué está roto

El host `Proxmox` (10817) tiene **546 de 549 items en estado "not supported"**.
Zabbix deja de consultar los items no soportados → el error queda congelado en
la UI y el descubrimiento (LLD) no vuelve a correr: no se descubren VMs nuevas
y las gráficas de VMs quedan sin actualizar.

Los dos errores que se ven son **cosas distintas**:

| Error visible | Origen real |
|---|---|
| `Preprocessing failed for: Error getting data. Failed: cannot extract value from json by path "$.data.[?(@.name == 'CLUST01' ...)]..."` | El master `proxmox.cluster.resources` (113306) tiene un paso de preprocesamiento `VALIDATE_NOT_SUPPORTED` con on-fail `SET_VALUE 'Error getting data'` y `history=0`. Cuando su request falla, **no registra el error real**: escribe ese string como valor. El master queda con `state=0` y sin error (parece sano) y los dependientes reciben el string → el JSONPath falla. Con `history=0` además se borra la evidencia |
| `Cannot perform request: Failed to connect to 192.0.2.4:8006 after 0 ms: Could not connect to server` | El error **real** del master, congelado en los items que no tienen el paso de enmascaramiento |

## 2. Diagnóstico (verificado 2026-10-21)

- **La API de Proxmox responde.** Desde el container `zabbix-server`, con el
  token del host (`{$PVE.TOKEN.ID}` / `{$PVE.TOKEN.SECRET}`), responden
  `/api2/json/version`, `/api2/json/cluster/resources`,
  `/api2/json/cluster/status` y `/api2/json/nodes/nodo1/qemu/100/status/current`
  con JSON válido. 50 requests simultáneos → 50 OK.
- **El problema es de confianza TLS.** El nodo sirve un certificado
  `CN=nodo1.example.com` firmado por la CA privada del cluster Proxmox
  (`CN=Proxmox Virtual Environment, OU=44e4525b-...`), que:
  - no está en el trust store del container
    (`/etc/ssl/certs/ca-certificates.crt` → solo CAs públicas),
  - no se sirve en la cadena TLS (el servidor envía solo su certificado).
- **En Zabbix 7.4 los items HTTP ya no exponen `verify_peer`/`verify_host`**
  (las columnas quedan legacy y el objeto del item no las expone) → no hay
  forma de desactivar la verificación por item. **La CA es la única palanca.**
- Prueba concluyente: un item HTTP **nuevo**, creado con la misma URL y el
  mismo token, falla **idéntico** a los viejos, mientras `curl`/`wget` desde el
  mismo container, mismo netns y misma ruta funcionan.
- Último dato bueno del master `proxmox.api.available`: **04:53** del 21/10.
  El stack se recreó el **2026-10-01 19:48 UTC (= 16:48 local)**, momento
  exacto en que empezaron los `OpenSSL SSL_read: unexpected eof` (pveproxy
  cortando la conexión) → los items quedaron "not supported" y congelados.
- El mismo síntoma aparece en otra instancia (memoria #196: "transient Proxmox
  8006 TCP failures").

## 3. Procedimiento tentativo de reactivación

### Paso 0 — Precondiciones

- Cluster Proxmox quieto (sin migraciones en curso).
- Back up del estado actual:
  ```bash
  docker exec zabbix-postgres pg_dump -U zabbix -d zabbix > /tmp/pre-reactivacion-$(date +%F).sql
  ```
- Identificar el token/API en uso: `hostmacro` del host 10817
  (`{$PVE.URL.HOST}` = `192.0.2.4`, `{$PVE.URL.PORT}` = `8006`,
  `{$PVE.TOKEN.ID}`, `{$PVE.TOKEN.SECRET}`).

### Paso 1 — Obtener la CA del cluster Proxmox

En **cualquier nodo** del cluster (no desde el server Zabbix):

```bash
# en el nodo Proxmox (192.0.2.4)
cat /etc/pve/nodes/nodo1/pveproxy-ssl.pem
```

El **primer** certificado del archivo es la CA del cluster
(`CN=Proxmox Virtual Environment, OU=44e4525b-...`). Guardarlo en el server:

```bash
# en el host del server Zabbix
sudo mkdir -p /opt/monitoring/data/certs/proxmox
# (copiar el primer bloque -----BEGIN CERTIFICATE----- ... -----END CERTIFICATE-----)
sudo tee /opt/monitoring/data/certs/proxmox/proxmox-cluster-ca.crt
```

> La CA del cluster se renueva cuando se renuevan los certificados de los
> nodos. Guardar el archivo **fuera** del container (en `DATA_DIR`) y
> bind-montarlo evita rehacer esto en cada recreacion.

### Paso 2 — Montar la CA en el container (persistir)

`docker/docker-compose.yml`, servicio `zabbix-server`, sección `volumes`:

```yaml
    volumes:
      - ../scripts:/usr/lib/zabbix/externalscripts:ro
      - ../data/certs/proxmox:/usr/local/share/ca-certificates/proxmox:ro
```

La imagen es `zabbix/zabbix-server-pgsql:alpine-7.4.16` (Alpine): las CAs se
instalan con `update-ca-certificates` desde `/usr/local/share/ca-certificates/`.

### Paso 3 — Recrear el container y regenerar el trust store

```bash
cd /opt/monitoring/zbx-in-docker/docker
docker compose up -d --force-recreate zabbix-server
# dentro del container: regenerar el bundle
docker exec -u 0 zabbix-server update-ca-certificates
# verificar que la CA de Proxmox quedó en el bundle
docker exec zabbix-server sh -c 'grep -c "BEGIN CERTIFICATE" /etc/ssl/certs/ca-certificates.crt'
```

> Si `update-ca-certificates` no está en el PATH de la imagen Alpine, usar
> `docker exec -u 0 zabbix-server sh -c 'cat /usr/local/share/ca-certificates/proxmox/*.crt >> /etc/ssl/certs/ca-certificates.crt'`
> (append manual, suficiente para cURL/OpenSSL).

### Paso 4 — Verificar que la API ahora se puede leer desde Zabbix

Crear un item HTTP de prueba (mismo formato 7.4: los headers van en el array
`headers`, no en `authentication`):

```json
{"hostid":"10817","name":"ZZ-TEST proxmox","key_":"zz.test.http","type":19,
 "url":"https://192.0.2.4:8006/api2/json/version","delay":"1m","timeout":"30s",
 "headers":[{"name":"Authorization","value":"PVEAPIToken={$PVE.TOKEN.ID}={$PVE.TOKEN.SECRET}"}],
 "value_type":4,"status_codes":"200"}
```

Si devuelve `200` → seguir. Si sigue `Failed to connect ... after 0 ms` → el
problema no es la CA: para el diagnóstico.

### Paso 5 — Re-activar los items congelados

```bash
# via API (token del usuario): volver a habilitar los items not-supported
#   -> item.update status=0 y forzar re-chequeo con task.create type 6
```

Con los items re-activados, la LLD vuelve a correr y se redescubren las VMs
(las que dejaron de aparecer: los items "not discovered anymore" se borran
según `lifetime`).

### Paso 6 — Verificar

- `docker logs zabbix-server | grep -i proxmox` → sin "Failed to connect".
- Items del host 10817 con `state=0` y `lastclock` reciente.
- LLD de VMs corriendo: aparecen items `proxmox.qemu.get.data[qemu/NNN]`.
- Gráficas de VMs con datos nuevos.
- El master `proxmox.api.available` vuelve acollectar (value distinto de "200").

## 4. Recomendación adicional (evita el próximo diagnóstico a ciegas)

El enmascaramiento del master es lo que hizo este problema invisible durante
19 días. Dos cambios posibles en el template `Proxmox VE by HTTP` (10517) o en
los items del host:

- Quitar el paso `VALIDATE_NOT_SUPPORTED` con `SET_VALUE 'Error getting data'`
  del master `proxmox.cluster.resources` → el error real del request queda
  visible en el item y en sus dependientes.
- O al menos poner `history > 0` en ese master → se conserva la evidencia del
  último fallo (hoy `history=0` la borra).

## 5. Rollback

- Revertir el compose (quitar el volume de la CA) y recrear el container.
- Los items se pueden volver a dejar como estaban (not-supported) sin
  consecuencias: la LLD no corre y no se descubren VMs, que es el estado
  actual.
- Restaurar la DB con el pg_dump del Paso 0 si se tocaron items de forma
  masiva.

## 6. Lo que NO hacer

- **No** asignar el template `Proxmox Backup NODE via HTTP` (10836) a ningún
  host: su token de API expiró y sus items de agente son pasivos (chocan con
  el template de agente activo).
- **No** borrar los hosts `PBS-NODE` (10882) ni `pbs.example.com` (10883):
  son los agentes de los servidores Proxmox del PBS, funcionan y mantienen el
  log sin ruido.
