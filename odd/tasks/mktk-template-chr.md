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
- T4: limpieza post + docs + reporte (inline) — ✅ (ver docs; incidente del
  filtro resuelto; pendiente Fase 2b: consolidar 10885 y retirar las 3 viejas)

## Log

- L1 (2026-10-27): usuario confirma: "Arrancamos con la plantilla. Nombre
  de plantilla: Mikrotik CHR" y luego "Dale nomas".
- Estrategia S4 elegida porque unlink+clear BORRA los items descubiertos
  (y sus itemids, rompiendo graphs del dashboard); unlink sin clear los
  vuelve host-level conservando ids; la LLD nueva adopta items existentes
  por key.

- L2 (2026-10-28): migracion aplicada x8 con herencia; itemids preservados; filtro unificado en template; incidente de discovery sin filtro resuelto con lifetime=0 temporal.
