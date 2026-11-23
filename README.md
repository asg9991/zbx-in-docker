# zbx-in-docker

Stack Zabbix en Docker (server 7.4 + web + postgres 15 + nginx).

Stack de monitoreo basado en tecnologías Open Source para infraestructura de red, servidores y servicios.

## Componentes

- Zabbix Server 7.4 LTS
- Zabbix Web
- PostgreSQL 15
- Nginx Reverse Proxy

---

# Arquitectura

```
                +------------------+
                |      Nginx       |
                +--------+---------+
                         |
                +--------v---------+
                |    Zabbix Web    |
                +--------+---------+
                         |
                +--------v---------+         +---------------+
                |  Zabbix Server   +<=======>+   PostgreSQL  |
                +----+--------+----+         +---------------+
                     |        |
          SNMP / ICMP         External Checks (Python)
                |                    |
         Equipos de red    +---------v----------+
                           | UniFi Network API  |
                           +---------+----------+
                                     |
                           +---------v----------+
                           |  UniFi Controller  |
                           +--------------------+
```

---

# Funcionalidades implementadas

## Monitoreo de infraestructura

- Monitoreo mediante SNMP
- Monitoreo ICMP
- Descubrimiento automático
- Triggers

## Integración UniFi Network

Integración nativa con la API de UniFi Network para obtener información que no está disponible mediante SNMP.

Características implementadas:

- Autenticación mediante UniFi Network API
- Descubrimiento automático de Access Points (LLD)
- Master Item basado en JSON
- Dependent Items
- Monitoreo de clientes conectados
- Estado del Access Point
- Versión de firmware
- Tráfico RX/TX
- Template reutilizable mediante macros de Zabbix

---

# Personalizaciones

## Zabbix Server

La imagen oficial de Zabbix Server fue extendida para incluir:

- Python 3
- Requests

Esto permite ejecutar External Checks desarrollados en Python.

---

# Estructura del proyecto

```
docker/
docs/
scripts/
templates/
```

### scripts/

```
scripts/

├── externalscripts/
│   └── unifi.py
│
└── unifi/
    ├── __init__.py
    ├── unifi.py
    └── unifi_api.py
```

---

# Documentación

La documentación técnica se encuentra en el directorio `docs`.

- **Instalación y operación:** `instalacion.md`, `checklist-servicio.md`,
  `recupero.md`, `migracion-checklist.md`
- **Agentes:** `zabbix-agent-linux.md`, `zabbix-agent2-docker.md`
- **Proxmox:** `proxmox-monitoreo.md`, `proxmox-monitoreo-tls.md`
- **Red y servicios:** `unifi-external-check.md`
- **Alertas y reportes:** `telegram-usuarios.md`, `telegram-es-i18n.md`,
  `reportes-automaticos.md`
- **TLS:** `tls-cloudflare-origin.md`, `tls-letsencrypt-direct.md`
- **Zabbix UI/DB:** `dashboard-update.md`
- **NOC Agent / MCP:** `mcp-spike-fase2.md`, `noc-agent/`
- **Seguridad:** `seguridad-secretos.md`
- **Decisiones de arquitectura:** `adr/`
- **Observabilidad (lab):** `docker/observability/README.md` — Loki, Grafana,
  Alloy y receptor syslog (ADR 0001)
- **Plan de dashboards para clientes:** `observabilidad-demo.md` — análisis,
  catálogo de dashboards y tareas
- **Alta de hosts y métricas:** `agregar-host.md` — procedimiento y verificaciones
- **Bitácora técnica:** `lecciones-observabilidad.md` — síntoma, causa y solución por componente
- **Mantenimiento:** `mantenimiento-observabilidad.md` — versiones, riesgos, backups y qué es Infinity
- **Riesgos y alternativas:** `riesgos-y-alternativas.md` — costo de mantenimiento de cada pieza
- **Mapas de red:** `mapas-red.md` — prompt, generación y varios mapas por cliente
- **Clases de incidente:** `clases-de-incidente.md` — catálogo y servicios críticos (D9/D10)
- **Servicios críticos:** `scripts/gen_servicios.py` — genera el dashboard desde `servicios*.yml`
- **Digest (fase N):** `contrato-digest.md` + `digest.py` (armar), `notify_digest.py` (enviar) y `preguntar.py` (consultar)
- **Evaluación del clasificador (N6):** `scripts/evaluar_clasificador.py` + `tests/fixtures/incidentes.yaml`
- **Revisión de coherencia:** `revision-coherencia.md` + `scripts/check_all.sh`
- **Respaldo y restauración:** `respaldo-observabilidad.md` + `scripts/backup_observability.sh`
- **Roadmap:** `ROADMAP.md`

---

# Estado del proyecto

## Finalizado

- Docker Compose
- PostgreSQL
- Zabbix Server
- Zabbix Web
- Nginx Reverse Proxy
- Integración con UniFi Network API
- Descubrimiento automático de Access Points
- Template basado en Low Level Discovery
- Master Item + Dependent Items

