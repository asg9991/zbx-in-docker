# Monitoring Stack

Stack de monitoreo basado en tecnologías Open Source para infraestructura de red, servidores y servicios.

## Componentes

- Zabbix Server 7 LTS
- Zabbix Web
- PostgreSQL 15
- Grafana
- Nginx Reverse Proxy

---

# Arquitectura

```
                 +----------------+
                 |    Grafana     |
                 +--------+-------+
                          |
                          |
+---------+        +-------v--------+
| Nginx   +------->+  Zabbix Web    |
+---------+        +-------+--------+
                          |
                          |
                  +-------v--------+
                  | Zabbix Server  |
                  +-------+--------+
                          |
              +-----------+-----------+
              |                       |
              |                       |
      SNMP / ICMP              External Checks
              |                       |
              |                 UniFi Network API
              |                       |
        Equipos de red         UniFi Controller
                          |
                  +-------v--------+
                  | PostgreSQL     |
                  +----------------+
```

---

# Funcionalidades implementadas

## Monitoreo de infraestructura

- Monitoreo mediante SNMP
- Monitoreo ICMP
- Descubrimiento automático
- Triggers
- Dashboards mediante Grafana

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

Actualmente:

- `ROADMAP.md`
- `unifi-external-check.md`

---

# Estado del proyecto

## Finalizado

- Docker Compose
- PostgreSQL
- Zabbix Server
- Zabbix Web
- Grafana
- Nginx Reverse Proxy
- Integración con UniFi Network API
- Descubrimiento automático de Access Points
- Template basado en Low Level Discovery
- Master Item + Dependent Items

## Próximas mejoras

- Utilización de radio (Radio Utilization)
- Potencia de transmisión (TX Power)
- CPU de Access Points
- Memoria
- Uptime
- Estadísticas por radio
- Dashboard específico para UniFi
- Template para UniFi Switches
