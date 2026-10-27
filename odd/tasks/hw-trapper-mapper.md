# CPU/disco/RAM via mapper+trapper (piloto 704)

Objetivo: eliminar los walks SNMP de CPU (`system.cpu.walk`) y storage
(`vfs.fs.walk`) de los CHR publicando CPU avg, disco % y RAM % por el mapper
(cron, trapper). Piloto en SW-EDGE-704; extrapolación a los demás CHR queda
como fase siguiente. Branch: `site-a-hw-mapper`. Test runner: `python3 -m pytest scripts/test_vlan_mapper.py`.

## Specs

- S1 (L1): "Vamos con 2. Extender el mapper y evitar la carga del walk pesado.
  Empezamos con piloto en SW-EDGE-704 y luego extrapolamos a los demas".
  Piloto = solo 704 publica hw; los demás hosts no cambian.
- S2: el mapper publica tres escalares float via zabbix_sender a items trapper
  de cada host: CPU promedio % (media de hrProcessorLoad), disco % usado
  (fila 131072 de hrStorage), RAM % usado (fila "Memory" de hrStorage).
- S3: guards estilo PPP: si el walk de una métrica falla o devuelve 0 filas,
  NO se publica esa métrica (no se pisa el último valor bueno con datos falsos).
- S4: deshabilitado por defecto global; se activa por host con `"hw": true`
  en su entrada de config. Ningún host cambia de comportamiento sin su flag.
- S5: en 704, tras el piloto funcionando: `system.cpu.walk` y `vfs.fs.walk`
  deshabilitados, items calculados viejos (134715 CPU, 134712 disco, 134606
  RAM) deshabilitados, widgets re-apuntados a los items trapper.
- S6: los items dependientes descubiertos por LLD (system.cpu.util,
  vfs.fs.*, vm.memory.*) quedan deshabilitados en 704; no se borra historial.

## Tasks

- T1 (S2-S4): mapper: colección hw + publish + config + tests (RED->GREEN, inline)
- T2 (S5): Zabbix 704: items trapper, deshabilitar walks/calc/dependientes, re-apuntar widgets (inline, remoto)
- T3 (S1): deploy a site-a (backup de config y mapper), corrida piloto 704, verificación de datos y dashboard (inline, remoto)
- T4: docs + checklist de extrapolación al resto de los CHR (inline)

## Log

- L1 (2026-10-27): "Vamos con 2. Extender el mapper y evitar la carga del walk
  pesado. Empezamos con piloto en SW-EDGE-704 y luego extrapolamos a los demas".
- Decisión: RAM NO queda con SNMP: sus items (`vm.memory.used/total`) son
  dependientes del walk de storage; se cubren con el mismo walk de hrStorage.
- Los walks de CPU (2 columnas) y storage (3 columnas) son tablas chicas
  (18 filas CPU; hrStorage ~decenas): costo marginal en la corrida del cron.
- Espejo Engram pendiente si mem_save sigue fallando por sesiones múltiples.
