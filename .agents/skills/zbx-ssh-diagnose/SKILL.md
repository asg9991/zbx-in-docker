---
name: zbx-ssh-diagnose
description: "Diagnóstico y cambios de DB en Zabbix vía SSH + psql (flujo primario). Usar cuando: investigar incidentes, verificar datos, consultar hosts/items/triggers/problems, tuning, o modificar config en DB. NO usar para dashboards/web (ver zbx-web-modify)."
license: Apache-2.0
metadata:
  author: asg
  version: "2.0"
  scope: project
---

# Zabbix — Diagnóstico vía SSH + DB (Flujo A)

Este es el flujo primario de operación. No desplegar MCP ni APIs para esto.

## Conexión

1. Usar el toolkit ops: `~/projects/ops/bin/work <alias>` (levanta VPN ipsec si
   el sitio lo requiere y luego SSH). Los alias de cada sitio están en
   `ops/config/clients.yaml` y en `client/agent-context.md` del repo del cliente.
   Lab local: no aplica SSH, operar directo en el host.
2. En el server, entrar a Postgres:
   ```bash
   sudo docker exec -it zabbix-postgres psql -U zabbix -d zabbix
   ```
   O one-shot: `sudo docker exec zabbix-postgres psql -U zabbix -d zabbix -c "SELECT ..."`

## Reglas de oro

- **Read-only por defecto.** SELECT primero. Cualquier UPDATE/DELETE requiere confirmación explícita del usuario antes de ejecutar.
- **Tokens API jamás en archivos, commits ni memoria persistente.** Solo transient en terminal.
- **Backup antes de cualquier cambio gordo** (ver `docs/checklist-servicio.md` §5): `.env.bak` + `pg_dump` fechado.
- **Solo `SELECT` vía ssh+psql** para relevamiento; writes solo con autorización.

## Procedimiento de diagnóstico

1. **Servicio vivo**: seguir `docs/checklist-servicio.md` (cgroup, docker ps, web 200, datos fluyendo, disco, red).
2. **Problemas activos**: query directa a `problem`/`triggers`/`hosts` (ver `docs/checklist-servicio.md` §4).
3. **Freshness de hosts**: `scripts/zbx-host-freshness.sh`, `scripts/zbx-active-agents.sh`.
4. **Tuning**: revisar `docs/instalacion.md` §Tuning.
5. **Recuperación**: `docs/recupero.md`.

## Trampas (gotchas) a recordar

- **cgroup, no pgrep**: container y nativo se llaman igual; verificar `/proc/$p/cgroup` para detectar procesos host (ver checklist §1).
- **VPN secuestra subredes Docker** (`172.28.x`): si curl cuelga con VPN activa, agregar `ip rule` por subred del lab.
- **Caché sorda a inserts nuevos**: si un item recién creado no recibe datos en 5 min → `zabbix_server -R config_cache_reload`, si sigue → restart.
- **`name_upper` no se rellena por API**: tras alta nueva, verificar `select hostid from hosts where name_upper='' or name_upper is null;` y corregir con UPDATE.
- **`psql -c` no interpola variables** en este entorno: usar SQL por stdin con dollar-quoting (`$tag$...$tag$`) para textos largos.
- **Mediatype `mediatype.update` vía API necesita Bearer token**; sin token → SQL directo + `config_cache_reload`.
- **Nativo muerto**: `systemctl is-enabled zabbix-server nginx mysql docker` → masked/masked/disabled/enabled.

## Textos largos en DB (dollar-quoting)

```bash
sudo docker exec -i zabbix-postgres psql -U zabbix -d zabbix <<'SQL'
UPDATE media_type SET ... WHERE mediatypeid=97;
SQL
```

Nunca usar `psql -c` con variables `:'var'` para updates de texto largo.

## Contexto del sitio

Los docs propios del sitio (diagnóstico de incidentes, migración, runbooks) y
sus particularidades viven en el repo privado del cliente:

```
client/agent-context.md
client/docs/
```

En el servidor el checkout está en `/opt/monitoring/zbx-in-docker`. Si el
archivo existe, leerlo antes de improvisar.

## Docs de referencia (genéricos)

- `docs/checklist-servicio.md` — checklist pre/post servicio
- `docs/recupero.md` — recuperación
- `docs/instalacion.md` — instalación y tuning
- `docs/migracion-checklist.md` — verificación posterior a migración
- `docs/telegram-es-i18n.md` — mediatype/Telegram/ES
- `docs/mcp-spike-fase2.md` — MCP lab (solo lectura, no modificar)

## Cuándo NO usar este flujo

- Modificar dashboards o partes web → usar `zbx-web-modify`.
- Consultas read-only simples en lab → MCP lab (`127.0.0.1:8080`, read-only) es aceptable, pero SSH+psql sigue siendo la fuente de verdad.
