---
name: zbx-index
description: "Mapa de documentación del proyecto zbx-in-docker. Usar PRIMERO cuando no sepas qué doc leer para una tarea de Zabbix. Indexa docs/, scripts/ y templates/. No inventar: si no está aquí, preguntar."
license: Apache-2.0
metadata:
  author: asg
  version: "2.0"
  scope: project
---

# Zabbix — Índice de documentación del proyecto

Abrir este skill primero para no explorar el árbol completo. Si la tarea no
aparece aquí, preguntar antes de improvisar.

## Flujos de trabajo

| Flujo | Skill | Cuándo |
|---|---|---|
| SSH + DB (diagnóstico, tuning, datos) | `zbx-ssh-diagnose` | Incidentes, SELECT/UPDATE en DB, tuning, backups |
| API token (dashboards, web) | `zbx-web-modify` | dashboard.update, mediatype, items/triggers via API |

## Mapa de docs por tarea

| Tarea | Doc / archivo |
|---|---|
| Modificar dashboards | `docs/dashboard-update.md` (ritual obligatorio) |
| Diagnóstico de servicio (pre/post) | `docs/checklist-servicio.md` |
| Recuperación / rollback | `docs/recupero.md` |
| Instalación / tuning | `docs/instalacion.md` |
| Migración config-only | `docs/migracion-checklist.md` |
| Mediatype / Telegram / ES | `docs/telegram-es-i18n.md` |
| Integración UniFi | `docs/unifi-external-check.md` |
| Proxmox / TLS de monitoreo | `docs/proxmox-monitoreo-tls.md` |
| MCP lab (read-only) | `docs/mcp-spike-fase2.md` |
| Hosts / freshness | `scripts/zbx-host-freshness.sh`, `scripts/zbx-active-agents.sh` |
| Bootstrap lab | `scripts/bootstrap_lab_agent.py`, `scripts/bootstrap_lab_sim.py` |
| Templates | `templates/` (XML/YAML) |
| Hoja de ruta | `docs/ROADMAP.md` |
| Seguridad / secretos | `docs/seguridad-secretos.md` |
| TLS | `docs/tls-letsencrypt-direct.md`, `docs/tls-cloudflare-origin.md` |

## Contexto del sitio

Este repo es genérico. Los datos del sitio (alias SSH, índice de docs propios,
trackers y particularidades) están en el repo privado del cliente:

```
client/agent-context.md
```

El trabajo de cliente se hace **por SSH sobre su servidor**: el checkout vive en
`/opt/monitoring/zbx-in-docker`, y el contexto está en
`/opt/monitoring/zbx-in-docker/client/agent-context.md`. Leerlo antes de operar y
usarlo como índice complementario a este. No clonar repos de cliente en la
máquina de trabajo: el único repo local es este, el genérico.

## Comandos frecuentes

```bash
# Conectar a un host remoto (levanta VPN si aplica)
~/projects/ops/bin/work <alias>

# Postgres en el server
sudo docker exec -it zabbix-postgres psql -U zabbix -d zabbix

# Backup mínimo antes de cambio gordo
cd /opt/monitoring/zbx-in-docker/docker
cp .env .env.bak.$(date +%Y%m%d_%H%M%S)
sudo docker exec zabbix-postgres pg_dump -U zabbix zabbix | gzip > /opt/monitoring/pg-backup-$(date +%Y%m%d_%H%M%S).sql.gz

# Reload caché de config
sudo docker exec zabbix-server zabbix_server -R config_cache_reload

# API version (verificar conectividad; sin Authorization)
curl -s http://127.0.0.1/api_jsonrpc.php -H 'Content-Type: application/json-rpc' \
  -d '{"jsonrpc":"2.0","method":"apiinfo.version","params":{},"id":1}'
```

## Reglas que no se negocian

1. Tokens API solo transient (terminal), jamás en archivos/commits/memoria.
2. `dashboard.update` reemplaza todo → ritual GET→backup→modify→PUT→verify.
3. Read-only por defecto en diagnóstico; writes solo con confirmación explícita.
4. Backup antes de cualquier cambio gordo.
5. `psql -c` no interpola variables → stdin + dollar-quoting.
6. No inventar configuración ni credenciales.
7. INSERT directo en `widget*`/`graphs*` → **actualizar la tabla `ids`**
   (`nextid = max+1`) o la próxima creación por API colisiona.
8. "Widget is not fully configured" = `widget_field.graphid.0` roto, no el
   widget: reparar el binding antes de tocar el dashboard.
9. Antes de dar un gráfico por hecho, correr la query de salud que corresponda
   al sitio (ver `client/agent-context.md`): resultado esperado 0 filas.

## Si la tarea no está en este índice

Preguntar al usuario antes de explorar. No asumir que existe un doc que no está aquí.
