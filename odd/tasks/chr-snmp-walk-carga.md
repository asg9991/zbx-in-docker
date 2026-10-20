# CHR SNMP walks: costo en el router y cortes de gráfica

## Objetivo

Determinar qué SNMP walkMikroTik es el que sale caro para el cliente (consumo
de CPU del agente SNMP en routers CHR que además forwardean ~2.000 sesiones
PPPoE) y eliminar los cortes de las gráficas de tráfico de los nodos MKT.

## Problema

Las gráficas de tráfico por interfaz (NODO 7 - MKT 703 - 40G, MKT 502 - VLANs,
USUARIOS DEDICADOS) se dibujan con saltos de ~306 s. El causa raíz es doble:

1. **Acoplamiento**: los items de tráfico (`net.if.in/out`, `net.vlan.in/out`)
   son *dependent items* (type 18) cuyo master es el walk SNMP. Si el walk
   falla o tarda, la gráfica se corta. Si se desactiva el walk para aligerar
   el router, los dependientes quedan huérfanos y la gráfica se congela.
2. **Volumen**: en los CHR la tabla `ifTable`/dot1q tiene ~2.200 filas y cada
   walk trae 6-17 columnas. Los walks de 6 y 17 columnas nunca completan
   contra el timeout y el MikroTik sigue procesando el walk abortado.

## Medición (2026-10-20, site-a 198.51.100.252)

`snmpwalk` contra cada CHR, con el agente en reposo entre walks (un walk
abortado deja al MikroTik trabajando en background y falsea el siguiente).

| CHR | Filas PPP | Filas ifDescr | PPP walk (1 col) | ifDescr walk |
|---|---|---|---|---|
| 601 | 1452 | 1472 | 1,95 s | 1,79 s |
| 602 | 1409 | 1422 | 1,44 s | 2,06 s |
| 701 | 1713 | 1725 | 6,40 s | 5,86 s |
| 702 | 2438 | 2458 | 5,69 s | 6,30 s |
| 703 | 2174 | 2190 | 8,31 s | 10,48 s |

Caminos multi-columna sobre 2.191 filas (703):

| Walk | Columnas | Varbinds | Tiempo |
|---|---|---|---|
| `net.if.walk` | 8 | ~17.500 | >25 s (timeout) |
| `net.vlan.walk` | 6 | ~13.100 | >25 s (timeout) |
| `net.if.wireless.walk` | 17 | **8.773** | >25 s (timeout) |

Carga estimada por CHR (varbinds/minuto, 703):
`if` 17.528 + `wireless` 8.773 + `vlan` 13.146 + `ppp` 435 ≈ **39.882**.
El walk PPP es **~2,5 %** del total.

Timeout global del server: `ZBX_TIMEOUT=4` (solo aplica a SNMP checks que no
sean `walk[]`/`get[]`; para esos manda el timeout del item).

## Listado: qué consume cada walk

### `net.if.walk` — template 10841 (item 127531) — 8 columnas

| # | OID | Columna | Filas (703) | Consumidor | Estado |
|---|---|---|---|---|---|
| 1 | 1.3.6.1.2.1.31.1.1.1.1 | dot1q nombre | 2191 | `{#IFNAME}` (LLD + 2 filtros) | USADA |
| 2 | 1.3.6.1.2.1.31.1.1.1.18 | dot1q alias | 2191 | `{#IFALIAS}` (LLD + 2 filtros) | USADA |
| 3 | 1.3.6.1.2.1.2.2.1.8 | ifOperStatus | 2191 | proto `net.if.status[]` | USADA |
| 4 | 1.3.6.1.2.1.2.2.1.7 | ifAdminStatus | 2191 | solo `mtxrWlAp.discovery` (**deshabilitada**) | **NO USADA** |
| 5 | 1.3.6.1.2.1.2.2.1.2 | ifDescr | 2191 | `{#IFDESCR}` (LLD + 2 filtros) | USADA |
| 6 | 1.3.6.1.2.1.2.2.1.3 | ifType | 2191 | `{#IFTYPE}` (LLD + 2 filtros) + proto `net.if.type[]` | USADA |
| 7 | 1.3.6.1.2.1.31.1.1.1.6 | dot1q HC in | 2191 | proto `net.if.in[]` | USADA |
| 8 | 1.3.6.1.2.1.31.1.1.1.10 | dot1q HC out | 2191 | proto `net.if.out[]` | USADA |

7 de 8 columnas alimentan la cadena habilitada. La 8ava solo la necesita la
regla WiFi, que está deshabilitada.

### `net.vlan.walk` — template 10869 (item 131403) — 6 columnas

| # | OID | Consumidor | Estado |
|---|---|---|---|
| 1 | 1.3.6.1.2.1.31.1.1.1.1 | `{#IFNAME}` | USADA |
| 2 | 1.3.6.1.2.1.31.1.1.1.18 | `{#IFALIAS}` | USADA |
| 3 | 1.3.6.1.2.1.2.2.1.2 | `{#IFDESCR}` | USADA |
| 4 | 1.3.6.1.2.1.2.2.1.3 | `{#IFTYPE}` | USADA |
| 5 | 1.3.6.1.2.1.31.1.1.1.6 | proto `net.vlan.in[]` | USADA |
| 6 | 1.3.6.1.2.1.31.1.1.1.10 | proto `net.vlan.out[]` | USADA |

**6 de 6 usadas.** Este walk no se puede reducir sin perder el LLD o los
contadores.

### `net.if.wireless.walk` — template 10841 (item 127532) — 17 columnas

| Consumidor | Estado |
|---|---|
| `mtxrLTEModem.discovery` | DESHABILITADA |
| `mtxrWlAp.discovery` | DESHABILITADA |
| `mtxrWlCMChannel.discovery` | DESHABILITADA |

**Cero consumidores habilitados.** Son 8.773 varbinds por minuto (22 % de la
carga) para alimentar tres reglas de descubrimiento apagadas, sobre features
(LTE/WiFi/CAPsMAN) que un CHR de laboratorio no tiene.

### `net.ppp.walk` — template 10870 (item 131645) — 1 columna

| # | OID | Consumidor | Estado |
|---|---|---|---|
| 1 | 1.3.6.1.4.1.14988.1.1.2.1.1.2 | `{#PPP_NAME}` + filtro whitelist | USADA |

1 de 1 usada, delay 5m, timeout 10s. Sus prototipos
(`net.ppp.in/out[{#PPP_NAME}]`, items 131653/131654) son **SNMP_AGENT con
`get[]` directo** — no dependen del walk. Por eso las gráficas de usuarios
dedicados **no** tienen cortes.

## Gráficos que dependen de cada cadena

| Host | Gráficos | net.if | net.vlan | net.ppp |
|---|---|---|---|---|
| SW-EDGE-501 | 7 | 4 | 1 | 2 |
| SW-EDGE-502 | 14 | 4 | 7 | 3 |
| SW-EDGE-602 | 14 | 4 | 8 | 2 |
| SW-EDGE-601 | 23 | 4 | 8 | 11 |
| SW-EDGE-701 | 15 | 4 | 8 | 3 |
| SW-EDGE-702 | 19 | 6 | 12 | 1 |
| SW-EDGE-703 | 9 | 4 | 5 | 0 |

- `net.if.in/out` → por interfaz (PUBLICA, USUARIOS, NAS) + "Interface {#IFNAME}({#IFALIAS}): Network traffic"
- `net.vlan.in/out` → por VLAN + agregados ("MKT 502 - All VLANs Traffic")
- `net.ppp.in/out` → usuarios dedicados
- `net.if.status[]` / `net.if.type[]` → **ningún gráfico**, solo triggers

## Estado live de los walks por host

| Host | net.if.walk | net.if.wireless.walk | net.vlan.walk | net.ppp.walk |
|---|---|---|---|---|
| 501 | activo 8c/1m | activo 17c/1m | activo 6c/1m | activo 1c/5m |
| 502 | activo 8c/5m | activo 17c/1m | activo 6c/5m | activo 1c/5m |
| 602 | activo 8c/1m | activo 17c/1m | activo 6c/1m | activo 1c/5m |
| 601 | activo 8c/1m | activo 17c/1m | activo 6c/1m | activo 1c/5m |
| 701 | **desactivado** | **desactivado** | activo 6c/1m | activo 1c/5m |
| 702 | **desactivado** | **desactivado** | **desactivado** | activo 1c/5m |
| 703 | **desactivado** | **desactivado** | **desactivado** | n/a (sin template PPP) |

Los walks desactivados en 701/702/703 son los que dejaron las gráficas
congeladas: sus dependientes (`134041`-`134049` en 703) quedaron huérfanos.

## Hallazgos laterales

- **501 y 502 están caídos**: no responden SNMP ni ICMP. 601 vive con 35 días
  de uptime. El reporte de "502 dejó de graficar desde 18/10 21:30" es el
  equipo, no la configuración.
- `interface.error` delata el walk culpable por host: 501 →
  `1.3.6.1.4.1.14988.1.1.2.1.1.2` (PPP), 502 →
  `1.3.6.1.4.1.14988.1.1.14.1.1.2` (wireless).
- El item de template `127531` (`net.if.walk`) quedó con OID simple
  `1.3.6.1.2.1.2.2.1.2` (edit manual), mientras los items a nivel host siguen
  con el walk de 8 columnas. Divergencia template/host a corregir.

## Propagación: el cambio va en DOS capas (template + host)

Un cambio de template **no** reescribe los items ya descubiertos en los hosts.
Prueba en vivo (2026-10-20): el item de template `127531` (`net.if.walk`) fue
editado a OID simple `1.3.6.1.2.1.2.2.1.2` con timeout 60s, y los 7 items de
hostansson `walk[8 columnas]` con timeout 300s. La edición nunca llegó.

Consecuencia: el desacople se aplica en dos capas.

| Capa | Qué se modifica | Alcance |
|---|---|---|
| Template (fuente de verdad) | prototipos `net.if.in/out` (127577/127580, tpl 10841) y `net.vlan.in/out` (131405/131406, tpl 10869): type 18 → 20, `snmp_oid` con `{#SNMPINDEX}`, quitar el paso SNMP_WALK_VALUE del preprocessing | 4 prototipos → aplica a hosts futuros y a rediscoveries |
| Host (efecto inmediato) | los items ya descubiertos: type 18 → 20, `snmp_oid` con el índice ya resuelto, `master_itemid` → null, preprocessing sin SNMP_WALK_VALUE | **146 items** en los 7 CHR |

**Por qué no borrar y re-descubrir**: los graphs apuntan a itemids concretos
(ej. graph 7814 usa los items 131477-131489). Al borrar y re-descubrir, los
items nacen con itemid nuevo → se rompen los graphs y se pierde la historia.
`item.update` conserva itemid, clave e historia.

Modelo a copiar: el item PPP descubierto `133880`
(`net.ppp.in[<pppoe-buratovichhnos>]`, type 20, `snmp_oid`
`1.3.6.1.4.1.14988.1.1.2.1.1.8.258013`, sin master) frente al `134041`
(`net.if.in[ifHCInOctets.96]`, type 18, sin OID, master 133979).

Al actualizar un item de host que viene de template, queda como override
local (la UI lo marca como modificado) y deja de seguir al template. Es
aceptable: el cambio estructural es puntual, no algo que deba seguir al
template.

Nota: `type`, `master_itemid`, `snmp_oid` y `preprocessing` deben ir en la
**misma** llamada `item.update`; no se puede pasar de DEPENDENT a SNMP_AGENT
dejando el master puesto.

## Acciones (EJECUTADAS 2026-10-20)

- [x] **A. Desacoplar las gráficas del walk** — prototipos `net.if.in/out`
      (127577/127580), `net.if.status/type` (127582/127583) y
      `net.vlan.in/out` (131405/131406) convertidos de DEPENDENT a SNMP_AGENT
      con `get[]` directo (`1.3.6.1.2.1.31.1.1.1.6/10.{#SNMPINDEX}`),
      sin master y sin el paso SNMP_WALK_VALUE. El walk queda solo como
      fuente del LLD.
- [x] **B. Apagar `net.if.wireless.walk`** (17 columnas, 22 % de la carga,
      cero consumidores habilitados) — deshabilitado en template y en los 7 hosts.
- [x] **C. Quitar las columnas de contadores del walk** — al independizar los
      items, el walk solo necesita identidad: `net.if.walk` 8 → 4 columnas y
      `net.vlan.walk` 6 → 4 columnas (ifAdminStatus nunca se uso en la cadena
      activa; dot1q .6/.10 quedaron en los items directos).
- [x] **D. delay 5m + timeout 60s** en los walks (de 1m/300s), para que no se
      reintenten cada minuto sobre un walk pesado.
- [x] **E. Reactivar el discovery** en 701/702/703 y forzar el rediscovery con
      `task.create` type 6 (Execute now).
- [x] **F. Sincronizar el repo** (`templates/*.yaml`) con el estado vivo.
- [ ] **G. Escalar a O&M** los cortes de 501/502 (equipos caídos) con el
      detalle de carga SNMP medido, que es el insumo para el cliente.

## Mecanismo de propagación (7.4) — lo que había que entender

| Hecho verificado | Consecuencia |
|---|---|
| `template.get` ignora `ids` (usar `templateids`) y devuelve las discovery rules en `discoveryRules` (camelCase) | el export por API no sirve para backup completo |
| `item.get` **no** devuelve las discovery rules ni los item prototypes | hay que usar `discoveryRule.get` / `itemPrototype.get` |
| El API 7.4 no expone preprocessing, filtros ni prototipos de las discovery rules | el backup fiel sale de la DB (`item_preproc`, `item_condition`, `item_discovery`) |
| Los items de host heredados son **inherited objects**: `snmp_oid` y `timeout` son readonly | no se pueden alinear item por item; hay que cambiar el template |
| `delay`, `status` y `type` sí se actualizan en el item de host | con eso se alinearon 19 items |
| El sync template → host **sí propaga** OID, delay y type | las divergencias venían de escrituras directas en DB |
| El sync **no** reescribe los items ya descubiertos por LLD | hay que purgarlos y forzar el rediscovery |
| Una discovery rule dependiente debe tener `delay=0` (su cadencia la hereda del master) | `delay: 1h` en la regla es inválido |
| `task.create` type 6 = "Execute now" para items y discovery rules | es lo que fuerza el rediscovery (el JSON de identidad no cambia, así que la LLD no dispara sola) |
| Al re-descubrir, Zabbix recrea también los `graph_items` de los graph prototypes | los graphs quedan apuntando a los itemids nuevos sin重建 manual |
| Tipos de preprocessing 7.4 (verificados en DB): 1=MULTIPLIER, 10=CHANGE_PER_SECOND, 20=DISCARD_UNCHANGED_HEARTBEAT, 28=SNMP_WALK_VALUE, 29=SNMP_WALK_TO_JSON | no son los de 6.x |

## Resultado

| Métrica | Antes | Después |
|---|---|---|
| Varbinds SNMP por minuto (703) | ~39.900 | ~3.960 (**−90 %**) |
| Columnas del walk de interfaces | 8 + 6 + 17 | 4 + 4 (+ 0) |
| Cadencia de los walks | 1 min | 5 min |
| Items de tráfico | dependent del walk | SNMP_AGENT directos |
| Divergencias host vs template (406 items) | 34 | **0** |
| Gaps > 120 s en los items de tráfico | 15-25 por host | 0 |

Hosts con el cambio aplicado: 601, 602, 701, 702, 703.
Pendiente: **501 y 502**, que están caídos (no responden SNMP ni ICMP). No se
purgaron para no dejar sus gráficas vacías; sus items viejos siguen
funcionando cuando el equipo vuelva, y ahí se aplica el mismo procedimiento.

## Verificación ejecutada

- 0 gaps > 120 s en los items de tráfico de los 5 CHR vivos (los gaps
  restantes en 601/602/701 son anteriores al fix, 15:56-15:58).
- 0 items de tráfico en estado de error; todos con valores nuevos cada 1 min.
- 0 `graph_items` colgando y 0 graphs vacíos en los 7 CHR.
- Divergencia host vs template = 0 en OID, delay, timeout, status y type.
- Repo (`templates/*.yaml`) verificado item por item contra el estado vivo.


## Verificación

- `SELECT ... FROM history_uint` con `LAG(clock)`: ningún hueco > 300 s en los
  items de tráfico de 701/702/703 tras 30 min de A.
- `interface.available = 1` y `interface.error` vacío en los 7 CHR.
- Conteo de varbinds por minuto (snmpwalk) antes/después para confirmar la
  reducción de carga.
- Dashboard: los widgets de NODO 7 y USUARIOS DEDICADOS sin cortes.
