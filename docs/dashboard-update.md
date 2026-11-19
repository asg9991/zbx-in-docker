# dashboard.update — full-payload procedure

Scope: Zabbix API `dashboard.update` on the Global view dashboard. Documentation only; no Zabbix changes are made by this file.

> Las particularidades de cada cliente (mapa de ifIndex, patrones de widgets,
> inventario de gráficos, minas propias del sitio) viven en su repo privado, en
> `client/docs/graficos-<cliente>.md`. Este documento cubre solo lo genérico del
> ritual; no reintroducir datos de cliente acá (ver `docs/recupero.md`).
> Si el objetivo es reparar un gráfico que "dejó de graficar", casi siempre es
> `widget_field.graphid.0` y NO hace falta `dashboard.update`.

## 1. Core rule: update replaces, it does not merge

`dashboard.update` is dashboard-scoped, not page-scoped. The `pages` array in the request **replaces** the whole dashboard definition:

- Sending a subset of pages deletes every page not included.
- Sending a subset of widgets on one page deletes the omitted widgets on that page.
- Dashboard changes leave no audit trail to restore from, so a partial payload is unrecoverable without a backup.

This happened twice in this project: partial updates deleted all other pages (12 pages lost once, 11 pages once). One incident was rebuilt from nginx access-log forensics plus the old database; the other was restored from a same-day configuration dump. Both recoveries were manual and slow.

Never send a partial payload. Always GET → backup → modify a full clone → single PUT → verify.

## 2. Mandatory backup before any mutation

Take all three before touching the dashboard:

1. `configuration.export` of the dashboard object.
2. `pg_dump` of the `dashboard*` / `widget*` tables.
3. The raw `dashboard.get` JSON saved to a dated file.

Generic examples (placeholders only, no secrets):

```bash
# 1. Full dashboard definition, dated backup
curl -s -H 'Content-Type: application/json' \
  -d '{"jsonrpc":"2.0","method":"dashboard.get","params":{"dashboardids":["1"],"selectPages":["extend"],"selectWidgets":["extend"]},"auth":"<token>","id":1}' \
  'https://<server>/api_jsonrpc.php' > "dashboard-1-$(date +%F).json"

# 2. configuration.export backup of the same dashboard
curl -s -H 'Content-Type: application/json' \
  -d '{"jsonrpc":"2.0","method":"configuration.export","params":{"format":"xml","options":{"dashboards":["1"]}},"auth":"<token>","id":2}' \
  'https://<server>/api_jsonrpc.php' > "dashboard-1-export-$(date +%F).xml"

# 3. Database-level backup of dashboard/widget tables
pg_dump -t 'dashboard*' -t 'widget*' "dbname=zabbix" > "dashboard-tables-$(date +%F).sql"
```

The old database (when available) also keeps the original layout in `widget` + `widget_field` keyed by `dashboard_pageid`, which is useful as a last-resort reference.

## 3. Procedure

### Step 1 — GET the complete definition

Fetch the dashboard with pages and widgets extended. Do not hand-craft a payload from memory.

```bash
curl -s -H 'Content-Type: application/json' \
  -d '{"jsonrpc":"2.0","method":"dashboard.get","params":{"dashboardids":["1"],"selectPages":["extend"],"selectWidgets":["extend"]},"auth":"<token>","id":1}' \
  'https://<server>/api_jsonrpc.php' > /tmp/dashboard-full.json
```

### Step 2 — Clone locally, never mutate the GET output in place

Work on a copy. Keep the pristine GET output as the rollback source.

### Step 3 — Validate the clone via `dashboard.create`

Before the real update, validate the payload shape by creating a throwaway clone with `dashboard.create`, then delete the clone. This catches stale `dashboard_pageid` / `widgetid` references: deleted IDs fail validation, so strip dead IDs before the real PUT.

### Step 4 — Pre-validation (before the PUT)

- Page count matches the GET output (e.g. 12 pages stay 12 pages; 11 pages stay 11 pages).
- Every `dashboard_pageid` in the payload is identical to the GET output.
- Per-page widget counts match, except for the one page being intentionally changed, whose delta is exactly the planned add/remove.
- New widgets use free grid coordinates (check `x`/`y`/`width`/`height` against existing widgets to avoid overlap).

### Step 5 — Minimal mutation

Change only the target page. Clone all other pages byte-identical. Prefer `graph.update` (dashboard-safe) over widget edits whenever the goal can be achieved without touching the dashboard.

### Step 6 — Single PUT

Send exactly one `dashboard.update` with the complete payload (all pages, all widgets). Multiple sequential updates multiply the window for loss.

Expected result: `{"dashboardids":["1"]}` with no error.

### Step 7 — Post-verification, per page plus sisters

Re-run `dashboard.get` and verify:

- Total page count unchanged.
- Widget count **per page**, not just the dashboard total (totals hide a page that lost widgets while another gained them).
- Every untouched ("sister") page has identical widget IDs and counts as before the mutation.
- The touched page contains exactly the expected widget ID list.

## 4. Trap: empty (reference-only) widgets drop silently

A widget that carries only a `reference` field and no data field (e.g. a graph widget with no `graphid`) can be dropped silently during a GET → PUT round-trip. This project lost an empty widget this way and had to restore it explicitly.

Consequences:

- A page whose widgets lost their backing objects (for example LLD-discovered graphs deleted after a discovery change) will show widgets with only `reference` fields. Do not PUT blindly in that state: either re-point them to valid objects first or abort the update.
- Always compare per-page counts before and after; a count drop of exactly the reference-only widgets is the signature of this trap.

### 4.1 Why widgets end up reference-only

Three cascades, verified in this project (documented per client in
`client/docs/graficos-<cliente>.md` of each private repo):

| Causa | Efecto |
|---|---|
| Se borra el `graph` | la FK `c_widget_field_5` borra el `widget_field` |
| Se borra el `item` | se borra el `graphs_items`; el gráfico queda vacío |
| Se borra un `template` | cascade sobre ítems/gráficos descubiertos de los hosts |

Reparación quirúrgica (sin `dashboard.update`): reinsertar `graphid.0` con
`type=6` y `value_graphid` válido, y **actualizar la tabla `ids`**.

### 4.2 Nunca insertar en `widget`/`widget_field`/`graphs` por SQL sin arreglar `ids`

Zabbix reserva IDs en la tabla `ids`. Un INSERT directo no la actualiza y el próximo
objeto creado por API colisiona. Después de cualquier INSERT directo:

```sql
UPDATE ids SET nextid = (SELECT max(widget_fieldid)+1 FROM widget_field) WHERE table_name='widget_field';
UPDATE ids SET nextid = (SELECT max(graphid)+1 FROM graphs)               WHERE table_name='graphs';
UPDATE ids SET nextid = (SELECT max(gitemid)+1 FROM graphs_items)         WHERE table_name='graphs_items';
UPDATE ids SET nextid = (SELECT max(widgetid)+1 FROM widget)              WHERE table_name='widget';
```

Verificar que cada `nextid` sea max+1 antes de seguir.

## 5. Lesson reference: the 12 deleted pages

A partial `dashboard.update` deleted 12 pages of the Global view. Recovery required nginx access-log forensics (`graphid` + referrer page mapping) plus the old database `widget` / `widget_field` rows, and several pages still needed manual input because no graph history existed for them. The mandatory ritual since then is GET → dated JSON backup → modify → PUT → verify counts per page.

## 6. Rollback

1. Re-PUT the pristine GET JSON saved in Step 1 (full payload, single `dashboard.update`).
2. If the API path is unusable, restore the `dashboard*` / `widget*` tables from the `pg_dump` backup, or re-import the `configuration.export` file.
3. Re-run the Step 7 verification and confirm sister pages are intact.

## 7. Widget `svggraph`: campos verificados

Un `svggraph` no tiene objeto `graph` detrás: las series viven en `widget_field`. Es la
opción cuando se necesita el valor al pasar el puntero y no hace falta un objeto reutilizable.

Cada campo es `{"type": <int>, "name": "...", "value": ...}`. Los tipos que importan:
`0` = entero, `1` = string, `6` = graphid.

Campos por dataset (`N` = 0, 1, 2…):

| Campo | Tipo | Contenido |
|---|---|---|
| `ds.N.dataset_type` | 0 | `0` = lista de items (el modo normal) |
| `ds.N.itemids.M` | 0 | `itemid` concreto del dataset N, serie M |
| `ds.N.color.M` | 1 | color hex de esa serie (`FF4655`) |
| `ds.N.axisy` | 0 | `0` = eje izquierdo, `1` = derecho |
| `ds.N.fill` | 0 | relleno bajo la curva |
| `ds.N.transparency` | 0 | transparencia del relleno |
| `ds.N.missingdatafunc` | 0 | qué dibujar cuando falta el dato |
| `ds.N.data_set_label` | 1 | etiqueta del dataset en la leyenda |
| `ds.N.aggregate_function` / `.aggregate_interval` / `.aggregate_grouping` | 0 / 1 / 0 | agregación por intervalo |

Campos del widget (fuera de `ds.`):

| Campo | Tipo | Contenido |
|---|---|---|
| `lefty_min` / `lefty_max` | 0 | eje Y fijo (omitir para automático) |
| `lefty_static_units` | 1 | unidad fija del eje (`bps`, `%`, …) |
| `lefty_units` | 0 | mostrar la unidad del item |
| `legend`, `legend_lines`, `legend_lines_mode`, `legend_columns`, `legend_statistic`, `legend_aggregation` | 0/1 | leyenda |
| `or.N.items.0` / `or.N.color` | 1 | overrides de color por item |

Patrón mínimo de un dataset con varias series en un solo gráfico:

```json
{"type": 0, "name": "ds.0.dataset_type", "value": 0},
{"type": 0, "name": "ds.0.itemids.0",    "value": "<itemid>"},
{"type": 1, "name": "ds.0.color.0",      "value": "FF4655"},
{"type": 0, "name": "ds.0.itemids.1",    "value": "<itemid>"},
{"type": 1, "name": "ds.0.color.1",      "value": "00A3A3"},
{"type": 1, "name": "lefty_static_units", "value": "bps"}
```

**Coste de mantenimiento:** cada retoque de un `svggraph` (agregar una serie, cambiar un
color, fijar el eje) es un `dashboard.update` con el payload completo, o sea el ritual de
la sección 3. Si el gráfico va a cambiar seguido, un `graph` clásico + widget `graph` es más
barato: se retoca con `graph.update`, que no toca el dashboard. La elección se hace por uso,
no por preferencia.

## 8. Gotchas de la API 7.4 (verificados)

- **Métodos en singular**: `item.create`, `trigger.create`, `graph.create`, `host.update`.
  `items.create` responde `Incorrect API "items"`.
- **Item SNMP**: `type: 20` (SNMP agent). Los tipos `1` / `4` / `6` (SNMPv1/v2/v3) están
  deprecados y el validador los rechaza.
- **`graph.create` usa `gitems`**, no `graphs_items` (ese es el nombre de la tabla).
- **Ejes fijos de un `graph`**: `yaxismin` / `yaxismax` (`ymin` / `ymax` no existen en el
  esquema). Requiere `ymin_type: 1` y `ymax_type: 1`.
- **`dashboard.get` no acepta `selectWidgets`**: con `selectPages: "extend"` los widgets
  vienen anidados en cada página.
- **Tipos de `widget_field`**: un campo entero con `type: 0` exige `value` numérico; los
  campos de texto (nombres de tag, labels) van con `type: 1`. Un `graphid` va con `type: 6`.
