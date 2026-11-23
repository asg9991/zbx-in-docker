# Lecciones de observabilidad (bitácora técnica)

Registro de cosas que costaron tiempo, con el síntoma tal como se ve, para no
volver a investigarlas. Se actualiza a medida que aparecen.

---

## Grafana

| Síntoma | Causa | Solución |
| --- | --- | --- |
| Todos los stats en verde aunque haya problemas | El color lo define el **último step** de thresholds que el valor supera. Con un solo step en verde, todo es verde | Steps ascendentes: `null→text`, `0→green`, `1→red` |
| Un stat con "Revisar" no dice cuánto | Se usaron mappings de texto en lugar del valor | Mostrar el número y dejar el color a thresholds |
| `No data` en verde | Grafana ignora los mappings cuando no hay dato y usa el color base | `noValue: "Sin datos"` + primer step en color `text` |
| Un stat que debe contar filas muestra "No data" | Solo considera campos numéricos | `reduceOptions.fields` con el nombre del campo |
| Link a otra app termina en "Page not found" | Grafana sirve bajo `/grafana`: una ruta absoluta (`/zabbix.php`) queda dentro del subpath | Usar rutas de Grafana (`/d/<uid>?viewPanel=<id>`); para salir a Zabbix, URL absoluta por sitio |

## Plugin Zabbix

| Síntoma | Causa | Solución |
| --- | --- | --- |
| Query con "todos los hosts" devuelve vacío | No acepta grupo vacío ni `*` | `group: {filter: "<grupo exacto>"}` + `host: {filter: "/.*/"}` |
| Columnas de problemas en inglés | El plugin no tiene i18n | Datasource `Zabbix API` (Infinity) + tabla propia |
| "non-metrics queries are not supported" | `queryType` de problemas no pasa por `/api/ds/query` | Solo el panel del plugin las resuelve; para tablas usar la API |

## Infinity

| Síntoma | Causa | Solución |
| --- | --- | --- |
| `Not authorized` con token válido | `auth_method: bearer` no existe | Debe ser exactamente `bearerToken` |
| `412 Precondition Failed` | Falta `Content-Type` | `url_options.headers: [{key: Content-Type, value: application/json-rpc}]` |
| Body ignorado | El campo no es `body` | Va en `url_options.data` (string JSON) |
| `no results found` al aplanar un array | `root_selector` con `parser: backend` es GJSON; las columnas usan JSONata | Usar JSONata (empieza con `$`): `$map(result, function($v){...})` |
| `$now()` en JSONata no resta | Devuelve ISO, no milisegundos | Usar `$millis()` |
| `paths cannot contain nulls... position: 0` | El backend no compila **bloques** JSONata (`($x := ...; ...)`) | Escribir una sola expresión sin asignaciones; repetir el cálculo si hace falta |
| El generador borra el marcador `query` | Se reemplaza el target completo | Incluir la clave `query` en el target generado |
| `root_selector` con `[{...}]` devuelve null | El backend no toma el constructor de array como raíz | Emitir la fila con `$map([1], function($x){...})` |
| `trigger.get` con `host: ["nombre"]` da error de sistema | El filtro por nombre está roto en 7.4 para este rol | Filtrar por `hostids` |
| **El mapa/estado dice OK con problemas activos** | `trigger.get` devuelve `value` inconsistente (0 en triggers que están en problema) y `only_true` mezcla resultados | Usar **`problem.get`** con `hostids` como fuente de estado; `trigger.get` para nombre/descripción, no para saber si hay problema |
| **Canvas: el nodo queda verde aunque el campo diga "red"** | `getColorDimensionForField` no interpreta el texto como color: usa el display processor del campo. Un string solo toma el color fijo del campo | Devolver **número 0/1** y definir en el panel `color: {mode: "thresholds"}` + thresholds 0 verde / 1 rojo |
| `countOutput` no se puede mostrar | Devuelve un escalar, no una tabla | Traer filas y contar en el panel |

## Loki y Alloy

| Síntoma | Causa | Solución |
| --- | --- | --- |
| Alloy no lee archivos nuevos y no se recupera | `loki.source.file` con glob sin coincidencias al arrancar descarta la fuente | `local.file_match` + `loki.source.file` |
| `unrecognized attribute "labels"` | `loki.source.file` no acepta ese argumento | Etiquetas en `path_targets` |
| El atraso nunca drena tras un corte | Loki rechaza entradas fuera de orden | `limits_config.unordered_writes: true` |
| `timestamp too new` | Reloj del emisor adelantado, o zona horaria mal interpretada | NTP en equipos; emitir **RFC5424 con `Z`** |
| Pérdida de líneas durante un corte | Buffer sin backpressure | `block_on_overflow: true` (default) y retención mayor al corte |
| Crash de Alloy pierde lo aceptado | Cola en memoria | `wal { enabled = true }` (requiere `--stability.level=experimental`) |
| Loki ingiere sus propios logs | Exclusión solo por label de compose | Regla extra por `__meta_docker_container_name` |
| `400 entry too far behind` y `dropping data` al reanudar | El atraso supera la ventana de desorden de Loki (`max_chunk_age/2` = 1 h), aunque el archivo lo tenga | No prometer drenaje de días: el buffer cubre caídas cortas. La siembra histórica del lab exige streams vacíos |
| Los logs se llenan de `failed to report usage` | Alloy intenta reportar a stats.grafana.org y no hay salida | `--disable-reporting` en el comando de Alloy |

## Clasificación y semáforos

| Síntoma | Causa | Solución |
| --- | --- | --- |
| El semáforo del cliente dice OK con un Desastre activo | La clase `desconocido` no tenía regla y no aportaba estado | `regla_desconocido` en `clases.yaml`: Alta+ escala a crítico; un aviso desconocido no mueve el semáforo |
| Una clase específica "desaparece" dentro de otra | La clasificación es por subcadena y gana la primera clase del catálogo | Clases específicas antes que genéricas; `evaluar_clasificador.py --verbose` muestra la matriz esperado→obtenido |
| El respaldo de Grafana falla con "Permission denied" | `grafana.db` lo escribe Grafana como uid 472 | `sudo scripts/backup_observability.sh`; la copia usa la API de backup de SQLite, no un `cp` |

## Docker

| Síntoma | Causa | Solución |
| --- | --- | --- |
| El puerto publicado no escucha | El contenedor está **solo** en redes `internal` | Conectarlo también a una red no interna |
| Plugin horneado no aparece | El volumen de `DATA_DIR` tapa `/var/lib/grafana` | Instalarlo en `/opt/grafana-plugins` + `GF_PATHS_PLUGINS` |
| Healthcheck siempre falla | Imagen distroless (Loki) sin shell ni wget | Sin healthcheck; verificar con cliente externo |
| `TZ` no hace efecto en Alpine | Falta `tzdata` | Usar imagen Debian, o instalar `tzdata` |

## Zabbix

| Síntoma | Causa | Solución |
| --- | --- | --- |
| Todo alta falla con `duplicate key items_pkey` | La tabla `ids` quedó por debajo de `max(itemid)` (restore/import) | `UPDATE ids SET nextid = (SELECT max(itemid)+1 FROM items)` |
| No hay forma de obtener el token al crearlo | `token.create` solo devuelve IDs | Después: `token.generate [<tokenid>]` |
| `host.get` devuelve `available: null` | Campo deprecado en 7.x | `hostinterface.get` con `available: 2` |
| Falta el equipo del problema | `problem.get` no trae hosts | `trigger.get` con `only_true` + `selectHosts` |
| `item.state` no existe en la tabla | Vive en `item_rtdata` | El API lo filtra igual: `filter: {state: 1}` |

---

## Regla de mantenimiento

Cada vez que algo cueste más de 10 minutos, se agrega una fila acá con el
síntoma **tal como se ve en pantalla**. Un documento que solo dice la solución
no sirve: la próxima persona busca por el síntoma.

---

## Enlaces entre aplicaciones (decisión pendiente)

Estado actual: **todo queda dentro de Grafana**. Los drill-down de los KPIs
llevan a dashboards de Grafana (`/d/problemas`, `/d/salud-monitoreo`), no a
Zabbix.

Por qué: Grafana sirve bajo el subpath `/grafana`, así que una ruta absoluta
como `/zabbix.php` termina en `/grafana/zabbix.php` y da "Page not found". Un
link correcto a Zabbix exige **URL absoluta con el host del sitio**.

Cuando se decida dónde vive esa opción, el lugar natural es:

| Pieza | Dónde |
| --- | --- |
| Valor por sitio | `.env` del cliente (`ZABBIX_PUBLIC_URL=https://zabbix.<sitio>`) |
| Transporte a Grafana | variable de entorno del contenedor |
| Uso en el dashboard | variable de tipo *textbox* con default `/zabbix.php` (o el valor publicado) usada en el data link |

Mientras no esté definido, **no se agregan links a Zabbix**: un link que a veces
funciona es peor que ninguno. Lo que el técnico necesita ver ya está replicado en
Grafana (`Problemas`, `Salud del monitoreo`, `Técnico`).

---

## Centralización de consultas a la API

Las consultas viven en **`scripts/observability/queries.py`** (nombre lógico →
método, params, root_selector, columnas). Los dashboards solo llevan
`"query": "<nombre>"` y `scripts/gen_queries.py` inyecta el resto.

```bash
python3 scripts/gen_queries.py          # regenera
python3 scripts/gen_queries.py --check  # falla si algo quedó desincronizado
```

Regla: no se escribe un body a mano en un dashboard. Si falta una consulta, se
agrega en `queries.py` con un nombre y se referencia.

---

## Canvas: conexiones

El campo `connections` de cada elemento **no usa nombres**: usa coordenadas
normalizadas respecto del elemento y un `targetName`.

```json
{
  "source": { "x": 1, "y": 0 },
  "target": { "x": -1, "y": 0 },
  "targetName": "router-sim-02",
  "path": "straight"
}
```

- `source`/`target` van de `-1` a `1` (0,0 es el centro del elemento; 1,0 el
  borde derecho; -1,0 el izquierdo).
- Adornos soportados: `color` (ColorDimensionConfig), `size` (ScaleDimensionConfig
  con `min`/`max`/`fixed`) y `lineStyle` (`{"fill": "solid"|"dash"|"dot"}`).
  El camino es siempre recto: no hay ruteo ortogonal ni curvas.
- La conexión se guarda en el elemento **origen**.
- Sin `path: "straight"` no se dibuja.

Canvas **no tiene `frameIndex`**: no se puede atar cada elemento a una fila
distinta de una consulta. La salida es una consulta **por nodo** con campos
únicos (`c_<i>`, ver "Mapa generado"), no una tabla al lado del mapa.

---

## Mapa generado (D-M1)

`scripts/gen_map.py` lee un `topology.yml` y escribe el dashboard Canvas.

```yaml
name: lab
title: Mapa de red
nodes:
  - {name: fw-sim-08, label: Firewall, level: 0, icon: shield}
edges:
  - [fw-sim-08, router-sim-02]
```

- **Cada nodo trae su propia consulta** (`estado_host`) con campos únicos
  `c_<i>` / `s_<i>`. Canvas resuelve el campo por nombre recorriendo los
  frames, así que el nombre único es lo que hace que cada elemento tome **su**
  estado.
- El color se ata con `background.color.field = "c_<i>"`.
- `hostid` es obligatorio: el filtro por nombre de host falla en 7.4.

---

## Canvas: iconos y layout

- Tipo de elemento `icon`: `config.path = {mode:"fixed", fixed:"img/icons/unicons/<nombre>.svg"}`
  y `config.fill` para el color. Iconos verificados en Grafana 13:
  `server, cloud, monitor, desktop, laptop, wifi, database, shield, exchange,
  process, fire, lock, bolt, plug, sitemap, chart-bar`.
- El `fill` del icono acepta el mismo truco que el fondo: campo numérico 0/1 +
  thresholds en el panel.
- Posiciones: `placement` es absoluto en píxeles. El generador calcula las
  columnas por `level` y centra cada columna, así que agregar un equipo no
  requiere mover nada a mano.
- El layout se parametriza en `topology.yml › layout`: `node_w`, `node_h`,
  `icon_size`, `x_gap`, `y_gap`, `origin_x`, `origin_y`, `line_color`,
  `line_size`.

---

## Drill-down por variable en Infinity

Infinity interpola variables de dashboard en `url`, `url_options.data`,
headers y params (`src/interpolate.ts`, función `interpolateQuery`). Eso
permite un dashboard genérico por equipo:

```
/d/equipo?var-host=<host>&var-hostid=<hostid>
```

- `host` alimenta la consulta de Loki (`{host="$host"}`).
- `hostid` va dentro del body JSON-RPC de `problem.get` como `${hostid}`.

Sin esto, cada equipo necesitaría un dashboard propio.

---

## Navegación entre dashboards

Problema: listar cada dashboard en la barra superior ocupa lugar y se
desactualiza (hay que editar N dashboards para agregar uno).

Solución: **un único link de tipo `dashboards` filtrado por etiqueta**.

```json
{"title":"Estado General","tags":["nav","cliente"]}
{"title":"Técnico",       "tags":["nav","tecnico"]}
{"title":"Mapas",         "tags":["nav","mapa"]}
```

Grafana filtra por **todas** las etiquetas (and). Cada dashboard declara
**una** audiencia (`cliente`, `tecnico` o `mapa`) y lleva `nav`.

**Excepción:** los dashboards de drill-down (como `equipo`) **no llevan `nav`**:
no se listan en ningún menú, se llega solo por link directo. Igual muestran los
menús para poder salir.

- Agregar un dashboard es ponerle `nav` + la audiencia (`cliente` o `tecnico`).
- `keepTime: true` mantiene la ventana de tiempo al saltar.
- `includeVars: false` evita arrastrar variables de un equipo a otro dashboard.
- `scripts/nav_links.py` **reemplaza** todos los links del dashboard por el
  menú único (no los agrega al lado: si no, quedan los viejos y la barra vuelve
  a llenarse). Idempotente, con `--check` para CI. El generador de mapas lo
  emite también.
