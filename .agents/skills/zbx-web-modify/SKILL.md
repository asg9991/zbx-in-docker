---
name: zbx-web-modify
description: "Modificar dashboards y partes web de Zabbix vía API token (flujo secundario). Usar cuando: dashboard.update, mediatype.update, items/triggers via API, o cambios en la web. Requiere token Bearer transient. NO usar para diagnóstico/DB (ver zbx-ssh-diagnose)."
license: Apache-2.0
metadata:
  author: asg
  version: "1.0"
  scope: project
---

# Zabbix — Modificaciones web vía API token (Flujo B)

Flujo secundario: solo cuando se modifica la web (dashboards, mediatypes, etc.). Token Bearer transient, jamás persistido.

## Autenticación (Zabbix >= 7)

- Bearer header: `Authorization: Bearer <token>`. NO usar campo `auth` top-level (rechazado en 7+).
- Token generado desde UI: Users → API tokens → Create API token. Transient: usar en terminal, no guardar en archivos ni memoria.
- `mediatype.update` vía API necesita Bearer token; sin token → SQL directo + `config_cache_reload`.

## Procedimiento obligatorio para dashboards

Fuente: `docs/dashboard-update.md`. Ritual no negociable (incidente: 12 páginas borradas).

1. **GET** completo: `dashboard.get` con `selectPages=["extend"]`, `selectWidgets=["extend"]`.
2. **Backup fechado**: guardar JSON crudo + `configuration.export` (XML) + `pg_dump` de `dashboard*`/`widget*`.
3. **Clonar** (nunca mutar el GET en sitio). Trabajar sobre la copia.
4. **Validar shape** con `dashboard.create` (clon descartable) para detectar IDs muertos (`dashboard_pageid`/`widgetid` stale).
5. **Pre-validación**: page count igual, `dashboard_pageid` idénticos, widget count per-page (no solo total), coordenadas libres (x/y/width/height).
6. **Mutación mínima**: cambiar solo la página objetivo; clonar byte-idénticas las demás. Preferir `graph.update` (dashboard-safe) sobre edición de widgets.
7. **Single PUT**: un solo `dashboard.update` con payload completo. Múltiples updates multiplican la ventana de pérdida.
8. **Verificación per-page**: re-GET y verificar page count, widget count por página (no solo total), sister pages intactas, página tocada con IDs esperados.

## Trampas específicas

- **`dashboard.update` reemplaza todo** (no suma): enviar subset de páginas borra las omitidas.
- **Widgets reference-only se dropean silenciosamente** en round-trip GET→PUT (ej. graphs LLD cuyos objetos se eliminaron). Comparar counts per-page antes/después; si cae exactamente la cantidad de reference-only, abortar o re-apuntar.
- **Página con widgets huérfanos** (sin backing object): no hacer PUT ciego; re-apuntar o abortar.

## Rollback

1. Re-PUT el JSON pristine del GET (payload completo, single update).
2. Si la API no sirve: restaurar tablas `dashboard*`/`widget*` desde `pg_dump`, o re-importar `configuration.export`.
3. Re-ejecutar verificación §8.

## Otras modificaciones web

- **Mediatype/Telegram/ES**: `docs/telegram-es-i18n.md`. CRLF real (0x0D 0x0A), no `\r` literal ni `\n` extra con dollar-quoting. Webhook `severity_es`/`event_es`.
- **Items nuevos que no grafican**: `config_cache_reload` o restart (ver `docs/checklist-servicio.md` §8).
- **Host nuevo invisible en búsquedas**: verificar `name_upper` (ver `docs/checklist-servicio.md` §9).

## Docs de referencia

- `docs/dashboard-update.md` — procedimiento completo (fuente de verdad)
- `docs/telegram-es-i18n.md` — mediatype/Telegram/ES
- `docs/checklist-servicio.md` — caché, name_upper, servicio

## Cuándo NO usar este flujo

- Diagnóstico o cambios en DB → usar `zbx-ssh-diagnose`.
- Crear hosts masivos → scripts de bootstrap (`scripts/bootstrap_lab_sim.py`) o API con token, pero validar con el flujo de arriba.
