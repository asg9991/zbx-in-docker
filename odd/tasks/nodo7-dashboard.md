# Feature: nodo7-dashboard

## Objective
Sumar NODO 7 (SW-EDGE-701/702) a la pestaña NODOS del Global view con PPP active users y graphs Interface PUBLICA.

## Problem
701/702 existen pero no figuran en NODOS; 701/702 no tienen items PPP y el dashboard no los referencia.

## Why
Pedido cliente: cada nodo de 2 mikrotik muestra PPP + PUBLICA. NODO 7 debe quedar como los anteriores.

## Scope
- Solo dashboard 1 Global view, página NODOS (pageid 17679).
- Crear par PPP (raw + count) en 10877/10878 copiando 401/402.
- Agregar hostids a widgets 65994/65995 y 2 widgets graph (8198/8213) en y34/y39.
- No tocar VLAN POR NODO en esta tarea.

## Constraints
- dashboard.update REEMPLAZA todo: full-payload clonado y validado antes. Cero escrituras parciales.
- Route: delegated direct (un writer). Checks: item.get + dashboard.get readback.
- Mantenimiento 3 activo en 701/702 (suprime ruido pero sigue colectando).

## Tasks
- [x] T1 Crear PPP raw+count en 701/702 [route: delegated]
- [x] T2 Update dashboard NODOS con hostids + 2 graphs [route: delegated]
- [x] T3 Readback y validación [route: delegated]

## Authorized scope
Usuario autorizó 2026-10-08: "Si, crear y sumar". Solo pág 17679. Push/PR: decisiones del usuario.

## Progress
- 2026-10-08: mapeo NODOS completo (8 widgets, PPP por hostids, PUBLICA 8198/8213 con datos). Pendiente T1-T3.
- 2026-10-08: T1-T3 ejecutados. PPP creados, dashboard actualizado a 10 widgets, readback OK. Count pendiente de próximo poll (fix JS aplicado).
- 2026-10-08: procedimiento dashboard.update full-payload curado en docs/dashboard-update.md.

## Verification evidence
- T1 PPP nuevos: 701 raw 133656 (interface 171, SNMP walk ppp, 3m/2d/0, con datos lastclock 1791465216) + count 133657 (dependent master 133656, JS <pppoe-); 702 raw 133658 (interface 172, con datos lastclock 1791465218) + count 133659 (dependent master 133658). Fuente: 130273/130279 (401) y 130280/130285 (402), mismo OID walk[1.3.6.1.4.1.14988.1.1.14.1.1.2], mismo delay/history/trends, tag component=network. item.get verifica 4 items habilitados state raw 0 sin error.
- T1 fix: JS inicial sin comillas (split(\\n)) daba SyntaxError invalid escape en 133657/133659; corregido vía item.update copiando preprocessing exacto de 130279 (split('\n')). Error residual es valor cacheado anterior; se limpia en próximo poll master (≤3m, sin reload forzado). Mantenimiento 3 suprime ruido.
- T2 dashboard 1: validación previa 11 pages, NODOS 17679 con 8 widgets (65994/65995 + 65996-66001), hostids orden 10842,10843,10844,10845,10848,10846. Un solo dashboard.update full-payload (11 pages, 34869 bytes): 65994/65995 suman hostids.6=10877 + hostids.7=10878; 2 widgets nuevos graph w72 h5 x0 y34 (NODO 7-701 graphid 8198, ref N7Q01) y x0 y39 (NODO 7-702 graphid 8213, ref N7Q02). Result dashboardids ["1"].
- T3 readback dashboard.get: NODOS 17679 con 10 widgets (65994/65995 con 8 hostids + 6 graphs previos + 66080 y34/8198 + 66081 y39/8213). Otros pages intactos (17676:5, 17677:1, 17678:7, 17680 VLAN:6, 17681:3, 17682:18, 17655:4, 17683:24, 17684:21, 17685:2). No se tocó VLAN POR NODO, no borrados, no reloads. Temporales /tmp borrados.
