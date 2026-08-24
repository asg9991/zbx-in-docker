# Guía de instalación

Instalación del stack de monitoreo con Docker Compose, incluyendo cómo asignar
credenciales y contraseñas antes del primer arranque.

## Requisitos

- Docker Engine 24+ con Docker Compose v2 (`docker compose version`)
- Puertos libres en el host: **80** (nginx) y **10051** (trapper de Zabbix)
- ~2 GB de RAM disponibles para los contenedores

## Paso 1 — Obtener el repositorio

```bash
git clone <url-del-repo>
cd noc-agent
```

## Paso 2 — Crear el archivo de entorno (credenciales)

El stack **no arranca sin credenciales**: todas las contraseñas se resuelven
desde `docker/.env`, un archivo que vive junto al `docker-compose.yml` y está
gitignored (nunca se commitea).

```bash
cp .env.example docker/.env
```

Generar una contraseña segura y completarla en el archivo:

```bash
openssl rand -base64 18
```

### Variables del entorno

| Variable            | La consume                          | Descripción                                        |
| ------------------- | ----------------------------------- | -------------------------------------------------- |
| `POSTGRES_DB`       | postgres, zabbix-server, zabbix-web | Nombre de la base de datos de Zabbix               |
| `POSTGRES_USER`     | postgres, zabbix-server, zabbix-web | Usuario de la base de datos                        |
| `POSTGRES_PASSWORD` | idem                                | Contraseña de la base — **única credencial real**  |
| `TZ`                | zabbix-web                          | Timezone del frontend PHP                          |
| `SERVER_IP`         | integraciones (macros)              | IP pública/referencia del server                   |
| `DATA_DIR`          | volúmenes del compose               | Base de datos persistentes (ver abajo)             |

### Dónde vive cada contraseña

1. **Único punto de verdad:** `docker/.env` (local al host, fuera de git).
2. Compose inyecta las variables a cada servicio vía `env_file` / `environment`.
3. **PostgreSQL solo usa `POSTGRES_PASSWORD` en el primer inicio** (cuando
   inicializa el volumen). Si el volumen ya existe, cambiar el `.env` NO rota
   la contraseña real.
4. Rotación sobre un volumen existente:

   ```bash
   docker compose exec postgres psql -U zabbix -d zabbix \
     -c "ALTER USER zabbix WITH PASSWORD 'nueva-password';"
   ```

   Luego actualizar `POSTGRES_PASSWORD` en `docker/.env` para que quede
   sincronizado.

### Persistencia

Los datos viven bajo `DATA_DIR`. Por defecto es `/opt/monitoring/data`
(pensado para servidor); en lab local conviene apuntarlo a un directorio del
proyecto o del home:

```bash
DATA_DIR=/home/usuario/ruta/del/lab/data
```

## Paso 3 — Levantar el stack

```bash
cd docker
docker compose up -d --build
```

El build extiende la imagen oficial de Zabbix Server con Python 3 y
`requests` (External Checks).

## Paso 4 — Verificar

```bash
docker compose ps                      # todos Up, postgres healthy
curl -s http://127.0.0.1/api_jsonrpc.php \
  -H 'Content-Type: application/json-rpc' \
  -d '{"jsonrpc":"2.0","method":"apiinfo.version","params":{},"id":1}'
# → {"jsonrpc":"2.0","result":"7.4.13","id":1}
```

Frontend: `http://localhost` — usuario por defecto `Admin` / `zabbix`.
**Cambiar esa contraseña en el primer login.**

## Datos simulados (solo lab, Fase 1 NOC Agent)

Un simulador alimenta 4 hosts falsos con métricas trapper y ventanas de
incidente cíclicas, para tener **problemas reales que consultar** desde el
agente. Nunca arranca en producción: vive detrás del profile `lab` de Compose.

**1. Crear template, host group y hosts (idempotente):**

```bash
export ZABBIX_URL=http://127.0.0.1/api_jsonrpc.php
export ZABBIX_USER=Admin
export ZABBIX_PASSWORD='tu-password'
python3 scripts/bootstrap_lab_sim.py
```

**2. Levantar el simulador (el compose vive en `docker/`):**

```bash
cd docker
docker compose --profile lab up -d lab-simulator
docker logs -f lab-simulator   # cada envío queda logueado
```

**3. Qué esperar:** a los ~3-4 min aparecen los primeros problemas en
*Monitoring → Problems*: CPU alta (`olt-sim-01`), pérdida de paquetes + latencia
(`router-sim-02`) y flaps de link (`ap-sim-04`). A los ~11 min el disco de
`server-sim-03` cruza el umbral y queda lleno (problema persistente, no se
resuelve solo).

Los escenarios (frecuencia, duración y valores de cada incidente) se editan en
`docker/simulator/scenarios.yml` — tomar efecto requiere recrear el contenedor:
`docker compose --profile lab up -d --force-recreate lab-simulator`.
Los umbrales de disparo viven en `templates/template_lab_simulado.yaml`.

## Redes internas

El stack define sus propias redes autocontenidas (no dependen de redes
externas precreadas):

| Red        | Subred           | Uso                                    |
| ---------- | ---------------- | -------------------------------------- |
| `backend`  | `172.28.90.0/24` | Postgres ↔ Zabbix (sin salida a internet) |
| `frontend` | `172.28.91.0/24` | nginx → zabbix-web → trapper           |

Las subredes son explícitas para no colisionar con otros proyectos Docker ni
con redes corporativas típicas (`10.x`, `192.168.x`, rangos bajos de
`172.16.x`).

## Gotcha: VPN corporativa activa

Si una VPN del estilo strongSwan instala una ruta por defecto en una tabla de
policy routing (ej. `table 220`), todo tráfico hacia rangos privados deja de
llegar a los bridges de Docker desde el host: los `curl` cuelgan aunque los
contenedores estén sanos.

Síntoma rápido:

```bash
ip rule show        # ¿hay reglas previas a main? (ej. prioridad 220)
ip route show table 220
```

Workaround mientras la VPN esté activa (una regla por subred del lab):

```bash
sudo ip rule add to 172.28.90.0/24 lookup main priority 100
sudo ip rule add to 172.28.91.0/24 lookup main priority 100
```

La solución durable pertenece al script `updown.sh` de la VPN (excluir las
subredes del lab del secuestro de rutas).

## Actualizar la versión de Zabbix

1. Bump de tags en dos lugares:
   - `docker/docker-compose.yml` → imagen de `zabbix-web` (`alpine-7.4.X`)
   - `docker/Dockerfile.zabbix-server` → `FROM` base (`alpine-7.4.X`)
2. `docker compose up -d --build`
3. Al arrancar, Zabbix Server **migra el esquema de la base automáticamente**
   a la versión nueva. El downgrade NO está soportado: hacer backup de
   `${DATA_DIR}/postgres` antes de saltar de versión.
