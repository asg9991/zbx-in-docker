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

## Acciones (pendiente de decisión)

- [ ] **A. Desacoplar las gráficas del walk** — convertir los prototipos
      `net.if.in/out` (127577/127580) y `net.vlan.in/out` (131405/131406) de
      DEPENDENT a SNMP_AGENT con `get[]` directo
      (`1.3.6.1.2.1.31.1.1.1.6/10.{#SNMPINDEX}`). Es el patrón que ya usa el
      template PPP y elimina los cortes de raíz. Requiere cambiar el
      preprocessing de los prototipos y re-sincronizar los items de host.
- [ ] **B. Apagar `net.if.wireless.walk`** (17 columnas, 22 % de la carga,
      cero consumidores habilitados).
- [ ] **C. Quitar la columna `ifAdminStatus` de `net.if.walk`** (7/8 columnas
      usadas; la 8ava solo la usa la regla WiFi apagada).
- [ ] **D. Subir delay de los walks restantes a 5m y fijar timeout 60s**, para
      que no se reintenten cada minuto sobre un walk que no completa.
- [ ] **E. Reactivar los walks de discovery** en 701/702/703 una vez
      desacoplados los items (A), con delay 5m.
- [ ] **F. Sincronizar el repo** (`templates/*.yaml`) con el estado vivo
      post-cambio y mover el backup de `templates/backup/2026-10-20/` a la
      posición canónica.
- [ ] **G. Escalar a O&M** los cortes de 501/502 (equipos caídos) con el
      detalle de carga SNMP medido, que es el insumo para el cliente.

## Verificación

- `SELECT ... FROM history_uint` con `LAG(clock)`: ningún hueco > 300 s en los
  items de tráfico de 701/702/703 tras 30 min de A.
- `interface.available = 1` y `interface.error` vacío en los 7 CHR.
- Conteo de varbinds por minuto (snmpwalk) antes/después para confirmar la
  reducción de carga.
- Dashboard: los widgets de NODO 7 y USUARIOS DEDICADOS sin cortes.
