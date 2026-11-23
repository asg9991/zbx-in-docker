# Observabilidad híbrida (lab)

Implementación de laboratorio del [ADR 0001](../../docs/adr/0001-observabilidad-hibrida-loki-grafana.md):
Loki para logs, Grafana para presentación, Zabbix sigue siendo el sistema de
registro de métricas y el único motor de alertas.

```
equipo de red ──syslog──▶ rsyslog ──archivo──▶ Alloy ──▶ Loki ──▶ Grafana
```

## Cómo se levanta

Override opcional: el stack Zabbix-only sigue funcionando sin esto.

```bash
cd docker
docker compose -f docker-compose.yml -f docker-compose.lab.yml \
  -f docker-compose.observability.yml --profile observability up -d
```

## Requisitos previos (una vez por sitio)

Variables nuevas en `.env` (ver `.env.example`): `SITE`, `LOKI_RETENTION`,
`LOKI_INGESTION_RATE_MB`, `LOKI_INGESTION_BURST_MB`, `LOKI_MAX_BACKLOG`,
`SYSLOG_BIND_IP`, `SYSLOG_PORT`, `RSYSLOG_RETENTION_DAYS`, `GF_ADMIN_PASSWORD`,
`GF_ZABBIX_USER`, `GF_ZABBIX_PASSWORD`, `GF_READ_TOKEN`.

`LOKI_MAX_BACKLOG` es el límite **absoluto** de antigüedad de una línea (192 h
permite la siembra de 6 días del lab). No es la ventana de drenaje tras una
caída: esa es `ingester.max_chunk_age / 2` (1 h por defecto).

`GF_READ_TOKEN` es un token de **service account con rol `Viewer`**, no la
cuenta admin: lo usan `digest.py`, `preguntar.py` y `check_all.sh` para leer
logs y dashboards. Se crea una vez por sitio:

```bash
# con la cuenta admin de Grafana (una sola vez)
curl -u admin:"$GF_ADMIN_PASSWORD" -H 'Content-Type: application/json' \
  -d '{"name":"digest-reader","role":"Viewer"}' \
  http://127.0.0.1/grafana/api/serviceaccounts
# tomar el id de la respuesta y crear el token:
curl -u admin:"$GF_ADMIN_PASSWORD" -H 'Content-Type: application/json' \
  -d '{"name":"digest"}' \
  http://127.0.0.1/grafana/api/serviceaccounts/<id>/tokens
# el campo "key" de la respuesta va en GF_READ_TOKEN del .env (no se versiona)
```

Directorios de datos y dueño: cada imagen corre con su propio UID y no puede
escribir un directorio creado por root.

```bash
D=/opt/monitoring/data   # DATA_DIR del sitio
mkdir -p "$D"/{loki,grafana,rsyslog,alloy}
chown -R 10001:10001 "$D/loki"     # loki
chown -R 472:0      "$D/grafana"   # grafana
chown -R 101:102    "$D/rsyslog"   # rsyslog (uid syslog del contenedor)
# alloy corre como root (imagen sin usuario propio) y escribe su WAL ahí.
```

Usuario Zabbix de solo lectura para el datasource: crearlo en el sitio con
permisos mínimos (rol `User role`) y cargar su contraseña en
`GF_ZABBIX_PASSWORD`. Sin esto, el datasource Zabbix responde error de
autenticación.

Además hace falta un **token de API** de ese mismo usuario para el datasource
`Zabbix API` (plugin Infinity), que es el que permite armar tablas en español
con `problem.get`/`trigger.get`:

```bash
# como Admin, con la API de Zabbix:
# 1) token.create {userid: <grafana-ro>, name: "grafana-infinity", status: 0}
# 2) token.generate [<tokenid>]  -> devuelve el token una sola vez
# 3) cargarlo en ZBX_API_TOKEN del .env del sitio
```

El token es de solo lectura (mismo usuario y rol) y no se versiona.

## Qué se verificó en el lab

| Prueba | Resultado |
| --- | --- |
| `docker compose config` | válido |
| Syslog UDP y TCP a `127.0.0.1:1514` | archivo diario en `DATA_DIR/rsyslog` |
| Parseo y etiquetas en Loki (`job`, `host`, `facility`, `severity`, `site`) | correcto |
| Logs de contenedor del stack | llegan con `job="docker"` |
| Loki caído 15 s + 5 líneas | 5/5 recuperadas al volver, sin pérdida ni duplicado |
| WAL de Alloy habilitado | entrada durable al llegar al colector (no al enviarse) |
| Datasource Loki en Grafana | `Data source successfully connected` |
| Dashboard `lab-hybrid` | provisionado; panel Loki devuelve datos |
| Datasource Zabbix | OK con usuario `grafana-ro` (read-only, rol User role) |
| Datasource Zabbix API (Infinity) | health OK; tabla de problemas en español con `trigger.get` |
| Grafana por nginx en `/grafana/` | health 200, login 200, dashboard 200 |

## Gotchas verificados

- **Docker no publica puertos de un contenedor en una red `internal`.** Por
  eso rsyslog va en `frontend`: es el único servicio que debe escuchar desde
  afuera.
- **`loki.source.file` con un glob sin coincidencias al arrancar no
  reintenta**: la fuente se descarta y queda ciega. Se usa `local.file_match`,
  que re-evalúa cada 10 s.
- **El volumen de Grafana tapa el plugin horneado.** El plugin se instala en
  `/opt/grafana-plugins` (`GF_PATHS_PLUGINS`), no en `/var/lib/grafana`.
- **Loki rechaza timestamps futuros.** Un equipo con reloj adelantado pierde
  sus logs ("timestamp too new"). NTP en los equipos de origen no es opcional.
- **El tope de ingesta limita el drenaje del buffer.** Tras un corte, Alloy
  empuja el atraso en ráfaga; con `ingestion_rate_mb` demasiado bajo el atraso
  no drena. Dimensionarlo con el volumen real del sitio.
- **La ventana de drenaje es ~1 h, no la retención.** Loki acepta entradas
  desordenadas solo dentro de `ingester.max_chunk_age / 2` (1 h con el default
  de 2 h). Una caída más larga termina en 400 `entry too far behind` y Alloy
  descarta el lote. El archivo de rsyslog de 7 días sirve para inspección, no
  para drenar a Loki.
- **UDP puede perder en ráfaga** antes de llegar al proceso. Usar TCP donde el
  equipo lo soporte; subir `net.core.rmem_max` en el host.
- **El `:ro` del socket de Docker no limita la API**, solo el filesystem:
  Alloy puede hablar con el daemon. Es una frontera de confianza deliberada;
  si molesta, poner un socket proxy delante.
- **El WAL de Alloy exige `--stability.level=experimental`** en v1.22.0. Si se
  quita, el buffer de archivo sigue cubriendo caídas de Alloy/Loki; solo se
  pierde la ventana de crash sucio.
- **`syslog_tag` no es etiqueta**: en Linux puede llevar el PID y dispara la
  cardinalidad. Va en el texto de la línea.

## Dos niveles de presentación (ADR D9)

| Carpeta | Para quién | Contenido |
| --- | --- | --- |
| **Cliente** → *Estado del servicio* | Cliente y gerencia | Problemas graves, avisos y equipos caídos; tabla de problemas con antigüedad; eventos por gravedad (24 h) y últimos avisos. Sin selector de tiempo |
| **Tecnico** → *Tecnico - observabilidad y logs* | Técnicos | Logs completos, métricas por host de Zabbix, catálogo de consultas para Explore |
| **Cliente** → *Red y capacidad* | Cliente | Tráfico por equipo, CPU, memoria y disco con gauges |
| **Tecnico** → *Problemas* | Técnicos | Tablas separadas por gravedad (Alta/Desastre y Media/Aviso) |
| **Tecnico** → *Eventos de red* | Técnicos | Logs filtrados por severidad |
| **Tecnico** → *Mapa de red* | Técnicos | Uno o más mapas generados desde `maps/*.yml`, con iconos y color por estado (ver `docs/mapas-red.md`) |
| **Tecnico** → *Salud del monitoreo* | Técnicos | Items sin datos, equipos sin respuesta, cola de Zabbix |
| **Cliente** → *Estado de servicios* | Cliente | Un panel por servicio crítico: OK / Degradado / Crítico. Un problema sin clase conocida nunca deja el servicio en verde si su severidad es Alta o superior |
| **Cliente** → *Capacidades* | Cliente | Gauges de disco, CPU y memoria por grupo de equipos |
| **Tecnico** → *Mapa - núcleo y servidores* | Técnicos | Segundo mapa del mismo sitio (mismo generador) |
| **Tecnico** → *Equipo* | Drill-down | Problemas y logs de un equipo (se llega desde el mapa) |

El nivel de servicio no nombra componentes ni consultas: son tres semáforos,
una lista de problemas en lenguaje llano y una tendencia. Lo avanzado está
detrás de una fila colapsada **Para tecnicos (avanzado)** con el enlace a
Explore y las consultas listas.

### Acceso por sitio

Cliente y técnico pueden ver ambas carpetas: no se restringe. Lo que se
cuida es que la vista de servicio sea la puerta de entrada y quede a un clic
de la técnica. Restringir `Tecnico` con permisos de carpeta es una opción por
sitio, no un requisito.

1. Crear los usuarios necesarios en Grafana (el cliente con rol `Viewer`).
2. `GRAFANA_ROOT_URL` con el nombre real del sitio.

## Acceso en el lab

- URL: `http://127.0.0.1/grafana/` (sale por nginx, no publica puerto propio).
- Usuario admin: `admin`, contraseña en `GF_ADMIN_PASSWORD` del `.env` del sitio.
- Vista cliente: `/d/estado-servicio`.
- Vista técnica: `/d/tecnico-observabilidad`.
- Explore: `{job="syslog"}` para equipos, `{job="docker"}` para el stack.

## Pendiente

- Criterio de aceptación 9 completo del ADR (corte de 15 min) y D24.
- Drill de restauración de Grafana probado (el respaldo ya es consistente:
  `sudo scripts/backup_observability.sh`).
- En un cliente: usuario Zabbix de solo lectura propio, service account de
  Grafana (`GF_READ_TOKEN`) y `GRAFANA_ROOT_URL` con el nombre real del sitio.

## Navegación

Todos los dashboards llevan el mismo menú **Navegación** (desplegable armado por
la etiqueta `nav`). Para que un dashboard aparezca, alcanza con ponerle esa
etiqueta; para normalizar todo:

```bash
python3 scripts/nav_links.py          # aplica
python3 scripts/nav_links.py --check  # verifica
```

## Set de dashboards por cliente

Los dashboards son **archivos**: el repo del cliente incluye solo los que
aplican y ese es su set. No hay dashboards "ocultos por permisos".

- La **carpeta** define dónde se provisiona; la **etiqueta** define el menú:
  `nav` + `cliente`, `tecnico` o `mapa`.
- Un cliente sin mapas: no incluye `maps/*.yml` ni los `mapa-*.json`.
- Un cliente sin servicios de negocio definidos: no incluye `servicios.yml`.
- Los generadores son por sitio (`gen_map.py`, `gen_servicios.py`); el resto de
  los dashboards es genérico.

Verificación: `bash scripts/check_all.sh` recorre los dashboards presentes.
