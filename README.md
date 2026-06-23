# Monitoring Stack

Stack de monitoreo basado en:

- Zabbix 7 LTS
- PostgreSQL 15
- Grafana
- Nginx

## Componentes

- Zabbix Server
- Zabbix Web
- PostgreSQL
- Grafana
- Nginx Reverse Proxy

## Estado

Proyecto en desarrollo.

## Funcionalidades implementadas

### Monitoreo UniFi

- Obtención de dispositivos mediante API de UniFi Network
- Integración mediante Zabbix External Check
- Procesamiento mediante Master Item + Dependent Items
- Script Python ejecutado desde Zabbix Server
