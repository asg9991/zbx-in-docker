# ROADMAP

## Fase 1 - Plataforma Base

- [x] Docker Compose
- [x] PostgreSQL
- [x] Zabbix Server
- [x] Zabbix Web
- [x] Nginx Reverse Proxy
- [x] Agent2 local
- [x] Imagen personalizada de Zabbix Server
- [x] Soporte para Python External Checks

---

## Fase 2 - Documentación

### General

- [x] README del proyecto
- [x] Arquitectura general
- [x] Guía de instalación
- [x] Backup (2026-09-06)
- [x] Restore (2026-09-06)
- [ ] Troubleshooting general

### Integraciones

- [x] Documentación de UniFi Network API
- [ ] Documentación FortiGate
- [ ] Documentación OLT Zhone
- [ ] Documentación de templates personalizados

---

## Fase 3 - Monitoreo

### Infraestructura

- [ ] FortiGate SNMP
- [ ] Linux Hosts
- [ ] Windows Hosts
- [ ] Switches
- [ ] OLTs

### UniFi Network

- [x] Integración mediante API
- [x] Autenticación
- [x] Descubrimiento automático (LLD)
- [x] Master Item
- [x] Dependent Items
- [x] Estado del AP
- [x] Firmware
- [x] Clientes conectados
- [x] Tráfico RX/TX

Próximas métricas:

- [ ] CPU
- [ ] Memoria
- [ ] Uptime
- [ ] Radio Utilization
- [ ] TX Power
- [ ] Channel
- [ ] Channel Width
- [ ] Clientes por radio
- [ ] Información PoE
- [ ] Dashboard UniFi

---

## Fase 4 - Operación

- [ ] Actualización de imágenes
- [ ] Backups automáticos
- [ ] Backups offsite prod: definir destino y automatizar (cron)
- [ ] Exportación de dashboards
- [ ] Templates personalizados
- [ ] Versionado de templates
- [ ] Librería de External Checks

---

## Fase 5 - Producto

- [ ] Instalación automatizada
- [ ] Script de despliegue
- [ ] CI/CD
- [ ] Versionado
- [ ] Release v1.0

---

## Fase 6 - NOC Agent

Asistente inteligente sobre la plataforma. Ver [docs/noc-agent/arquitectura.md](noc-agent/arquitectura.md).

- [x] Fase 0: Compose parametrizado para lab local (`DATA_DIR`) y stack levantado
- [x] Fase 1: Datos simulados con triggers que generan problemas reales
- [ ] Fase 2: Hub MCP (zabbix-mcp-server filtrado read-only) validado con endpoint externo
- [ ] Fase 3: Orquestador (router determinista + clasificador + cliente MCP)
- [ ] Fase 4: Adapter Discord (alertas→hilos, botones, ephemeral)
