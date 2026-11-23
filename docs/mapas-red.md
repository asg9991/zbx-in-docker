# Mapas de red por cliente

Procedimiento curado para levantar uno o varios mapas de red en un sitio.
El insumo es un **prompt con el orden de los equipos**; el resto lo hace el
generador.

---

## 1. El prompt (lo que se le pide al agente)

Se completa y se pega tal cual. Lo importante es el **orden por nivel** y los
**enlaces**; los nombres son los hosts de Zabbix.

```text
Armá el mapa de red del sitio <CLIENTE> con slug <slug-del-mapa>.

Niveles, de izquierda a derecha (uno por línea):
  nivel 0: <host-zabbix>            # p. ej. FW-SITIO
  nivel 1: <host-zabbix>
  nivel 2: <host-zabbix>, <host-zabbix>
  nivel 3: <host-zabbix>, <host-zabbix>

Enlaces (origen -> destino):
  <host> -> <host>
  <host> -> <host>

Etiquetas visibles (si el host de Zabbix no se entiende):
  <host>: <etiqueta>
```

### Contrato del agente

1. Crear `docker/observability/maps/<slug>.yml` con:
   - `slug`, `title`, `folder: Tecnico`
   - `layout` (ver defaults abajo)
   - `nodes`: `name` (host en Zabbix), `label`, `level`, `icon`
   - `edges`
2. **No escribir `hostid`**: se resuelve con la API.
3. Icono según la clase (tabla de abajo). Si no está claro, `server`.
4. Ejecutar:
   ```bash
   ZBX_API_URL=http://127.0.0.1/api_jsonrpc.php \
   python3 scripts/gen_map.py --resolve
   ```
5. Verificar (checklist §5) y reportar el `uid` generado.

### Iconos por clase

| Clase | Icono | Clase | Icono |
| --- | --- | --- | --- |
| Firewall | `shield` | Servidor | `server` |
| Router / Switch | `exchange` | ONU | `plug` |
| Core | `sitemap` | PBX / Voz | `monitor` |
| OLT | `bolt` | UPS / Energía | `bolt` |
| AP / WiFi | `wifi` | Base de datos | `database` |
| Cloud / Internet | `cloud` | Cámara / IoT | `process` |

---

## 2. Archivo de topología

```yaml
slug: cliente-norte           # define uid = mapa-cliente-norte
title: Mapa - Norte
folder: Tecnico

layout:
  node_w: 120
  node_h: 44
  icon_size: 40
  x_gap: 170
  y_gap: 34
  origin_x: 20
  origin_y: 60
  line_color: "#8fa6c1"
  line_size: 1.5

nodes:
  - {name: FW-NORTE, label: Firewall, level: 0, icon: shield}
  - {name: RTR-NORTE, label: Router, level: 1, icon: exchange}
  - {name: SW-CORE, label: Core, level: 2, icon: sitemap}

edges:
  - [FW-NORTE, RTR-NORTE]
  - [RTR-NORTE, SW-CORE]
```

### Parámetros

| Campo | Efecto |
| --- | --- |
| `level` | columna (0 = izquierda). El generador centra cada columna |
| `icon` | icono de Grafana; si se omite, caja de texto |
| `x_gap` / `y_gap` | separación horizontal / vertical |
| `node_w` / `node_h` | tamaño de la caja (sin icono) |
| `icon_size` | lado del icono |
| `origin_x` / `origin_y` | origen del dibujo |
| `line_color` / `line_size` | estilo de las conexiones |

---

## 2bis. Drill-down: del nodo al problema

Cada nodo del mapa abre **`/d/equipo?var-host=<host>&var-hostid=<hostid>`**, un
dashboard por equipo con:

- contador de problemas activos,
- tabla de problemas del equipo (Problema, Gravedad, Antigüedad),
- logs de ese equipo (`{job="syslog", host="$host"}`).

Infinity **interpola variables dentro del body** (`src/interpolate.ts`), por eso
`problem.get` recibe `"hostids": ["${hostid}"]` y Grafana lo reemplaza con el
valor de la URL.

Regla: nunca linkear a `problemas` a secas desde un equipo; siempre pasar
`var-host` y `var-hostid`.

---

## 3. Varios mapas en un mismo cliente

Un archivo por mapa. Cada uno genera su dashboard con `uid = mapa-<slug>` y se
enlazan entre sí automáticamente.

```
maps/
  cliente-norte.yml       -> /d/mapa-cliente-norte
  cliente-sur.yml         -> /d/mapa-cliente-sur
  cliente-datacenter.yml  -> /d/mapa-cliente-datacenter
```

Para un cliente con muchas sedes (como el caso real con varias zonas), se
recomienda **un mapa por zona** y no un mapa gigante: se lee mejor y cada uno
se actualiza sin tocar el resto.

---

## 4. Generación

```bash
# todos los mapas del directorio, resolviendo hostid por nombre
python3 scripts/gen_map.py --resolve

# uno solo
python3 scripts/gen_map.py --resolve docker/observability/maps/cliente-norte.yml
```

Requiere `ZBX_API_TOKEN` (en `docker/.env` o en el entorno) y `ZBX_API_URL`
(default `http://127.0.0.1/api_jsonrpc.php`, la API detrás de nginx).

---

## 5. Checklist de aceptación

1. El dashboard responde 200 en `/d/mapa-<slug>`.
2. Todos los nodos tienen datos: una consulta por nodo (N/N).
3. Los equipos con problemas activos se ven **rojos** y coinciden con la tabla.
4. La tabla "Problemas de los equipos del mapa" lista solo hosts del mapa.
5. El menú **Mapas** lista todos los mapas del sitio.
6. `python3 scripts/gen_queries.py --check` sigue limpio.

---

## 6. Problemas conocidos

| Síntoma | Causa | Solución |
| --- | --- | --- |
| Todos los nodos verdes con problemas activos | Se usó `trigger.get` para el estado | El generador usa `problem.get`; no cambiar |
| Icono gris en vez de verde/rojo | El `fill` no está atado al campo numérico | Verificar `config.fill.field = c_<i>` y el threshold del panel |
| Nodo sin datos | `hostid` incorrecto o host inexistente | Correr con `--resolve`; revisar el nombre exacto del host |
| El drill-down lista problemas de otros equipos | El link no pasó `var-hostid` | Regenerar el mapa con `gen_map.py` (los links los arma el generador) |
| Flechas superpuestas | Dos equipos comparten columna y fila | Separar los `level` o aumentar `y_gap` |
| Icono no aparece | Nombre de icono inexistente | Usar solo los de la tabla §1 |
