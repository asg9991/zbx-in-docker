---
name: zbx-index
description: "Mapa de documentación del proyecto zbx-in-docker. Usar PRIMERO cuando no sepas qué doc leer para una tarea de Zabbix. Indexa docs/, scripts/, templates/ y odd/tasks/. No inventar: si no está aquí, preguntar."
license: Apache-2.0
metadata:
  author: asg
  version: "1.0"
  scope: project
---

# Zabbix — Índice de documentación del proyecto

Abrir este skill primero para no explorar el árbol completo. Si la tarea no aparece aquí, preguntar antes de improvisar.

## Flujos de trabajo

| Flujo | Skill | Cuándo |
|---|---|---|
| SSH + DB (diagnóstico, tuning, datos) | `zbx-ssh-diagnose` | Incidentes, SELECT/UPDATE en DB, tuning, backups |
| API token (dashboards, web) | `zbx-web-modify` | dashboard.update, mediatype, items/triggers via API |

## Mapa de docs por tarea

| Tarea | Doc / archivo |
|---|---|
| **Armar/arreglar un gráfico o widget** | **`docs/graficos-site-a.md`** (modelo DB, patrones, receta, minas) |
| Modificar dashboards | `docs/dashboard-update.md` |
| Recolección EDGE (mapper, LLD, macros) | `docs/vlan-lld-site-a.md` |
| Diagnóstico de servicio (pre/post) | `docs/checklist-servicio.md` |
| Diagnóstico de incidente real | `docs/diagnostico-site-a-20250915.md` |
| Recuperación / rollback | `docs/recupero.md` |
| Mediatype / Telegram / ES | `docs/telegram-es-i18n.md` |
| Instalación / tuning | `docs/instalacion.md` |
| Migración config-only | `docs/migracion-site-a-config-only.md`, `docs/migracion-site-b-config-only.md` |
| Runbooks de migración | `docs/runbook-migracion-site-a.md`, `docs/runbook-migracion-site-b.md` |
| Integración UniFi | `docs/unifi-external-check.md` |
| MCP lab (read-only) | `docs/mcp-spike-fase2.md` |
| Hosts / freshness | `scripts/zbx-host-freshness.sh`, `scripts/zbx-active-agents.sh` |
| Bootstrap lab | `scripts/bootstrap_lab_agent.py`, `scripts/bootstrap_lab_sim.py` |
| Templates | `templates/` (XML/YAML) |
| Tareas ODD activas | `odd/tasks/*.md` |
| Hoja de ruta | `docs/ROADMAP.md` |
| Seguridad / secretos | `docs/seguridad-secretos.md` |
| TLS | `docs/tls-letsencrypt-direct.md`, `docs/tls-cloudflare-origin.md` |

## Hosts y accesos (NO memorizar IPs — leer YAML)

Fuente de verdad: `~/projects/ops/config/clients.yaml` (skill `ops-remote`).

| Cliente | Acceso | Hosts Zabbix |
|---|---|---|
| site-c | ipsec | zabbix-site-c |
| site-a | ssh directo | zabbix-site-a |
| site-b | ssh directo | zabbix-site-b |
| lab | local | zbx-in-docker (este repo) |

## Comandos frecuentes

```bash
# Conectar a un host remoto (levanta VPN si aplica)
~/projects/ops/bin/work <host>

# Postgres en el server
sudo docker exec -it zabbix-postgres psql -U zabbix -d zabbix

# Backup mínimo antes de cambio gordo
cd /opt/monitoring/zbx-in-docker/docker
cp .env .env.bak.$(date +%Y%m%d_%H%M%S)
sudo docker exec zabbix-postgres pg_dump -U zabbix zabbix | gzip > /opt/monitoring/pg-backup-$(date +%Y%m%d_%H%M%S).sql.gz

# Reload caché de config
sudo docker exec zabbix-server zabbix_server -R config_cache_reload

# API version (verificar conectividad)
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
9. Antes de dar un gráfico por hecho, correr la query de salud de
   `docs/graficos-site-a.md` (paso 6): resultado esperado 0 filas.

## Si la tarea no está en este índice

Preguntar al usuario antes de explorar. No asumir que existe un doc que no está aquí.
