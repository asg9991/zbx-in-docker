# Plantilla unificada "Mikrotik CHR" (Fase 2)

Objetivo: UNA template para los 8 SW-EDGE que reemplace a las 3 actuales
(10841 "Mikrotik by SNMP Modified for CHR", 10869 "Mikrotik VLAN site-a by
SNMP", 10870 "PPP Dedicated Users by SNMP") y al drift host-level (items
system.hw.* + triggers recreados). Alta de CHR nuevo = host + 1 template +
2 macros. Branch: `site-a-hw-mapper`.

## Specs

- S1 (L1): nombre exacto de la plantilla: "Mikrotik CHR".
- S2: contenido: identidad SNMP basica (GETs) + LLD de interfaces (net.if,
  filtrada por {$NET.IF.IFDESCR.MATCHES}, triggers de link down) + LLD
  trapper de VLANs (net.vlan.map/discovery, macros via lld_macro_paths,
  filtro {$site-a.VLAN.MATCHES}) + LLD trapper de dedicados (net.ppp,
  prototipos net.ppp.in/out, trigger "sin trafico" max semantics, graph
  prototype "PPP {#PPP_NAME}: Traffic") + items trapper system.hw.* con
  triggers (CPU avg >85% 10m, disco low/crit, memoria) .
- S3: semantica de triggers: NO min(rate,N)=0; max(rate,N)=0 (falsos
  positivos corregidos en F1).
- S4: migracion por host SIN perder itemids: link de la nueva template ->
  forzar LLD (publicar maps) -> unlink SIN clear de las 3 viejas (los items
  quedan host-level, historial y graphs intactos) -> verificar.
- S5: piloto en 1 host primero; extrapolacion al resto tras verificar.
- S6: al final, las 3 templates viejas quedan sin hosts (retirar si el
  usuario confirma).

## Tasks

- T1: extraer definiciones fuente (10841/10869/10870 + hw de 704) y crear la template "Mikrotik CHR" con todo el contenido (inline)
- T2: piloto de migracion en SW-EDGE-704 + verificacion completa (inline)
- T3: extrapolar a los otros 7 + verificacion (inline)
- T4: limpieza post + docs + reporte (inline) — ✅ (ver docs; incidente del filtro resuelto)
- T5 (Fase 2b, S6): 10885 standalone (herencia removida), 3 templates viejas borradas con backup — ✅ verificado x8
- T6 (L4): interfaces al mapper: mapper publica net.if.map (JSON [{index, ifdescr}] filtrado por la macro del host leida por psql); LLD trapper en 10885 con lld_macro_paths + prototipos; baja del walk+LLD viejo; re-apuntar uplinks (inline)

## Log

- L1 (2026-10-27): usuario confirma: "Arrancamos con la plantilla. Nombre
  de plantilla: Mikrotik CHR" y luego "Dale nomas".
- Estrategia S4 elegida porque unlink+clear BORRA los items descubiertos
  (y sus itemids, rompiendo graphs del dashboard); unlink sin clear los
  vuelve host-level conservando ids; la LLD nueva adopta items existentes
  por key.

- L2 (2026-10-28): migracion aplicada x8 con herencia; itemids preservados; filtro unificado en template; incidente de discovery sin filtro resuelto con lifetime=0 temporal.

- L3 (2026-10-28): Fase 2b completa. Las 3 templates viejas retiradas; 10885 es la unica template del monitoreo EDGE.

- L4 (2026-10-28, SIN CERRAR - rotura del LLD de interfaces): al borrar las 3
  templates viejas, el cascade dejo atados a los prototipos viejos a los items
  descubiertos y quedaron deshabilitados en varias olas (audit: 11:18, 11:22,
  12:04, 12:13). Estado actual: VLANs/PPP/hw funcionando (mapper, intactos);
  **interfaces (uplinks) SIN monitoreo**: items descubiertos borrados/zombis,
  el net.if.walk colecciona (verificado con history temporal: 1.341 filas,
  0,5 s) pero el LLD no redescubre. Corregido en el camino: filtro de la regla
  a 6 condiciones (IFALIAS/IFDESCR/IFNAME), macros {$NET.IF.IFALIAS.*} agregadas
  a la template (faltaban = filas rechazadas), walk reducido a 1 columna
  (ifDescr) + preprocessing acorde, timeout 60s. Todavia no redescubre.
  Items uplink re-habilitados varias veces; las LLD viejas los volvian a
  deshabilitar. Los graphs de uplink (7042/7080/8198/8645) existen pero sus
  items fueron borrados -> habra que re-apuntar tras redescubrir.
  HIPOTESIS PENDIENTE: el valor del walk[4 columnas] y el formato que espera el
  preprocessing walk-to-JSON de la regla pueden no calzar; probar con el valor
  real del walk (activar history y ver) contra el formato esperado, o migrar
  la discovery de interfaces al mapper (patron VLANs) y liquidar el walk.
  REGLA: no seguir toqueteando items a mano; diagnosticar el formato primero.

- L5 (2026-10-28): T6 COMPLETADO — discovery de interfaces por mapper+trapper,
  walk pesado eliminado, uplinks re-apuntados y verificados x6.

- L6 (2026-10-28, PENDIENTE - metricas mal): los prototipos net.if.in/out nuevos
  NO tienen el "change per second" (delta): grafican el CONTADOR crudo x8
  (Tbps absurdos). En 7.4 delta NO es preprocessing type 2 (verificado: type 2
  rechazado en prototype.update con "params/1 cannot be empty" y items
  descubiertos tienen preprocessing readonly; la tabla items no tiene columna
  delta). Los items discovereds heredan preprocessing del prototipo (readonly),
  o sea que el fix es SOLO en el prototipo 158091/158100 con el type correcto
  de delta en 7.4 (mirar el numero de tipo en la UI de un item viejo o docs
  7.4). Falta ademas:
  a) borrar la historia corrupta ya hecho (DELETE history_uint > 13:00),
  b) re-apuntar uplinks 702/703 (widgets 67525/67517 sin campo graphid;
     graphs nuevos "Interface PUBLICA(): Network traffic" por host ya existen),
  c) reconstruir los graphs combinados de VLANs de 601/701/702/703 (sus items
     viejos fueron borrados; los nuevos por LLD ya existen; rehacer gitems
     sent-colors/received-grays),
  d) insertar campos graphid.0 (type=6) para los widgets de VLANs 601/701/702/703.

- L7 (2026-10-28, CERRADO): metricas corregidas. En 7.4 "Change per second" es
  preprocessing type 10 con params VACIO (type 2 NO existe; mi error inicial).
  Aplicado a los prototipos net.if.in/out (cascada a los descubiertos), historia
  corrupta borrada, uplinks 702/703 re-apuntados (13057/13060) y graphs de
  VLANs de 601/701/702/703 reconstruidos (13074-13077; 602 y 704 conservan los
  originales 7816/8646). Verificado: 0 widgets rotos, valores en Mbps.

- L8 (2026-10-28): ajustes finos. Triggers huerfanos de CPU borrados (6: 43598-43603,
  quedaban duplicados por templates viejas) -> 1 por host. Items hw renombrados sin
  "(trapper, mapper)" en template 10885. Uplinks con linea verde en gradiente
  (drawtype 5 en prototipo 13042 + propagado). Widget 704 VLANs apuntado al graph
  nuevo 13078 (el 8646 original habia sido borrado en la limpieza).

- L9 (2026-10-28): dedicados PPP corregidos. Causa raiz: el mapper leia la
  whitelist {$PPP.DEDICATED.MATCHES} del template 10870 (BORRADO en la fase 2b)
  -> leia nada -> 0 dedicadas -> LLD vacio -> items/graphs borrados. Fix:
  template_hostid 10870 -> 10885 en vlan_mapper_config.json (y default del py).
  Ademas: normalizacion de nombre "Enlace-patrullarural" -> "<pppoe-patrullarural>"
  en el mapper (mismo estilo que el resto). Graphs "Usuario <pppoe-X>" recreados
  (13089-13096) y 8 widgets re-apuntados (67621-67628), incl. widget de
  patrullarural renombrado. Verificado: items_ok=2 en los 8, datos llegando.

- L10 (2026-10-28): documentacion del metodo de graficos. Nuevo
  docs/graficos-site-a.md (modelo item->graphs_items->graphs->widget_field->
  widget, codigos verificados 7.4, 4 patrones golden, receta de 6 pasos,
  13 minas, query de salud, inventario de IDs). dashboard-update.md y
  zbx-index apuntan ahi; vlan-lld-site-a.md cierra Fase 2d y limpia el bullet
  obsoleto del 10870. Mina nueva detectada y corregida: los INSERT directos
  habian dejado ids.nextid por detras de max -> proxima creacion por API
  colisionaba (widget_field 298442 < max 298463). Estado verificado del
  dashboard 1: 0 widgets graph rotos de 81.
