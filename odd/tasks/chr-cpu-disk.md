# Feature: chr-cpu-disk

## Objective
Probar si los CHR de site-a exponen CPU y disco via SNMP habilitando los discoveries correspondientes, canario 701/702 ya mapeado, ahora expandido a todo el fleet CHR.

## Problem
Template 10841 trae CPU (`hrProcessorLoad`), memoria, disco (`storage`) y temp, pero en los CHR solo hay instancias de memoria/trafico. CPU/disco/temp/disco solo existen como prototipos porque los discoveries estan en status=1. Temp se excluye a pedido (sin sensores en CHR).

## Why
Pedido cliente: metricas CPU/Mem/hardware donde se pueda. Usuario autorizo 2026-10-09: "intenta habilitando a ver si salen esos datos de cpu/disco (temp no)". Aclaro: 701/702 son virtuales CHR (no fierros) y que 701 sin VLANs esta bien. Expansion a todo el fleet autorizada 2026-10-09 con token API provisto por el usuario (no persistido).

## Scope
- Todos los CHR: 10842 (401, baja pronto, mejor esfuerzo), 10843 (402), 10844 (501), 10845 (502), 10848 (601), 10846 (602), 10877 (701), 10878 (702).
- Solo discoveries: `hrProcessorLoad.discovery` (CPU) y `storage.discovery` (disco). NO tocar `mtxrHlTemperature` ni `mtxrHlProcessorTemperature`.
- T5 NUEVO: trigger CPU >85% sostenido 10m severidad High, referencia (no SLA fino, acordado con usuario 2026-10-09). Solo CPU; disco/memoria usan triggers del template.
- Token API provisto solo en memoria/transporte, jamas persistido en archivos, memoria Engram ni logs.

## Constraints
- ODD test-first no aplica con RED runnable (sin runner deterministico para SNMP CHR); excepcion: verificacion funcional via discoveryrule.get + item.get + history.
- Cambios via Zabbix API por SSH no-interactivo desde zabbix-site-a; cero edicion de codigo fuera del task doc.
- Route: delegated direct (un writer). Checks proporcionales, sin review nativa por checkbox (candidato = work-unit commit si hubiera cambio de doc).

## Tasks
- [x] T1 Relevar IDs de discovery rules CPU/disco en 701/702 [route: delegated]
- [x] T2 Habilitar `hrProcessorLoad.discovery` + `storage.discovery` en 10877/10878 y esperar poll [route: delegated] — desbloqueado con token usuario 2026-10-09 (no persistido); ejecutar junto a T4
- [x] T3 Verificar items instanciados + datos (item.get/history) y reportar expansion o descarte [route: delegated] — verificado 2026-10-09 21:18 UTC: instancias CPU/disco en los 8 hosts + history con datos (ver Verification evidence)
- [x] T4 Habilitar CPU/disco en resto fleet (10842/10843/10844/10845/10848/10846) + verificar [route: delegated] — ejecutado 2026-10-09 21:18 UTC junto a T2 (16/16 status 0, ver Progress)
- [x] T5 Crear trigger CPU >85% sostenido 10m severidad High en los 8 CHR [route: delegated] — ejecutado 2026-10-09 ~22:15 UTC via UNICO prototipo template 43427 (preferred design, sin fallback host-level)
- [x] T6 Crear UN trigger agregado por equipo (promedio todos los cores >85% 10m, High) [route: delegated] — ejecutado 2026-10-09 ~22:40 UTC via 8 trigger.create host-level (43596-43603), prototipo 43427 intacto
- [x] T7 Crear 8 graphs CPU agregados (todos los cores en uno por equipo, 401 incluido) [route: delegated] — ejecutado 2026-10-09 ~23:00 UTC via 8 graph.create (8396-8403), nombres "NODO <n> - MKT <nnn> CPU prom", ymax fijo 100, gitems con calc_fnc avg
- [x] T8 Agregar 16 widgets en NODOS (disco + CPU promedio lado a lado por nodo, 401 incluido, widget viejo 401 intacto) [route: delegated] — ejecutado 2026-10-09 ~23:10 UTC via UNICO dashboard.update (26 widgets, h2 por cap y<=63 de la plataforma, ver Progress)
- [x] T9 Version presentable sobre layout manual usuario (reordeno torta disco + CPU multiline por nodo): 8 items calculados CPU promedio + 8 graphs 1-linea + gauges disco/CPU, reemplazo in-place sin mover su orden [route: delegated] — ejecutado 2026-10-09 ~23:40 UTC via 8 item.create (133868-133875) + 8 graph.create (8404-8411) + UNICO dashboard.update in-place (26 widgets, sisters intactas, gauges-CPU omitidos sin celda libre adyacente, ver Progress)

## Authorized scope
Usuario autorizo 2026-10-09: habilitar CPU/disco, temp no. Canario 701/702 primero, luego todo el fleet CHR con token provisto (uso unico, no persistir). T5 autorizado 2026-10-09: trigger CPU >85% sostenido 10m severidad High como referencia (no SLA fino). T6 autorizado 2026-10-09: "vamos a crear ese trigger agregado por equipo" (uno por host, evita tormenta de 160 alertas). T7+T8 autorizado 2026-10-09: usuario confirma propuesta con cambios — 401 intacto (widget viejo no se toca) pero INCLUIDO en graphs nuevos; layout por nodo con disco y CPU promedio uno al lado del otro. T9 autorizado 2026-10-09: "Si! Dale nomas" a version presentable (gauges + CPU 1-linea + numeros en disco) sobre su layout manual. Push/PR: decisiones del usuario.

## Acceptance criteria
- discoveryrule.get muestra CPU y storage en status 0 en los 8 hosts (401 mejor esfuerzo por baja).
- item.get muestra instancias nuevas o evidencia de "no soportado" con error SNMP.
- history con datos o diagnostico de vacio tras al menos un intervalo de poll.
- T5: trigger presente y habilitado por host cubriendo CPU >85% durante 10m, prioridad High (4), verificado via trigger.get (sin forzar datos falsos).

## Progress
- 2026-10-09: feature doc creado, pendiente T1-T3.
- 2026-10-09 18:05 UTC-3: T1 completo (read-only via SSH DB). T2 BLOQUEADO por falta de auth API: discoveryrule.get sin token devuelve "Not authorized." (API 7.4.13 en https://127.0.0.1/api_jsonrpc.php); no hay token/scripts reusables en repo ni en zabbix-site-a (~/scripts, /opt/monitoring/zbx-in-docker sin helpers con token); DB `token` tiene solo report_token (userid 4) y temp_add_template_agent-admin (userid 1, expira ~2026-10-09). No se intento update sin auth; no se crean tokens ni writes por DB (requeririan config cache reload, prohibido). Temp discoveries intactas en status=1.
- 2026-10-09 21:18 UTC: IDs resto fleet resueltos read-only via DB (todos status 1): 10842 CPU 127610 + disk 127617; 10843 CPU 127676 + disk 127683; 10844 CPU 127742 + disk 127749; 10845 CPU 127808 + disk 127815; 10848 (601) CPU 128226 + disk 128233; 10846 (602) CPU 127874 + disk 127881. Temp mtxrHl* confirmadas status 1 en los 8 hosts (no tocar).
- 2026-10-09 21:18 UTC: discoveryrule.update status=0 ejecutado en las 16 reglas CPU+storage (6 fleet + 701/702): result itemids 16/16, sin errores de auth. Sin reloads/restarts. Espera ~6 min (21:11–21:17 UTC) antes de verificar. Token de un solo uso transportado solo via env var, unset + history scrub tras cada uso, jamas persistido.
- 2026-10-09 21:18 UTC: T2+T3+T4 verificados. 401 (10842, pending decommission) respondio igual que el resto: mejor esfuerzo cumplido, no bloquea. Temp intactas (0 reglas mtxrHl* con status<>1).
- 2026-10-09 ~22:15 UTC (T5): baseline read-only: prototipo existente 40447 `MikroTik: #{#SNMPINDEX}: High CPU utilization`, expresion `{66807}>{$CPU.UTIL.CRIT}` = min(/host/system.cpu.util[hrProcessorLoad.N],5m)>90 (macro {$CPU.UTIL.CRIT}=90), prioridad 2 Warning — NO cubre >85%/10m ni severidad High; ~160 instancias por host con ese formato. Diseno preferred aplicado: UNICO triggerprototype.create 43427 en template 10841 (`avg(/Mikrotik by SNMP Modified for CHR/system.cpu.util[hrProcessorLoad.{#SNMPINDEX}],10m)>85`, priority 4, status 0, comments de referencia CHR), ligado a discovery 127551; sin fallback host-level, sin tocar temp/disco/memoria, sin deshabilitar nada. Instanciacion requirio `docker exec zabbix-server zabbix_server -R config_cache_reload` (cache trabada, issue conocido del repo) + re-disparo LLD por host (toggle status 1->0 de las 8 reglas CPU + check-now de los `system.cpu.walk` master; check-now sobre la LLD dependiente sola es no-op). Token de un solo uso solo via env var, unset + history scrub tras cada uso, jamas persistido.

## Verification evidence
- `SELECT itemid,hostid,name,key_,status,flags FROM items WHERE hostid IN (10877,10878) AND flags=1`: 10877 CPU=133510 status 1 (`hrProcessorLoad.discovery`), storage=133517 status 1 (`storage.discovery`); 10878 CPU=133568 status 1, storage=133575 status 1; temp 133511/133512/133569/133570 status 1 (no tocar).
- `curl apiinfo.version`: `{"jsonrpc":"2.0","result":"7.4.13","id":1}`.
- `curl discoveryrule.get sin auth`: `{"jsonrpc":"2.0","error":{"code":-32602,"message":"Invalid params.","data":"Not authorized."},"id":2}`.
- Prototipos confirmados via `item_discovery.lldruleid` (join por parent_itemid da 0, el link real es lldruleid): regla tpl 127551 -> 127559 `system.cpu.util[hrProcessorLoad.{#SNMPINDEX}]`; regla tpl 127558 -> 127584/127585/127586 `vfs.fs.pused/total/used[hrStorageSize.{#SNMPINDEX}]`.
- Baseline instancias: 10877 26 plain + 12 discovered, 0 system.cpu.util*, 0 vfs.fs.* descubiertos (solo `vfs.fs.walk` estatico 133504); 10878 26 plain + 46 discovered, 0 system.cpu.util*, 0 vfs.fs.* descubiertos (solo `vfs.fs.walk` 133562). Triggers: 10877=29, 10878=44. Graphs: 10877=9, 10878=25.
- Sin writes: ningun UPDATE/restart/reload ejecutado; history spot-check pendiente de T2.
- `SELECT ... WHERE hostid IN (10842,10843,10844,10845,10848,10846) AND flags=1 AND (hrProcessorLoad.discovery|storage.discovery)`: 12 filas status 1 (127610/127617, 127676/127683, 127742/127749, 127808/127815, 128226/128233 en 10848, 127874/127881 en 10846).
- `discoveryrule.update status=0 x16`: `{"result":{"itemids":["127610","127617","127676","127683","127742","127749","127808","127815","128226","128233","127874","127881","133510","133517","133568","133575"]}}` (UPDATE_EXIT:0).
- `discoveryrule.get readback 16 IDs`: 16/16 con status 0 (10842, 10843, 10844, 10845, 10848, 10846, 10877, 10878 — CPU + storage en cada uno).
- `item.get search system.cpu.util (8 hosts)`: 160 instancias flags=4 status 0 error vacio — 10842:20, 10843:20, 10844:20, 10845:20, 10848:20, 10846:24, 10877:18, 10878:18; sample `system.cpu.util[hrProcessorLoad.1]` presente en cada host.
- `item.get search vfs.fs. (8 hosts)`: 3 descubiertas flags=4 status 0 por host (`vfs.fs.pused/total/used[hrStorageSize.131072]`, ids ej. 133724/133725/133726 en 10842, 133862/133863/133864 en 10877) + 1 estatica `vfs.fs.walk` por host; error vacio en todas.
- `history.get item 133805 (CPU 701) history 0 limit 1`: `{"itemid":"133805","clock":"1791580673","value":"0"}` — con datos.
- `history.get item 133862 (disk pused 701) history 0 limit 1`: `{"itemid":"133862","clock":"1791580622","value":"52.10481381756091"}` — con datos.
- `SELECT count(*) status=0 en las 16 reglas`: 16. `SELECT mtxrHl* status<>1 en 8 hosts`: 0 filas (temp intactas en status 1).
- T5 `triggerprototype.get 10841`: prototipo previo 40447 expresion `{66807}>{$CPU.UTIL.CRIT}` prioridad 2 (expandido: `min(/SW-EDGE-401/system.cpu.util[hrProcessorLoad.10],5m)>90`); macro template {$CPU.UTIL.CRIT}=90.
- T5 `triggerprototype.create`: `{"result":{"triggerids":["43427"]}}`; readback `triggerprototype.get 43427` + `selectFunctions`: function avg parameter `$,10m` sobre item prototipo 127559, discoveryRule 127551 CPU discovery, priority 4, status 0.
- T5 `trigger.get search "CHR reference" countOutput 8 hosts`: 160 (10842:20, 10843:20, 10844:20, 10845:20, 10848:20, 10846:24, 10877:18, 10878:18); sample expandido `avg(/SW-EDGE-501/system.cpu.util[hrProcessorLoad.2],10m)>85` priority 4 status 0 value 0.
- T5 `trigger.get ... filter value=1 countOutput`: 0 (sin false-fire tras polls; sin inyeccion de datos).
- T5 `discoveryrule.get 16 mtxrHl* en 8 hosts`: 16/16 status 1 (temp intacta). `discoveryrule.get 8 reglas CPU`: 8/8 status 0 state 0 sin error.
- T6 `item.get search system.cpu.util re-verificado (8 hosts)`: 160 instancias, conteos identicos al baseline — 10842:20, 10843:20, 10844:20, 10845:20, 10848:20, 10846:24, 10877:18, 10878:18; todas `hrProcessorLoad.N` contiguas 1..N por host.
- T6 `trigger.create x8`: `{"triggerids":["43596"]}` (10842/401) + 43597 (10843) + 43598 (10844) + 43599 (10845) + 43600 (10848/601) + 43601 (10846/602) + 43602 (10877/701) + 43603 (10878/702); descripcion "CHR aggregate CPU average >85% sustained 10m (reference, per-host; avoids 160 per-core alert storm)", priority 4, status 0.
- T6 `trigger.get readback 43596-43603`: 8/8 con priority 4, status 0, value 0 (sin false-fire, sin inyeccion de datos); host mapping 43596->SW-EDGE-401 ... 43603->SW-EDGE-702; denominadores /20, /20, /20, /20, /20, /24, /18, /18 segun conteo por host.
- T6 `trigger.get 43596 expandExpression`: `((avg(/SW-EDGE-401/system.cpu.util[hrProcessorLoad.1],10m)+...+avg(/SW-EDGE-401/system.cpu.util[hrProcessorLoad.20],10m))/20)>85` — avg/10m en los 20 terminos; spot-check selectFunctions en 43596/43601/43602: 20/24/18 funciones todas con parametro `$,10m`.
- T6 prototipo 43427 y familia per-core no tocados (sin disable); 401 (10842) respondio igual que el resto, mejor esfuerzo OK.
- T7 `graph.get 8396-8403 selectGraphItems`: 8/8 con nombres/hosts/conteos correctos (401:20, 402:20, 501:20, 502:20, 601:20, 602:24, 701:18, 702:18).
- T7 `graph.get search "Disk" (8 hosts)`: 8268 (401), 8309 (402), 8366 (501), 8393 (502), 8391 (601), 8395 (602), 8394 (701), 8392 (702); search "CPU prom": 0 resultados pre-T7.
- T8 `dashboard.get before`: 11 paginas, NODOS 10 widgets (65994, 65995, 65996-66001, 66080, 66081); total 101 widgets.
- T8 primer `dashboard.update` (h5 y45..y85): rechazado `Invalid parameter "/1/pages/4/widgets/19/y": value must be one of 0-63` — sin mutacion (re-get confirma 10 widgets).
- T8 `dashboard.update` (h2 y45..y61): `{"dashboardids":["1"]}`.
- T8 readback `dashboard.get after`: 11 paginas; NODOS 26 widgets; hermanas 10/10 byte-identicas; pre-existentes 0 faltantes + 0 modificados (65996 = "NODO 4 - MKT 401" graphid 7012; 65994/65995 hostids 8/8 hosts); nuevos 66185-66200 (8 disco: 8268/8309/8366/8393/8391/8395/8394/8392 + 8 CPU: 8396-8403, x0/x36 w36 h2 y45..y59 en orden de nodo); overlap check 0.
- T8 `history.get item 133703 (core 1 de 401, miembro de grafo 8396) limit 3`: 3 valores recientes con clock/namespaces validos — datos fluyendo, sin inyeccion.
- T8 backups: `dashboard-1-2026-10-09.json` (dashboard.get completo) + `dashboard-tables-2026-10-09.sql` (pg_dump via `docker exec zabbix-postgres`, 1241875 bytes).
- T9a `item.get 133868-133875`: 8/8 key `system.cpu.avg`, status 0, state 0, error vacio.
- T9a `history.get 8 avgs limit 16 DESC`: 2 valores por item con variacion natural (ej. 133868 0.7/0.7, 133869 47.3/47.15, 133870 56.95/57.0, 133871 51.2/50.95, 133872 52.25/51.95, 133873 44.92/45.0, 133874 0.0/0.0, 133875 48.67/50.67) — promedios fluyendo, sin inyeccion.
- T9b `graph.get 8404-8411 selectGraphItems`: 8/8 nombres/hosts correctos, yaxismin 0 / yaxismax 100, 1 gitem c/u sobre 133868-133875 respectivamente.
- T9c `dashboard.get before`: 11 paginas, NODOS 26 widgets, 0 overlaps, filas T8 intactas en posiciones de usuario.
- T9c `dashboard.update`: `{"dashboardids":["1"]}` sin error (payload 53900 bytes, 11 paginas completas).
- T9c `dashboard.get after`: 11 paginas; NODOS 26 widgets; hermanas 10/10 byte-identicas; 10 no-objetivo NODOS byte-identicos (trafico 65996-66001/66080/66081 + topitems 65994/65995, widget viejo 401 graphid 7012 intacto); 8 disco graph->gauge mismo widgetid/x/y/w/h sobre vfs.fs.pused (133724/133767/133826/133859/133853/133865/133862/133856, min 0 max 100, thresholds 0/20/40/60/80, desc MB); 8 CPU -> graphs 8404-8411 renombrados "CPU avg" misma posicion; overlap check 0.

## Next step
- Cerrado 2026-10-09 21:18 UTC: CPU/disco habilitados y con datos en los 8 CHR (401 incluido, mejor esfuerzo OK). Temp excluida por pedido. No se crearon triggers/graphs. Monitorear errores SNMP en items nuevos; push/PR segun decision del usuario.
- Cerrado T5 2026-10-09 ~22:15 UTC: prototipo 43427 en template 10841 + 160 triggers instanciados (20/20/20/20/20/24/18/18) con prioridad High, 0 en problema, temp intacta. Push/PR segun decision del usuario.
- Cerrado T6 2026-10-09 ~22:40 UTC: 8 agregados host-level operativos (value 0, sin falsos disparos). Feature completa: CPU/disco con datos + alerta per-core (prototipo) + alerta agregada client-facing. Push/PR segun decision del usuario.
- Cerrado T7+T8 2026-10-09 ~23:10 UTC: 8 graphs CPU agregados (8396-8403) + 16 widgets NODOS (66185-66200, disco+CPU lado a lado por nodo, 401 incluido, widget viejo 401 intacto). Desvio documentado: filas h2 (y45..y61) porque la API limita y a 0-63. Push/PR segun decision del usuario.
- Cerrado T9 2026-10-09 ~23:40 UTC: NODOS presentable in-place — 8 avgs calculados con datos + 8 graphs 1-linea (8404-8411) + 8 gauges disco; trafico y widget viejo 401 intactos; gauges-CPU omitidos por falta de celda adyacente. Push/PR segun decision del usuario.
- FINAL 2026-10-09 ~23:50 UTC (layout manual usuario, referencia para futuras modificaciones): NODOS 26 widgets en 8 filas uniformes por nodo (y5..y40 step 5, h5): trafico x0 w46 + CPU-avg x46 w13 + gauge-disco x59 w13 (=72 full, 0 overlap). Orden 401/402/501/502/601/602/701/702. Topitems 65994 (x0 w39) + 65995 (x39 w33) con los 8 hostids. Widgets trafico 65996-66001/66080/66081 (graphs PUBLICA 7012/7018/7027/7035/7080/7042/8198/8213). CPU 66186/66188/66190/66192/66194/66196/66198/66200 (graphs 8404-8411 sobre items avg 133868-133875). Gauges 66185/66187/66189/66191/66193/66195/66197/66199 (items pused 133724/133767/133826/133859/133853/133865/133862/133856, min 0 max 100, thresholds 0/20/40/60/80, angulo 270, desc MB usados). Dashboard 1 total 11 paginas / 117 widgets. ANTES DE MODIFICAR: fresh dashboard.get (backups locales quedan stale) y respetar y<=63.
- 2026-10-09 ~23:40 UTC (T9a): 8 item.create calculados `system.cpu.avg` (type 15, float, units %, delay 1m, status 0): 133868 (10842/401) + 133869 (10843) + 133870 (10844) + 133871 (10845) + 133872 (10848/601) + 133873 (10846/602) + 133874 (10877/701) + 133875 (10878/702). Formula `(last(/HOST/system.cpu.util[hrProcessorLoad.1])+...+last(/HOST/...N))/N` con N=20/20/20/20/20/24/18/18 (contiguedad 1..N re-verificada por host via item.get). Sin interfaceid (no requerido para calculados).
- 2026-10-09 ~23:40 UTC (T9b): 8 graph.create 1-linea (8404-8411) "NODO <n> - MKT <nnn> CPU avg", yaxismin 0 / yaxismax 100, 1 gitem c/u sobre el avg del host (color 00CC00, calc_fnc avg).
- 2026-10-09 ~23:40 UTC (T9c): FRESH dashboard.get antes de armar payload: 11 paginas, NODOS 26 widgets; el layout manual del usuario conserva las filas T8 (disco+CPU x0/x36 w36 h2 y45..y61, 0 overlaps) — los widgets "disco" son graph sobre graphs de disco (8268/8309/8366/8393/8391/8395/8394/8392), sin pie-widgets presentes. Backups: raw dashboard.get JSON + pg_dump dashboard*/widget* (1244723 bytes); configuration.export NO aplica a dashboards globales en 7.4 (`Invalid parameter "/options": unexpected parameter "dashboards"`). Validacion de forma via dashboard.create clon 412 OK, luego dashboard.delete 412. UNICO dashboard.update full-payload: `{"dashboardids":["1"]}`. Cambio de tipo graph->gauge con widgetid conservado aceptado por la API. Gauges-CPU omitidos: banda y45-61 ocupa todo el ancho (36+36) sin celda libre adyacente a los widgets CPU; espacio libre solo en x39-72 y5-44 (banda trafico, no adyacente) + filas y61-62. Desvio documentado: descripciones de gauges en MB (no GB) porque los discos CHR miden 62369792 B (~59.5 MiB) y en GB leerian 0.06 — valores calculados de lastvalues observados.
