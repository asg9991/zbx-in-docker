# UniFi Monitoring - External Check

## Objetivo

Obtener información de dispositivos UniFi mediante API y procesarla en Zabbix utilizando un External Check.

---

## Arquitectura

```text
UniFi Controller
        ↓
unifi_dump.py
        ↓
External Check (Zabbix)
        ↓
Master Item (JSON)
        ↓
Dependent Items
```

---

## Ubicación del script

Host:

```text
/opt/monitoring/scripts/externalscripts/unifi_dump.py
```

Contenedor:

```text
/usr/lib/zabbix/externalscripts/unifi_dump.py
```

Montaje Docker:

```yaml
volumes:
  - ../scripts/externalscripts:/usr/lib/zabbix/externalscripts:ro
```

---

## Imagen personalizada de Zabbix Server

La imagen oficial no incluye Python.

Se creó una imagen derivada:

Archivo:

```text
docker/Dockerfile.zabbix-server
```

Contenido:

```dockerfile
FROM zabbix/zabbix-server-pgsql:alpine-7.0.6

USER root

RUN apk add --no-cache \
    python3 \
    py3-pip \
    py3-requests

USER zabbix
```

Docker Compose:

```yaml
zabbix-server:
  build:
    context: .
    dockerfile: docker/Dockerfile.zabbix-server

  image: site-c/zabbix-server:7.0.6
```

---

## Variables de entorno

Definidas en `.env`:

```env
UNIFI_URL=https://192.0.2.40
UNIFI_USER=admin
UNIFI_PASS=CHANGE_ME
```

Configuradas en `docker-compose.yml`:

```yaml
environment:
  UNIFI_URL: ${UNIFI_URL}
  UNIFI_USER: ${UNIFI_USER}
  UNIFI_PASS: ${UNIFI_PASS}
```

---

## Script Python

Shebang utilizado:

```python
#!/usr/bin/python3
```

No utilizar:

```python
#!/usr/bin/env python3
```

ya que provocó errores de ejecución desde Zabbix External Check.

---

## Verificaciones

Validar Python:

```bash
docker exec -it zabbix-server python3 --version
```

Validar requests:

```bash
docker exec -it zabbix-server python3 -c "import requests; print(requests.__version__)"
```

Validar script:

```bash
docker exec -it zabbix-server \
/usr/lib/zabbix/externalscripts/unifi_dump.py
```

---

## Observaciones

- El script devuelve el JSON completo de UniFi.
- Los datos son procesados mediante Items Dependientes.
- Las credenciales se obtienen desde variables de entorno.
- Los scripts personalizados permanecen fuera del contenedor y son persistentes mediante bind mount.
