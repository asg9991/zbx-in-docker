# Limpieza EDGE Fase 1 (dedicados legacy, items muertos, LLD muertas)

Objetivo: eliminar los mecanismos duplicados y la masa muerta de los 8 SW-EDGE
sin perder monitoreo ni dashboard, como paso previo a la plantilla unificada
"Mikrotik CHR". Branch: `site-a-hw-mapper`. Tests: `python3 scripts/test_vlan_mapper.py`.

## Specs

- S1 (L2): los dedicados de 601/602 (Enlace-arrebeef, Enlace-franciscosellart,
  Enlace-multijactosa, Enlace-patrullarural) pasan del LLD legacy
  `dedicados.ppp.discovery` (SNMP walk 10m, host-level) al mecanismo
  mapper+trapper (`net.ppp.*`, whitelist `{$PPP.DEDICATED.MATCHES}`).
- S2: borrar los items deshabilitados acumulados por las migraciones
  (~30/host) y los 20 items net.if duplicados de 703 (criterio: sin datos
  frescos). Backup JSON de definiciones antes de borrar.
- S3: borrar las 5 reglas LLD sin uso real por host (mtxrHlTemperature,
  mtxrHlProcessorTemperature, mtxrLTEModem, mtxrWlAp, mtxrWlCMChannel).
  Conservar deshabilitadas como rollback: hrProcessorLoad.discovery,
  storage.discovery, net.vlan.walk, net.ppp.walk, system.cpu.walk, vfs.fs.walk.
- S4: no se borra historia de items que siguen vivos; los widgets/graficos
  que usen algo afectado se re-apuntan primero.

## Tasks

- T1 (S1): dedicados legacy baja: whitelist OK, widget 67621 -> graph 8180, LLD + prototipos + items + graphs borrados en 501-602 — ✅ (los Enlaces de 601 ya eran sesiones <pppoe-*> cubiertas por el whitelist)
- T2 (S2): 204 items propios deshabilitados borrados (backup edge-cleanup-backup-20261027.json) + 24 heredados vm.memory.* via template (graph 7000 + 3 items en 10841) + 20 churn net.if de 703 — ✅
- T3 (S3): 5 LLD wireless/LTE/temp borradas en el TEMPLATE 10841 (heredadas: cascada a los 8) — ✅; quedan por host 5 LLD: net.if/net.ppp/net.vlan activas + hrProcessorLoad/storage deshabilitadas (rollback)
- T4: CANCELADO — el "39 items" de 703 incluia prototipos; los habilitados reales eran 19 como el resto (diagnostico corregido)
- T5: verificacion final — ✅ 8 hosts uniformes (8-9 deshabilitados = walks rollback + uptimes viejos), 0 triggers rotos, 0 graphs huerfanos, mapper OK

## Log

- L1 (2026-10-27): diagnostico y aprobacion de Fase 1 (usuario: "Confirmo
  Fase 1. Al terminar y verificar todo OK, seguimos con la plantilla. Nombre
  de plantilla: Mikrotik CHR").
- L2: los enlaces dedicados legacy leen cada ~10 min via LLD SNMP host-level
  (verificado con ultima lectura); el dashboard los referencia (a mapear en T1).

- L3 (2026-10-27): F1 verificada. Correccion honesta del diagnostico: los 39
  items net.if de 703 eran 19 reales + 20 prototipos (error mio de conteo).
  Los triggers templados y graphs templados no se pueden borrar por host (API
  los rechaza): template 40441 y graph 7000 se borraron en el template.
  graph_discovery con parent_graphid colgado bloqueaba 4 graphs huerfanos.
