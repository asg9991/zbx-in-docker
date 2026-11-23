# Observabilidad para clientes: análisis y plan de demo

Estado: **análisis previo a desarrollo**. Extiende el [ADR 0001](adr/0001-observabilidad-hibrida-loki-grafana.md)
(§D9, dos niveles de presentación). Este documento no describe código existente:
describe qué construir y en qué orden.

---

## 1. Qué se ve hoy (diagnóstico de las capturas)

### Dashboard cliente — "Estado del servicio"

| # | Defecto | Por qué importa |
| --- | --- | --- |
| C1 | **"Revisar" en rojo por un solo error de log** | El mapeo es 0 vs ≥1. Un error aislado pinta toda la pantalla en rojo y el cliente se acostumbra a ignorarlo. Es el mismo problema que la fatiga de alarmas |
| C2 | **"Con actividad" en azul** | No dice nada. Un cliente no sabe si "con actividad" es bueno o malo |
| C3 | **Tabla de problemas en inglés**: `Host`, `Severity`, `Status`, `PROBLEM`, `Ack`, `Tags`, `Time`; severidades `Average`/`Warning` | El título está en español y el contenido en inglés. Rompe la ilusión de producto terminado |
| C4 | **Tabla de 10 filas para 2 problemas** + paginación visible | Espacio muerto y controles innecesarios en una vista "simple" |
| C5 | **Gráfico de 7 días con barras cada 5 minutos** | El `interval: 1d` no se aplicó: muestra media hora, no una semana. Además el error aparece en verde y la leyenda dice `(severity="err")` |
| C6 | **Logs con timestamp duplicado y prefijo de IP** | `2026-11-19T19:33:56.000 | 2026-11-19T19:33:56-03:00 172.28.91.1 lab-sw-core ...`. El cliente ve dos veces la hora y una IP que no le dice nada |

### Dashboard técnico

| # | Defecto |
| --- | --- |
| T1 | Logs con `UNK` como nivel y timestamp duplicado (mismo origen que C6) |
| T2 | Sin filtros de host/grupo: para ver otro equipo hay que editar la consulta |
| T3 | Falta el panel que el cliente pidió explícitamente: **alarmas generadas** (historial de eventos, no solo los activos) |

### Transversal

- **"Make editable"** aparece con rol admin; con rol `Viewer` desaparece. Verificar en la demo.
- Los dos dashboards **no se enlazan entre sí** desde la navegación principal.

---

## 2. Problemas reales de los sitios que esto debe resolver

Base: relevamientos previos de los tres sitios (inventario, problemas abiertos,
eventos de 30 días, plantillas y sincronización de nombres de evento en español).

| # | Problema real | Evidencia | Qué debe responder la herramienta |
| --- | --- | --- | --- |
| R1 | **Fatiga de alarmas**: decenas de problemas abiertos y permanentes; triggers deshabilitados para callar ruido | Relevamiento: 37 problemas y 515 eventos en 30 días en un sitio; bajas masivas de triggers de un switch para silenciar | ¿Cuántos hay, cuáles son **nuevos hoy**, cuáles llevan días sin atender, cuáles son crónicos y deberían silenciarse con criterio? |
| R2 | **Alarmas sin contexto**: "Link down" sin decir qué interfaz ni qué cliente | Plantillas sin macros de interfaz/sesión en un sitio | Nombre del equipo, interfaz o sesión, y **el log del mismo minuto** al lado |
| R3 | **Monitoreo roto sin avisar**: cientos de items `not-supported` durante semanas | Caso Proxmox: 546 items sin datos desde hacía un mes | Panel de salud del monitoreo: items sin datos, hosts sin agente, última actualización |
| R4 | **Tareas de operación que fallan en silencio**: backup configurado que nunca corrió | Timers de backup habilitados sin ejecución; auditoría manual lo descubre | Indicador de "último backup correcto" por sitio |
| R5 | **Sin logs para post-mortem**: no hay receptor syslog; el procesador de eventos de firewall quedó fuera de una migración | Auditorías de los tres sitios | Búsqueda por equipo y por hora; correlación evento ↔ log |
| R6 | **Idioma mezclado**: nombres de evento en inglés en algunos sitios | Relevamiento de prototipos EN | El dashboard nunca muestra inglés; los nombres ya traducidos se usan tal cual |
| R7 | **Sin tendencia**: se reacciona cuando el disco está lleno | — | Disco, memoria, CPU y tráfico con proyección simple ("a este ritmo, 21 días") |
| R8 | **Accesos y cambios sin visibilidad**: logins de administración, reglas denegadas, cambios de configuración | Sin syslog no hay registro | Panel de seguridad: logins, denies, cambios |

**Conclusión de diseño:** el valor no está en "ver logs". Está en **convertir un
evento en una respuesta**: qué pasó, dónde, desde cuándo, y qué log lo explica.

---

## 2bis. Auditoría read-only de los tres sitios (2026-11-19)

Consulta exclusivamente de lectura sobre las bases de Zabbix (SELECT), sin
escrituras ni cambios de estado. Datos anonimizados: **Sitio A**, **B** y **C**.

| Métrica (30 días) | A | B | C |
| --- | --- | --- | --- |
| Hosts habilitados | 127 | 76 | 66 |
| Items habilitados | 29.178 | 25.044 | 21.137 |
| **Problemas abiertos** | 131 | **4.881** | 107 |
| — sin clasificar (sev 0) | 0 | **4.798** | 0 |
| — alta/desastre (sev ≥4) | 27 | 4 | 0 |
| — abiertos hace más de 7 días | 38 | 55 | 36 |
| — reconocidos (ack) | 4 | 0 | 0 |
| **Eventos** | 6.061 | 355 | **4.560** |
| — sin clasificar (sev 0) | 3.009 | 165 | 2.276 |
| **Items `not-supported`** | 124 | 112 | **1.201** |
| Triggers deshabilitados | 443 | 138 | 29 |

### Hallazgos

1. **Contar problemas no sirve.** En el Sitio B, 4.798 de 4.881 problemas son
   un artefacto: `Cannot evaluate function ... not enough data` de items de
   Proxmox, abiertos desde hace un año. Un semáforo que sume problemas pinta
   rojo permanente y el cliente deja de mirar.
2. **El ruido viene de pocos orígenes.** En el Sitio C, dos access points
   generan ~90 % de los 4.560 eventos (2.446 + 2.164). En el Sitio A, la OLT
   ZTE y Proxmox concentran ~80 % (2.844 + 1.974). Un "top 5 de orígenes"
   resuelve más que un listado completo.
3. **El monitoreo roto es el problema más grande y es invisible.** 1.201
   items `not-supported` en el Sitio C (5,7 % del total; los peores switches
   con 248, 240 y 232). Nadie lo detectó por dashboard: se descubrió auditando.
   → **"Salud del monitoreo" pasa de fase 2 a prioridad 1.**
4. **Hay problemas crónicos.** 38, 55 y 36 problemas llevan más de una semana
   abiertos; en el Sitio B uno desde hace un año. Sin una vista de "crónicos"
   el cliente se acostumbra al ruido.
5. **El reconocimiento (ack) no se usa.** 4 de 131, 0 de 4.881, 0 de 107. El
   dashboard no puede apoyarse en el ack para decir "esto está atendido".
6. **La severidad 0 domina los eventos** (3.009; 165; 2.276). Son triggers sin
   severidad asignada: invisibles para cualquier filtro por gravedad.
7. **Las clases de incidente reales** son: latencia ICMP (53 abiertos en A),
   memoria alta de VMs (Proxmox), link down de interfaces, tasa de errores de
   WiFi, y servicios de Windows detenidos (incluido un actualizador de Google).

### Consecuencias para el diseño

- El semáforo del cliente **no cuenta problemas totales**: excluye severidad 0
  y los problemas sin datos (`Cannot evaluate`).
- Prioridad 1: **Salud del monitoreo** (D13) y **Crónicos** (dentro de D11).
- El panel de problemas necesita **agrupar por clase y por origen**, no listar
  131 filas.
- Todo umbral absoluto (X errores por día) debe **calibrarse con estos datos**;
  hasta entonces es provisional.

---

## 3. Catálogo de dashboards prefabricados

Cada uno se entrega como JSON versionado en `docker/observability/grafana/dashboards/`.
"Nivel" según ADR D9: `Cliente` o `Tecnico`.

| Dashboard | Nivel | Responde | Fuente |
| --- | --- | --- | --- |
| **Estado del servicio** (existe, hay que pulir) | Cliente | ¿Está todo bien hoy? | Zabbix problemas + Loki contadores |
| **Alarmas y eventos** | Cliente/Técnico | Qué se disparó, cuándo, quién lo atendió, cuánto tardó en resolverse | Zabbix eventos |
| **Red y enlaces** | Cliente/Técnico | Disponibilidad, latencia, pérdida, sesiones PPPoE, interfaces con más caídas | Zabbix + logs de equipos |
| **Salud del monitoreo** | Técnico | ¿El monitoreo está mirando de verdad? | Zabbix items/hosts + Loki |
| **Capacidad** | Técnico | Disco, memoria, CPU, tráfico y proyección | Zabbix |
| **Seguridad y accesos** | Técnico | Logins, denies, cambios de config, VPN | Loki (syslog) |
| **Depuración de logs** | Técnico | Buscar por equipo/hora/texto y correlacionar con el evento | Loki + Explore |

---

## 4. Lista de tareas

Orden pensado para que cada fase deje algo mostrable. Cada tarea tiene criterio
de aceptación; nada se marca hecho sin observarlo funcionando.

### Fase 0 — Demo creíble (corregir lo que ya se ve)

| ID | Tarea | Aceptación |
| --- | --- | --- |
| D1 | Umbrales por severidad en los semáforos del cliente | 1 error aislado no pinta rojo; rojo solo con error crítico o volumen anómalo |
| D2 | Reemplazar "Con actividad" por un indicador con significado ("Equipos reportando" o "Sin novedades") | Un no técnico entiende el indicador sin preguntar |
| D3 | Localizar la tabla de problemas (columnas y severidades en español) | No queda ninguna palabra en inglés visible en la vista cliente |
| D3b | **Bloqueada: el panel del plugin no se puede traducir.** No tiene i18n (`grafana-zabbix` no publica archivos de locale) y sus columnas/severidades vienen en inglés. Dos caminos: (a) plugin **Infinity** + token de API de Zabbix para leer `problem.get` y armar una tabla nativa en español; (b) **exportador** que consulta la API y escribe a Loki. Recomendado (a): sin servicio nuevo ni copia de datos | Tabla de problemas en español, con gravedad "Aviso/Media/Alta/Desastre" |
| D4 | Ajustar layout: tabla con altura acorde, sin paginación visible | 2 problemas no dejan 8 filas vacías |
| D5 | Arreglar el gráfico de 7 días: buckets diarios, leyenda "Avisos"/"Errores", colores semánticos | Una barra por día; error en rojo, aviso en amarillo |
| D6 | Parsear el log: mensaje limpio, una sola hora, sin IP | Fila de log legible por un cliente |
| D7 | Enlazar los dos dashboards desde la navegación y dejar "Estado del servicio" como acceso principal | Dos clics desde el login a cualquier vista |
| D7b | **Estados vacíos**: "Sin datos" en gris, no "No data" en verde; antigüedad legible ("hace 4 h"); columnas en orden Equipo/Problema/Gravedad/Antigüedad | Ningún panel muestra "No data" ni timestamps ISO crudos |

### Fase 1 — Evidencia real (base para prefabricar)

| ID | Tarea | Aceptación |
| --- | --- | --- |
| D8 | **Auditoría read-only de los sitios actuales**: top 20 problemas por nombre, eventos de 30 días por severidad, hosts con más eventos, items `not-supported`, triggers deshabilitados, antigüedad de problemas abiertos | Informe por sitio, sin IPs ni nombres de cliente, con los datos que alimentan D9–D14 |
| D9 | Catálogo de clases de incidente y su log esperado | **hecho**: `clases.yaml` con 13 clases, LogQL validado contra Loki |
| D10 | Servicios críticos del sitio | **hecho con reglas por clase**: `reglas_por_clase` en `clases.yaml`, override por servicio, `gen_servicios.py` genera `servicios` (OK/Degradado/Crítico). Falta completar el YAML de cada cliente |

> D8 requiere autorización explícita de consulta remota ("andá con ssh para
> consulta"), según `ops/docs/ssh-readonly.md`.

### Fase 2 — Dashboards prefabricados

| ID | Tarea | Aceptación |
| --- | --- | --- |
| D11 | **Alarmas y eventos**: activos + historial con ack y tiempo de resolución | **parcial**: hay activos por gravedad y logs por severidad; falta el historial con ack/tiempo de resolución |
| D12 | **Red y enlaces**: disponibilidad, latencia/pérdida, PPPoE, interfaces más caídas | **parcial**: `Tráfico de Red` cubre tráfico; faltan disponibilidad, PPPoE e interfaces más caídas |
| D13 | **Salud del monitoreo** *(prioridad 1 por auditoría)*: items sin datos, hosts sin agente, última actualización | Un monitoreo roto se detecta el mismo día |
| D14 | **Capacidad**: disco/mem/CPU con proyección a 30 días | **parcial**: dashboard `Capacidades` con gauges; falta la proyección |
| D15 | **Seguridad y accesos**: logins, denies, cambios | **parcial**: la clase `seguridad` y sus consultas existen; falta el dashboard |
| D16 | **Depuración de logs**: filtros por equipo/hora + consultas guardadas + correlación evento↔log | **casi**: `eventos` + drill-down `equipo` + digest cubren el flujo; faltan consultas guardadas en Explore |

### Fase 3 — Producto demo

| ID | Tarea | Aceptación |
| --- | --- | --- |
| D17 | Usuarios de demo: `cliente` (Viewer) y `tecnico`, sin "Make editable" | El cliente no ve controles de edición |
| D18 | Datos sintéticos realistas: simulador que emite syslog variado y problemas por clase | La demo se ve con vida sin depender de un cliente |
| D19 | Guion de demo de 10 minutos (orden, qué se dice, qué se prueba en vivo) | Cualquiera del equipo puede repetirla |
| D20 | Arranque de demo en un comando + URL en pantalla | `make demo` levanta todo y muestra la URL |

### Fase 4 — Hacia un cliente real

| ID | Tarea | Aceptación |
| --- | --- | --- |
| D21 | Onboarding por sitio: habilitar syslog en equipos, firewall, perfil de recursos | Checklist ejecutado en un sitio |
| D22 | Respaldo y restauración de Loki y Grafana | Restauración probada, no solo escrita |
| D23 | Runbook de operación del stack | Qué hacer si cae Loki, Alloy, rsyslog o Grafana |
| D24 | Criterio de aceptación 9 del ADR: corte de 15 minutos con tráfico continuo | Cero pérdida verificada |

---

## 5. Dependencias

```
D1..D7  (independientes, se pueden hacer ya)
D8  ──▶ D9 ──▶ D11..D16
D10 ──┘
D11..D16 ──▶ D18 ──▶ D19 ──▶ D20
D21..D24 en paralelo, antes de instalar en un cliente
```

## 6. Lo que se necesita del lado humano

1. Autorización de consulta remota read-only para D8 (tres sitios).
2. Decisión de qué es "crítico" por cliente para D10.
3. Confirmación de si la demo se muestra con datos sintéticos o con un sitio real
   (cambia el orden de D18 y D21).

---

## 7. Estado de ejecución

Actualizado 2026-11-19.

| Fase 0 | Estado | Nota |
| --- | --- | --- |
| D1 umbrales por severidad | **hecho** | 0 errores / 1–4 "aislados" / ≥5 "revisar"; avisos: ≥20 dispara. Provisional hasta calibrar con datos de 30 días |
| D2 indicador con significado | **hecho** | "Equipos que están reportando" (hosts distintos en 24 h) reemplaza "Con actividad" |
| D3 tabla en español | **hecho** | Resuelto con D3b |
| D3b Infinity + token de API | **hecho** | Plugin Infinity 4.1.8 + token de solo lectura; tabla nativa en español (Equipo / Problema / Gravedad / Desde) con gravedad mapeada a Información, Aviso, Media, Alta, Desastre |
| D4 layout | **hecho** | Tabla de 7 filas de alto, 8 filas por página |
| D5 gráfico diario | **hecho (a verificar visualmente)** | `interval: 1d` a nivel de panel + `maxDataPoints: 7`; leyenda "Avisos"/"Errores" con colores semánticos |
| D6 log legible | **hecho** | Alloy emite `equipo | etiqueta mensaje`; la IP pasa a metadato estructurado |
| D7b estados vacíos | **hecho** | `noValue: Sin datos` con color neutro, antigüedad relativa, columnas ordenadas; exclusión de la capa de observabilidad reforzada por nombre de contenedor |
| D7 acceso principal | **hecho** | `Estado del servicio` es el home de la organización; enlaces cruzados entre ambas vistas |

Pendiente de verificación visual: D5 (buckets diarios) y D3b.

### Estado D13 (hecho)

Dashboard **Tecnico → Salud del monitoreo** (`/d/salud-monitoreo`), construido
con el datasource Infinity que dejó D3b y el datasource Zabbix:

| Panel | Fuente | Verificado |
| --- | --- | --- |
| Items sin datos | `item.get` con `filter: {state:1}` | 12 en el lab |
| Equipos sin respuesta | `hostinterface.get` con `available:2` + `selectHosts` | 1 en el lab |
| Cola de Zabbix | `item.get` de `zabbix[queue]` | 0 |
| Items sin datos: detalle | `item.get` con equipo, item y motivo | 12 filas, 3 columnas |
| Equipos sin respuesta: detalle | `hostinterface.get` con motivo del timeout | 1 fila con el error |
| Cola de Zabbix (24 h) | item interno `zabbix[queue]` vía datasource Zabbix | serie de 24 h |

En un site real, el panel "Items sin datos" muestra el 1.201 del Sitio C y los
124/112 de A y B: es el tablero que convierte un problema invisible en una
tarea con nombre y motivo.

---

## 8. Qué se sensa hoy en los sitios (relevamiento 2026-11-21)

Consulta read-only sobre las bases de los tres sitios. Datos anonimizados.

| | Sitio A | Sitio B | Sitio C |
| --- | --- | --- | --- |
| Items habilitados | 29.178 | 25.044 | 21.137 |
| **Interfaces de red** (`net.if`) | 8.180 | 5.088 | 4.379 |
| Discos (`vfs.fs`) | 693 | 534 | 453 |
| CPU (`system.cpu`) | 644 | 431 | 415 |
| Memoria (`vm.memory`) | 481 | — | 343 |
| Hardware de servidor | `dell.server` 697 | `dell.server` 697 + `system.hw` 509 | `system.hw` 457 + `hpe.msa` 278 |
| Virtualización | `proxmox.*` 300+ | `proxmox.*` 416 | — |
| Dashboards propios | 4 | 4 | 4 |

Los cuatro dashboards propios son, en los tres sitios, variantes de:
**Global view**, un **reporte ejecutivo o mapa**, y los dos del propio servidor
Zabbix. Es decir: el cliente ya tiene una vista "de negocio" y nadie la
mantiene sincronizada con lo que se mide.

### Lectura

1. **El 30–40 % de lo sensado son contadores de interfaz.** La red es el dato
   dominante; cualquier vista para cliente tiene que empezar por enlaces y
   disponibilidad, no por CPU del servidor.
2. **Hay mucho hardware de servidor y virtualización** (Dell, HPE, Proxmox):
   el segundo bloque natural es capacidad (disco, memoria, CPU).
3. **No hay sensing de logs** en ningún sitio: la capa nueva (Loki) agrega un
   tipo de dato que hoy no existe, no duplica nada.
4. **Cuatro dashboards por sitio es el techo razonable.** Agregar más no es
   progress: es ruido. La regla para lo prefabricado es **una sola vista de
   servicio** con 10–12 números, y el resto para técnicos.

### Compresión propuesta (12 números, no más)

| Bloque | Qué muestra | Fuente |
| --- | --- | --- |
| Estado | Problemas por gravedad, sin sev 0 ni "cannot evaluate" | Zabbix API |
| Enlaces | WAN/ISP arriba/abajo + latencia y pérdida | `net.if`, `icmpping*` |
| Equipos | Caídos por ICMP/agente | disponibilidad |
| Capacidad | Top 5 discos con menos espacio, proyección | `vfs.fs` |
| Cómputo | Top 5 CPU/memoria sobre umbral | `system.cpu`, `vm.memory` |
| Tráfico | Entrada/salida del enlace principal | `net.if` |
| Internet del ISP | Sesiones PPPoE activas y caídas | items de sesión |
| Eventos | Por clase: enlace, latencia, hardware, backup | Zabbix eventos |
| Respaldos | Último backup correcto por sitio | items de backup |
| Monitoreo | Items sin datos (solo técnico) | API + Loki |
| Logs | Solo errores de las últimas horas | Loki |
| Contexto | "Qué cambió" (reinicios, config) | logs de equipos |

Regla: si un bloque no cambia una decisión del cliente en 10 segundos, se
saca. La vista de servicio no pagina, no tiene variables y no tiene selector
de tiempo.

---

## 9. Integración con noc-agent: observabilidad + automatización

### La idea, en una frase

`zbx-in-docker` es **el lugar del dato**; el **noc-agent** es **el que lo
mastica y avisa**. El técnico deja de buscar: recibe "esto pasó, esto es lo
que importa, esto podés hacer", con el enlace a la evidencia.

### Reparto de responsabilidades (no negociable)

| Capa | Quién | Qué hace | Qué NO hace |
| --- | --- | --- | --- |
| Dato | Zabbix + Loki + Grafana | Recolectar, almacenar, mostrar, alertar | No decide ni interpreta |
| Contexto | Repo privado del cliente | Servicios críticos, qué significa cada alarma, ruido conocido, runbooks | No es código |
| Síntesis | noc-agent | Correlaciona alarma ↔ log, resume, pregunta | **No define umbrales ni alerta por su cuenta** |
| Acción | noc-agent (fase tardía) | Propone o ejecuta con aprobación y auditoría | No actúa sin confirmación |

Tres reglas que protegen lo construido:

1. **Un solo motor de alertas.** El agente consume alertas de Zabbix; no crea
   un segundo sistema de umbrales. Si el agente quiere avisar algo nuevo, se
   implementa como trigger de Zabbix.
2. **Una sola fuente de dato.** El agente lee la misma API y el mismo Loki que
   Grafana. Nada de scraping paralelo ni base propia.
3. **Trazabilidad obligatoria.** Cada mensaje del agente lleva el problema,
   el equipo y el enlace al dashboard/consulta que lo respalda. Sin eso no se
   puede confiar en él.

### El contrato que falta: el "context pack" por sitio

Un agente sin contexto inventa. El contexto es un archivo por cliente en su
repo privado:

```yaml
servicios:            # qué es crítico y cómo se llama para el cliente
  - nombre: Internet
    hosts: [<router-wan>]
    enlaces: [<ifIndex>]
  - nombre: Telefonía
    hosts: [<pbx>]
clases_de_alarma:     # qué significa cada familia y qué log la explica
  - clase: enlace
    patrones: ["Link down", "Enlace caído"]
    logs: '{host="$HOST"} |= "LINK" |~ "DOWN|UP"'
    accion: "verificar energía del equipo y siguiente salto"
ruido_conocido:       # lo que se puede silenciar con criterio
  - patron: "ICMP ping response time"
    motivo: "latencia de última milla, no actionable"
```

Ese archivo sirve para las tres cosas: el dashboard de servicio, el digest del
agente y las tareas de depuración de ruido que ya están en el diario.

### Flujo objetivo

```
Zabbix (problema) ─┐
                   ├─▶ noc-agent ──▶ digest ──▶ Discord/Telegram ──▶ técnico
Loki (logs) ───────┘        │
                            ├─▶ "¿qué pasó con X?" (consulta)
                            └─▶ propuesta de acción (con aprobación)
```

### Tareas nuevas (fase N), sin romper lo pendiente

| ID | Tarea | Aceptación | Depende de |
| --- | --- | --- | --- |
| N1 | **Context pack** por sitio (servicios, clases de alarma, ruido conocido) | **base hecha**: `clases.yaml` + `servicios.yml`, validados con `digest.py --check` | D10 |
| N2 | **Contrato del digest** | **hecho**: `docs/contrato-digest.md` + `digest.py --json` | N1 |
| N3 | **Biblioteca de correlación alarma ↔ log** | **hecho**: LogQL por clase, acotado a `host="$HOST"`, validado y usado por el digest | D9 |
| N4 | **Digest a Discord/Telegram** | **hecho**: `notify_digest.py` (dry-run sin destinatario, `--solo-alertas`); falta operarlo 7 días | N2, N3 |
| N5 | **Modo consulta** | **base hecha**: `preguntar.py` resuelve host o búsqueda textual con evidencia; falta medir 10 preguntas | N4 |
| N6 | **Banco de evaluación** | **hecho**: 31 casos de calibración + 10 de retención; retención 90 % (≥80 %). Huecos documentados | N4 |
| N7 | **Acciones sugeridas**: proponer ack/silencio/crear ticket, el humano aprueba | Ninguna acción se ejecuta sin aprobación | N6 |
| N8 | **Acciones con auditoría**: ejecutar con registro y rollback | Solo tras N6 aprobado y con auditoría probada | N7 |

Regla de secuencia: **nada de acciones antes del banco de evaluación**. Un
agente que se equivoca al resumir es molesto; uno que se equivoca al actuar es
un incidente.

### Lo que ya sirve para esto (no hay que rehacer nada)

- Zabbix API con usuario y token de solo lectura (D3b) → el agente usa el mismo camino.
- Loki con logs etiquetados por equipo y severidad → correlación directa.
- Catálogo de clases de incidente (D9) y auditoría de ruido (tareas del diario) → insumo de N1/N3.
- Dashboards con enlaces cruzados → la evidencia que el agente cita.

### Lo que hay que evitar

- Que el agente genere "su propio dashboard": ya hay uno.
- Que el agente decida qué es ruido sin el contexto del cliente.
- Que el agente escriba en Zabbix antes de tener evaluación.
- Duplicar el análisis en el prompt y en el dashboard: el dashboard muestra, el agente explica.

---

## 10. Demo: guion de 10 minutos

Script: `scripts/demo-up.sh` (levanta todo y siembra 6 días de logs).

### Orden de la demo

| Min | Qué se muestra | Qué se dice |
| --- | --- | --- |
| 0–1 | **Estado del servicio** | "Tres números: problemas graves, avisos y equipos caídos. Nada más" |
| 1–3 | Tabla **Qué está pasando ahora** | "Equipo, qué pasa, gravedad y hace cuánto. Sin entrar a Zabbix" |
| 3–5 | **Eventos de red de las 24 h** | "Errores, avisos e informativos, y su peso relativo" |
| 5–7 | **Últimos avisos** (logs) | "El mensaje del equipo, legible: qué interfaz, qué sesión" |
| 7–8 | Fila **Para técnicos** → vista técnica | "El técnico baja al detalle y a las consultas" |
| 8–10 | **Salud del monitoreo** | "Y acá vemos si el monitoreo miente: 1.201 items sin datos en un sitio real" |

### Puntos de venta

1. **No hay que abrir Zabbix para saber qué pasa.**
2. **Los logs explican la alarma**: el problema dice "link caído", el log dice qué interfaz.
3. **El monitoreo roto se ve**: items sin datos, no falsos verdes.
4. **Un dato, dos vistas**: el cliente ve el estado; el técnico, el detalle.

### Qué puede fallar

- Sin `.env` completo, Grafana no arranca (`GF_ADMIN_PASSWORD`).
- Si no se sembró historia, el gráfico de 24 h muestra poco: correr el script con siembra.
- La siembra de 6 días necesita **streams vacíos**: si Loki ya tiene líneas
  recientes, rechaza las viejas (`entry too far behind`, ventana de ~1 h). En un
  lab ya usado, recrear el volumen de Loki antes de sembrar.
- El puerto 1514 debe estar libre; el receptor escucha solo en `127.0.0.1`.

### Estado de la demo (2026-11-21)

| Tarea | Estado |
| --- | --- |
| D17 usuarios de demo | pendiente (hoy se usa `admin`) |
| D18 datos sintéticos | **hecho**: 12 equipos con métricas, 17 con syslog, 9 clases de evento, siembra de 6 días |
| D19 guion | **hecho** (esta sección) |
| D20 arranque en un comando | **hecho** (`scripts/demo-up.sh`) |

---

## 11. Notas del laboratorio (2026-11-21)

El lab pasó de 7 equipos a **12 con métricas y 17 con syslog**, con 9 clases de
evento y siembra de 6 días (≈9.400 líneas). Sirve para mostrar volumen y
gravedades distintas sin depender de un cliente.

Dos gotchas que costaron tiempo y conviene recordar:

1. **Desincronización de la tabla `ids` de Zabbix.** Crear equipos fallaba con
   `duplicate key ... items_pkey`: el contador `ids.items.nextid` estaba por
   debajo del `max(itemid)` real. Se corrige con
   `UPDATE ids SET nextid = (SELECT max(itemid)+1 FROM items) WHERE ...`.
2. **Zona horaria entre emisor y receptor.** El simulador (Alpine, UTC) emitía
   RFC3164 y rsyslog (Debian, `TZ=-03:00`) interpretaba esa hora como local:
   el mensaje quedaba **3 h en el futuro** y Loki lo rechazaba con
   `timestamp too new`. Se emite **RFC5424 con `Z` explícito**.

---

## 12. Navegación y drill-down (2026-11-21)

Regla: todo número que diga "revisar" tiene que llevar a donde se revisa.

| Panel | Al hacer clic | Adónde va |
| --- | --- | --- |
| Problemas graves | Ver solo problemas graves | `problemas` (tabla filtrada Alta/Desastre) |
| Avisos | Ver solo avisos | `problemas` (tabla filtrada Media/Aviso) |
| Equipos caídos | Ver equipos sin respuesta | `salud-monitoreo` foco en el detalle |
| Items sin datos (salud) | Ver detalle por equipo | detalle con host y motivo |
| Equipos sin respuesta (salud) | Ver detalle por equipo | detalle con host y motivo |

Los KPIs ahora muestran el **número** con color, no la palabra: "5" en rojo dice
más que "Revisar".

Dashboard nuevo **Cliente → Red y capacidad** (`/d/red-capacidad`): tráfico
entrada/salida por equipo y gauges de disco, CPU y memoria. Tiene un selector
de grupo de equipos (default `Lab/Simulados` en el lab; por sitio se fija al
grupo del cliente).

---

## 13. Correcciones post-revisión (2026-11-21)

| Reportado | Causa | Corrección |
| --- | --- | --- |
| Los tres KPIs en verde con 4, 3 y 1 | El último step de thresholds era verde: todo valor lo superaba | Steps con rojo desde 1 (graves/caídos) y naranja desde 1, rojo desde 6 (avisos) |
| Click en Problemas/Avisos → Page not found | El link apuntaba a `/zabbix.php`, que bajo el subpath `/grafana` resuelve mal | Links internos: `/d/estado-servicio?viewPanel=4` y `/d/salud-monitoreo?viewPanel=5` |
| Barra de eventos sin relleno visible | Gradiente continuo pisando el color fijo por serie | `color.mode: fixed` por serie (rojo/naranja/azul) |

Las lecciones técnicas quedaron en `docs/lecciones-observabilidad.md`
(síntoma → causa → solución, por componente).

### Ajuste de colores y filtros (2026-11-21)

- Semáforo: `semi-dark-green` en 0; `semi-dark-red` para graves; `semi-dark-yellow`
  para avisos; `semi-dark-orange` para equipos caídos. Tonos suaves, no rojo puro.
- Dashboard nuevo **Tecnico → Problemas**: dos tablas, una por gravedad
  (`priority` 4-5 y 2-3). Los KPIs abren la tabla correspondiente con
  `?viewPanel=1` / `?viewPanel=2`.
- Los links a Zabbix quedan **fuera de alcance** hasta definir
  `ZABBIX_PUBLIC_URL` por sitio (ver `lecciones-observabilidad.md`).

---

## 14. Evaluación del mapa de red (2026-11-21)

Lo que se ve hoy: Node Graph con estado real por equipo, pero **layout
automático**. En radial los nodos se superponen; en grilla queda una fila, no
una topología. Las etiquetas son chicas y el zoom no se recuerda.

| Opción | Estado | Layout | Mantenimiento |
| --- | --- | --- | --- |
| Node Graph (actual) | Automático por host | Radial/grilla, sin control | Cero |
| Canvas generado | **Implementado a mano en el lab** | Total | Generador chico (D-M1) |
| Canvas a mano | Funciona | Total | Alto: cada cambio de red se edita |
| Mapa de Zabbix | Funciona | Manual | Sacar al cliente de Grafana |

**Decisión:** Node Graph se queda como vista de estado y se agrega, como tarea
propia, el **generador de Canvas** desde `topology.yml` (niveles: internet →
firewall → core → acceso/servidores). Mientras no exista, el mapa lleva una nota
con la leyenda y el enlace a `Problemas`.

Tarea nueva:

| ID | Tarea | Aceptación |
| --- | --- | --- |
| D-M1 | Generador `topology.yml` → Canvas: un elemento por equipo, color por problemas, link al detalle | **hecho**: `scripts/gen_map.py`; 12 nodos, 12 consultas, 2 rojos verificados |
| D-M2 | Canvas de muestra (12 equipos, 11 conexiones, links) + tabla "Estado por equipo" | **hecho** y generado |

### Corrección del estado del mapa (2026-11-21)

El mapa y la tabla decían OK con problemas activos. Causa: se usaba
`trigger.get` y se contaba `value == "1"`, pero la API devuelve `value` de
forma inconsistente (0 en triggers que sí están en problema) y `only_true`
mezcla resultados.

Corrección: el estado sale de **`problem.get` con `hostids`**, que es la fuente
autoritativa y coincide con la pestaña de Problemas. Verificado: 3 nodos rojos
y 3 filas en la tabla para los mismos equipos.

### Mapa: iconos y geometría (2026-11-21)

El mapa usa **iconos por clase de equipo** (unicons de Grafana) con el color
atado al estado, etiqueta debajo, y conexiones con color y grosor
parametrizables. La posición sale de `level` (columna) + `layout`, no de
coordenadas a mano.

| Parámetro (`layout`) | Default | Qué controla |
| --- | --- | --- |
| `node_w` / `node_h` | 120 / 44 | tamaño de la caja de texto (modo sin icono) |
| `icon_size` | 40 | lado del icono |
| `x_gap` / `y_gap` | 170 / 34 | separación entre columnas y dentro de la columna |
| `origin_x` / `origin_y` | 20 / 60 | origen del dibujo |
| `line_color` / `line_size` | `#8fa6c1` / 1.5 | estilo de las conexiones |

Limitación: Canvas solo dibuja conexiones **rectas**; no hay ruteo ortogonal.

### Mapas múltiples (2026-11-22)

Un archivo por mapa en `docker/observability/maps/`; el generador crea un
dashboard por archivo con `uid = mapa-<slug>` y los enlaza entre sí. El insumo
es un prompt con el orden por niveles (ver `docs/mapas-red.md`), y los `hostid`
se resuelven contra la API con `--resolve`.

Demo en el lab: `mapa-lab` (12 nodos) y `mapa-lab-core` (5 nodos).

### Renombres y set por cliente (2026-11-23)

- `Estado del servicio` → **Estado de la Red**.
- `Red y capacidad` → **Tráfico de Red** (solo tráfico).
- Nuevo **Capacidades**: gauges de disco, CPU y memoria.
- Cada cliente usa el set de dashboards que su repo incluya (ver README de
  observabilidad).
