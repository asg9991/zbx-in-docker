# Zabbix 7.4 — API y widgets: referencia

Material de consulta sobre la API y los widgets de Zabbix 7.4, verificado contra una
instalación en producción. Los procedimientos operativos viven en otros documentos: el
ritual de `dashboard.update` en `docs/dashboard-update.md` y el checklist de servicio en
`docs/checklist-servicio.md`.

## API

| Tema | Realidad verificada |
|---|---|
| Métodos | en **singular**: `item.create`, `trigger.create`, `graph.create`, `host.update`. `items.create` responde `Incorrect API "items"` |
| Item SNMP | `type: 20` (SNMP agent). Los tipos `1` / `4` / `6` (SNMPv1/v2/v3) están deprecados y el validador los rechaza |
| Grafos | `graph.create` usa `gitems`, no `graphs_items` (ese es el nombre de la tabla) |
| Ejes fijos de un grafo | `yaxismin` / `yaxismax`; no existen `ymin` / `ymax` en el esquema. Requiere `ymin_type: 1` y `ymax_type: 1` |
| Grafos descubiertos por LLD | no se pueden modificar por API: `Cannot update a discovered graph`. Para cambiar color o nombre, crear un grafo manual sobre los mismos items y repuntar el widget |
| `dashboard.get` | no acepta `selectWidgets`; con `selectPages: "extend"` los widgets vienen anidados en cada página |
| `widget_field.type` | `0` = entero, `1` = string, `6` = graphid. Un campo entero con `type: 0` exige `value` numérico |
| Macros de host | `usermacro.create` exige `description` (columna NOT NULL). Sin ella falla con un error SQL genérico, no con un mensaje de validación |

## Widget `svggraph`

Un `svggraph` no tiene objeto `graph` detrás: las series viven en `widget_field`. Sirve
cuando se necesita el valor al pasar el puntero y no hace falta un objeto reutilizable.

Cada campo es `{"type": <int>, "name": "...", "value": ...}`, con los tipos del cuadro
anterior.

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

**Coste de mantenimiento.** Cada retoque de un `svggraph` (agregar una serie, cambiar un
color, fijar el eje) es un `dashboard.update` con el payload completo, o sea el ritual de
`docs/dashboard-update.md`. Si el gráfico va a cambiar seguido, un `graph` clásico + widget
`graph` es más barato: se retoca con `graph.update`, que no toca el dashboard. La elección
se hace por uso, no por preferencia.
