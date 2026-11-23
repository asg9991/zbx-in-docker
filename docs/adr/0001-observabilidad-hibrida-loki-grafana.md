# ADR 0001 — Capa de observabilidad híbrida: Loki y Grafana junto a Zabbix

- **Estado:** Aceptado (implementado en el laboratorio; promoción a un cliente pendiente)
- **Fecha:** 2026-11-19
- **Ámbito:** stack genérico (`zbx-in-docker`) y despliegues por cliente
- **Implementación:** laboratorio primero; replicación en producción de un cliente después

---

## 1. Contexto

El stack actual es Zabbix-only: server 7.4 LTS, web, PostgreSQL 15, nginx y
Agent2. Cubre bien lo que Zabbix hace mejor:

- SNMP e ICMP sobre equipos de red, con LLD y templates propios (Mikrotik,
  Cisco IOS, Zyxel, ZTE, OLT Zhone, UniFi, Eaton, DNS).
- External checks para lo que SNMP no expone (API UniFi, sesiones PPPoE).
- Proxmox por HTTP template.
- Alertas por Telegram, reportes PDF vía Web Service, dashboards nativos.

Quedan tres huecos que no son de implementación sino de tipo de dato y de
capa:

1. **Logs.** Zabbix no agrega logs. Ante una caída de sesión PPPoE, un AP que
   flapea o un reinicio de servicio, el evento de red no se puede correlacionar
   en tiempo con el log del equipo.
2. **Exploración y análisis de tendencia.** Los gráficos nativos de Zabbix son
   pobres para capacidad, comparación entre sitios y consultas ad-hoc.
3. **Presentación multi-fuente.** No hay una capa única de visualización sobre
   datos que hoy viven en Zabbix y datos que hoy no existen (logs).

Se evaluó el repositorio público `datenmaniak/grafana-hybrid-monitor`
(Prometheus + Loki + Grafana + Zabbix) como referencia. Su **intención**
arquitectónica es correcta: separar por tipo de dato (métricas scrapeadas,
logs, SNMP/LLD) y provisionar datasources y dashboards como código. Su
**implementación** no es adoptable y este ADR registra explícitamente por qué
(ver §6). En particular:

- Grafana no tiene datasource de Zabbix; el README afirma una integración que
  el código no tiene.
- Loki corre sin ningún cliente de envío: no recibe logs.
- No hay `rule_files` ni Alertmanager; las alertas descritas no existen como
  código.
- Versiona `grafana.db`, el WAL de Prometheus y un `.env` con contraseña.
- Publica Prometheus, Loki y Grafana sin autenticación ni proxy.
- Descarga dashboards de `grafana.com` sin pin de revisión ni verificación.

### Restricciones vigentes

- Un despliegue por sitio, con repositorio privado por cliente. Lo específico
  del sitio (IPs, VLAN, hosts, credenciales) **no** puede vivir en este repo.
- El stack se expone detrás de nginx con TLS por sitio; no se agregan puertos
  públicos nuevos.
- Un solo motor de alertas por sitio. Dos motores solapados sobre la misma
  métrica se consideran un defecto, no una feature.
- Los datos persistentes van bajo `DATA_DIR`; los secretos quedan fuera del
  repo según `docs/seguridad-secretos.md`.
- Todo cambio debe poder revertirse sin tocar Zabbix.

### Qué es un sitio

Un **sitio** es una instalación de un cliente: un servidor, un stack y su
propio repositorio privado (Todd, Cespal, Cavox, …). Hay **un despliegue por
sitio** y la etiqueta `site` de Loki identifica a ese despliegue, no a una
zona dentro de un cliente. La agregación de varios clientes en un colector
compartido **no está decidida** y queda fuera de esta etapa (§3).

---

## 2. Decisión

Se adopta una **capa de observabilidad híbrida de dos piezas**: Loki para logs
y Grafana para presentación, montadas junto al stack actual. Zabbix sigue
siendo el sistema de registro de métricas y el único cerebro de alertas de
infraestructura.

### D1 — Loki y Grafana, sin Prometheus (fase 1)

Se incorporan Loki y Grafana al compose. **No se incorpora Prometheus** en
esta fase. Re-monitorear por scraping lo que Zabbix ya consulta por SNMP/LLD
duplicaría trabajo, almacenamiento, retención, backups y superficie de
upgrade, sin agregar una métrica nueva.

### D2 — Zabbix sigue siendo el sistema de registro y de alertas

- Métricas de infraestructura: Zabbix, sin cambios de recolección.
- Alertas de umbral, disponibilidad, SNMP y negocio: Zabbix.
- Grafana es **capa de lectura**, no de recolección ni de alerta.
- El datasource de Zabbix en Grafana apunta a la API existente, en modo
  lectura, con un usuario/token dedicado y de permisos mínimos.

### D3 — Transporte de logs: syslog como columna, Alloy como colector

Promtail está en fin de vida en Loki 3.x; el agente soportado es Grafana
Alloy. rsyslog recibe el syslog de la red, lo escribe a archivo y Alloy lo
envía a Loki junto con los logs de contenedor.

Relevamiento de tres sitios de producción (269 hosts monitoreados): ~35 % se
monitorea por SNMP (routers, switches, APs, OLTs, firewalls), ~39 % por agente
(Linux y Windows) y el resto por ICMP/HTTP. Es decir: **la mayoría de las
fuentes de log son equipos de red, no servidores**. Todos los fabricantes
presentes (Fortinet, MikroTik/RouterOS, Zyxel, Huawei VRP, Cisco IOS, OLT ZTE
y Zhone, Ubiquiti airOS) soportan syslog remoto, y ninguno de los tres sitios
tenía receptor syslog configurado.

#### Cadena de transporte

La recepción es **rsyslog por defecto**, por resiliencia y porque ya está
instalado y corriendo en todos los sitios. El archivo que escribe es el buffer
de disco que absorbe caídas de Alloy o de Loki.

```
equipo de red ──syslog──▶ rsyslog ──archivo──▶ Alloy ──▶ Loki ──▶ Grafana
```

- **Recepción: rsyslog** en la IP de gestión. Aporta recepción UDP/TCP, cola en
  disco y un archivo que sobrevive a reinicios de Alloy y a caídas de Loki.
- **Envío: Alloy** hace tail del archivo y empuja a Loki con etiquetas y
  parseo.
- **Alertas: no cambian.** Siguen en Zabbix sobre métricas. Esta capa no
  envía eventos ni alertas a Zabbix; Alloy solo transporta logs.
- **Un solo receptor por puerto y protocolo.** Nunca rsyslog y Alloy
  escuchando el mismo puerto.
- **Excepción:** Alloy puede recibir syslog directo (`loki.source.syslog`) solo
  en fuentes de bajo valor o donde no haya rsyslog, aceptando que sin archivo
  no hay buffer.

#### Qué garantiza y qué no el buffer de archivo

La durabilidad no es automática: depende del backpressure y de la retención de
rotación. Comportamiento verificado en la documentación de Alloy:

| Situación | Resultado |
| --- | --- |
| Alloy detenido o reiniciando | rsyslog sigue escribiendo; Alloy retoma desde la posición guardada. Sin pérdida |
| Loki caído con Alloy arriba | `loki.write` reintenta con backoff; la cola se llena y `block_on_overflow=true` (default) **bloquea la lectura**: la posición no avanza y el archivo acumula el atraso |
| Caída más larga que la ventana de desorden de Loki (~1 h) | **Se pierden las líneas más viejas al reanudar**, aunque el archivo las tenga: Loki responde 400 `entry too far behind` y Alloy descarta el lote |
| Caída más larga que la retención del buffer | **Se pierden líneas**: el borrado por edad elimina datos que nunca se enviaron |
| Crash sucio de Alloy | Sin WAL se pierden las entradas ya aceptadas en la cola en memoria (la posición avanzó). Con `wal { enabled = true }` la entrada es durable al llegar al componente |
| UDP con ráfaga | Puede perder en el socket del kernel; mitiga con `rmem` y TCP donde el equipo lo soporte |

Condiciones obligatorias para que el buffer sea real:

- **Archivos diarios sin rename ni truncado** y borrado por edad
  (`find -mtime +N`), nunca `logrotate` con `copytruncate`: rotar por nombre
  mientras Alloy lee pierde líneas. La retención del archivo (7 días por
  defecto) cubre la **inspección forense**, no el drenaje: para ingesta la
  ventana útil es la de Loki.
- **La ventana de drenaje es `ingester.max_chunk_age / 2`** (1 h con el
  default de 2 h). Es la única condición que decide cuánto atraso acepta Loki
  al recuperarse; `reject_old_samples_max_age` es un límite absoluto distinto.
  Sobrevivir caídas más largas exige subir `max_chunk_age` (más memoria y
  chunks más grandes) o una cola que preserve el orden, no más retención.
- `block_on_overflow = true` en `loki.write` (default) y apagado ordenado de
  Alloy.
- **Alerta de atraso de ingesta**: si el archivo más viejo sin enviar supera N
  minutos, o si la rotación va a borrar datos no enviados. Sin esta alerta, el
  buffer crece en silencio hasta perderse.
- Cola de `loki.write` explícita (`block_on_overflow`, `drain_timeout`) y
  **WAL habilitado**: cierra la ventana de pérdida ante crash sucio de Alloy.
  El WAL de Alloy v1.22.0 exige `--stability.level=experimental`; se fija la
  versión y se documenta cómo desactivarlo (se vuelve solo al buffer de
  archivo).

La recepción (colector) y el reenvío (servidor monitoreado) son decisiones
distintas: en Linux monitoreado se reenvía con el rsyslog que ya está
instalado, para no sumar un agente.

#### Fuentes y transporte

| Fuente | Transporte | Etapa |
| --- | --- | --- |
| `zabbix-server`, `zabbix-web`, `nginx` | logs de contenedor vía Alloy | lab y sitio |
| Proxmox (nodo y VMs) | rsyslog del host → Alloy | lab y sitio |
| Linux monitoreado | rsyslog forwarding al colector | sitio |
| Equipos de red (Fortinet, RouterOS, Zyxel, VRP, IOS, OLT, airOS) | syslog al colector | sitio |
| VMware (ESXi) | syslog al colector | sitio |
| Windows | fuera de fase 1 (requiere agente de eventos) | — |

#### Reglas de ingesta

- **Volumen por sitio.** El tope de ingesta y la retención se fijan en el
  `.env` del sitio. Si una familia de equipos genera más volumen del que entra
  en el presupuesto de disco, **qué se envía se decide en el repo de ese
  cliente**; este repo genérico no define filtros por fabricante ni depende de
  ningún procesador externo de eventos.
- **Etiquetas de índice**: `site`, `job`, `host`, `facility`, `severity`.
  Nunca `logid`, `msg`, `syslog_tag` (puede llevar el PID del proceso en
  Linux: `sshd[1234]:`) ni valores de alta cardinalidad como labels. Lo que se
  parsea —incluido lo propio de un fabricante o del sitio, como `vendor` o
  `device_role`— se consulta como campo de la línea, no como índice.
- **Retención y tope de ingesta** se fijan por sitio en su `.env`; sin tope, un
  equipo ruidoso consume el disco del sitio.
- **Habilitar syslog en los equipos** es un cambio por sitio, con respaldo y
  ventana, y se registra en el repo privado del cliente.

#### Alternativas descartadas para el transporte

| Alternativa | Motivo |
| --- | --- |
| Agente por host (Alloy/Filebeat en cada equipo) | Instalar y actualizar un agente en decenas de equipos de red que no lo permiten; inviable fuera de servidores |
| Polling de API del fabricante (firewall, router, controladora WiFi) | Las APIs no exponen el log completo; la latencia y el costo de consulta son peores que syslog |
| SNMP traps como único camino | Solo llegan los eventos que el equipo decide emitir y sin el detalle del mensaje; complementa, no reemplaza |
| Lectura de logs por SSH | No es tiempo real, no escala y depende de credenciales interactivas |
| Driver de logging de Docker hacia Loki | Acopla el runtime al destino y no cubre equipos de red |

SNMP traps se mantienen donde ya funcionan y donde el evento es binario
(link up/down, alarma); syslog aporta el contenido y la correlación.

### D4 — Provisioning como código, con pin

- `grafana/provisioning/datasources/` y `grafana/provisioning/dashboards/`
  montados `:ro` desde el repo.
- Dashboards: solo curados, con ID **y revisión** de origen registrados en un
  manifiesto versionado, y el JSON revisado como cualquier otro artefacto.
  Nada de `latest` a ciegas.
- Imágenes con **tag de parche exacto** (sin `latest` ni `-latest`), registrado
  en este ADR al implementar.
- El plugin de Zabbix para Grafana se instala con versión fijada; si el método
  de instalación en runtime no permite fijarla, se hornea en una imagen propia.
- Nunca se versiona estado binario: ni `grafana.db`, ni WAL, ni bases.

### D5 — Exposición y credenciales

- Grafana y Loki **no publican puertos**. Se alcanzan solo por la red interna
  y, si hace falta acceso externo, a través del nginx existente con el TLS del
  sitio.
- **Única excepción: el receptor syslog.** Se publica en la IP de gestión del
  host, en puerto alto (`1514/tcp` y `1514/udp` por defecto), con regla de
  firewall limitada a las redes de los equipos que lo envían. Nunca en la
  interfaz WAN ni en la IP pública. `514` solo se habilita si una familia de
  equipos no permite configurar otro puerto, y se documenta por qué.
- Credenciales por variables de entorno / archivo de secretos fuera del repo.
  Sin valores por defecto utilizables en producción.

### D6 — Persistencia y retención explícitas

- Datos de Loki bajo `${DATA_DIR}/loki`; datos de Grafana bajo
  `${DATA_DIR}/grafana`.
- Retención de logs definida por sitio y escrita en el `.env` del sitio, no
  implícita.
- El respaldo de Loki y Grafana se suma al runbook de respaldo existente; el
  respaldo de Zabbix no cambia.

### D7 — Orden de despliegue: laboratorio, luego un cliente

Este ADR se implementa **primero en el laboratorio de este repo** y se replica
en producción de **un** cliente, no en todos. La promoción requiere cumplir
los criterios de §4. Cualquier diferencia del sitio (fuentes de log, volumen,
exposición) se registra en el repo privado del cliente, no acá.

### D8 — Perfil por sitio y presupuesto de recursos

El trío completo (Loki + Grafana + Alloy) no entra en cualquier servidor. El
relevamiento mostró sitios con 2 vCPU / 2,5 GB de RAM y otros con 8 vCPU /
64 GB, y discos con 33 GB libres frente a 205 GB. Por eso se define un
**perfil mínimo** antes de desplegar:

| Perfil | Requisito | Qué se despliega |
| --- | --- | --- |
| Completo | ≥ 4 GB RAM libres y ≥ 20 GB de disco libre por encima del uso actual | Loki + Grafana + Alloy en el sitio |
| Reducido | Menos que lo anterior | Solo rsyslog + Alloy, con envío a un colector central **si el cliente lo autoriza**; sin Grafana local |
| Sin logs | Disco o RAM por debajo del mínimo operativo | Se mantiene Zabbix-only y se documenta la limitación |

Reglas:

- El perfil se decide con medición en el sitio, no por modelo de servidor.
- La retención y el tope de ingesta de Loki se fijan por sitio; el valor por
  defecto no puede consumir el disco del huésped.
- Si el perfil es reducido, el envío a un colector central se acuerda con el
  cliente. Hoy no hay hub desplegado ni una vista multi-sitio: ambos requieren
  decisión propia.
- Ampliar RAM o disco para habilitar el perfil completo es una decisión del
  cliente, no un supuesto.

### D9 — Dos niveles de presentación: cliente y técnico

El cliente no consume dashboards técnicos. Se definen dos niveles explícitos:

| Nivel | Quién | Qué ve | Dónde |
| --- | --- | --- | --- |
| Servicio | Cliente, gerencia | Estado, problemas activos en lenguaje llano, tendencia de avisos, últimos eventos importantes | Dashboard `Estado del servicio`, sin selector de tiempo ni variables |
| Técnico | Técnicos propios | Logs completos, consultas ad-hoc, métricas de Zabbix por host | Dashboard técnico + Explore |

Reglas:

- **El nivel de servicio no expone conceptos técnicos**: ni nombres de
  componentes, ni consultas, ni selectores de etiquetas. Ventanas fijas
  (24 h y 7 días), no un rango libre.
- **Las consultas avanzadas no se esconden, se separan**: Explore sigue
  disponible para el técnico, con un catálogo de consultas en el dashboard
  técnico.
- **El nivel de servicio no alerta**: Zabbix sigue siendo el único motor
  (D2). Un panel que se pone rojo no reemplaza una acción de Zabbix.
- **Acceso y usuarios (estado actual)**: no hay separación de privilegios por
  audiencia. Cliente, ejecutivo y técnico entran con acceso a ambas carpetas;
  qué usuarios y roles se crean por sitio **todavía no está definido**. Lo que
  se garantiza es que la vista de servicio sea **la puerta de entrada** y esté
  a un clic. Restringir `Tecnico` por permisos de carpeta es una opción futura
  por sitio, no un requisito ni algo que hoy haga el provisioning.
- **Datos**: ambos niveles leen lo mismo; no hay una segunda recolección ni
  un segundo almacenamiento para "simplificar".

---

## 3. Fuera de alcance

- Prometheus, `node_exporter`, `cAdvisor`, `kube-state-metrics`, `pve-exporter`
  y cualquier otro exporter.
- Alertmanager y Grafana Alerting (ver §5 para la excepción admitida).
- Reemplazar dashboards nativos de Zabbix.
- Trazas / OpenTelemetry.
- Agregación central de varios clientes en un hub compartido (requiere decisión
  propia y un selector `site` en los dashboards).
- Analítica de flujos (NetFlow/IPFIX/sFlow). Evaluada en §11; no se implementa
  en esta etapa.
- Logs de Windows (requieren agente de eventos; se evalúan en un ADR aparte).
- Traer logs de equipos que no emiten syslog ni admiten agente; se documenta
  como limitación del sitio.
- Cambiar versiones, topología o ajustes de Zabbix.

---

## 4. Criterios de aceptación

### Laboratorio (bloqueante para promover)

1. `docker compose config` válido y `up -d` sin errores en el stack completo.
2. Consulta a Loki devuelve al menos un log de `zabbix-server`, uno de nginx y
   uno de Proxmox, con etiquetas correctas.
3. El datasource de Zabbix en Grafana devuelve series históricas de un host
   conocido, con el mismo valor que muestra Zabbix para la misma ventana.
4. Un dashboard provisionado renderiza métricas de Zabbix y logs de Loki en la
   misma vista, y sobrevive a `down`/`up` sin intervención manual.
5. No hay puertos nuevos publicados fuera de los ya existentes, salvo el
   receptor syslog en la IP de gestión, limitado por firewall a las redes de
   origen. Grafana y Loki solo son alcanzables desde la red interna (o por
   nginx), y el receptor no responde desde la WAN.
6. Las alertas de Zabbix siguen funcionando sin cambios y no se duplican.
7. Reinicio del host: el stack vuelve completo y Grafana conserva dashboards y
   datasources.
8. Se ejecuta y documenta un ciclo de respaldo y restauración de Loki y
   Grafana.
9. **Resiliencia del buffer**: con Loki detenido 15 minutos y tráfico syslog
   sintético continuo, al reiniciar Loki no falta ninguna línea y Alloy sigue
   la posición sin duplicar. Con el borrado por edad adelantado durante el
   corte, la alerta de atraso de ingesta dispara antes de perder datos.

### Producción (un cliente)

10. Se cumplen 1–9 en el sitio, con el `.env` del cliente.
11. El consumo de disco y memoria medido a 7 días entra en el presupuesto del
    servidor del cliente.
12. El runbook del sitio queda actualizado y el rollback (§7) fue probado.

---

## 5. Consecuencias

### Positivas

- Correlación log↔métrica para triage de incidentes, sin duplicar recolección.
- Retención de logs fuera de la base de Zabbix.
- Dashboards densos y consultas ad-hoc sobre datos que ya existen.
- La capa es repetible por sitio: sumar un cliente es reinstalar, no rediseñar.
  Una vista multi-sitio no está en alcance.
- Rollback barato: la capa nueva no participa de la recolección ni de las
  alertas.

### Negativas

- Dos servicios más por sitio: más superficie de upgrade, parcheo y monitoreo.
- Un almacén nuevo que respaldar y dimensionar (logs crecen distinto que las
  métricas).
- Una UI más que mantener y explicar; el riesgo real es que Grafana derive en
  un segundo lugar donde se configuran cosas a mano.
- El plugin de Zabbix para Grafana agrega una dependencia de terceros sobre la
  API de Zabbix.

### Neutras / a vigilar

- Grafana consume la API de Zabbix. Si el volumen de consultas afecta al
  server, se limita por caché y por cantidad de paneles, no se escala Zabbix.
- Los dashboards de la comunidad envejecen; el manifiesto con revisión fijada
  es lo que evita el drift.

### Excepción admitida de alerta

Si en el futuro aparece una alerta que **solo** se puede expresar sobre logs
(por ejemplo, un patrón que Zabbix no puede ver), puede implementarse en
Grafana Alerting con estas condiciones: dueño explícito, documentada como
segundo motor, sin solapamiento con ninguna alerta de Zabbix, y registrada en
un ADR posterior. Fuera de eso, Grafana no alerta.

---

## 6. Qué no se toma del repositorio de referencia

Se registra para que no se reintroduzca por copia:

| Práctica observada | Por qué se rechaza |
| --- | --- |
| Prometheus scrapeando lo mismo que Zabbix ya monitorea | Duplica TSDB, backups y alertas sin métricas nuevas |
| `grafana.db`, WAL y `.env` versionados | Estado binario y secretos en git |
| Puertos 3000/9090/3100 sin auth | Inaceptable en un servidor de cliente |
| Tags rodantes (`7.2-latest`) | Upgrades no reproducibles |
| Dashboards `latest` sin revisión | Cambios silenciosos, JSON no revisable |
| Alertas descritas en README pero inexistentes en código | Documentación que miente; acá los criterios son verificables |
| Bind mount de datos sin ruta ni permisos definidos | Pérdida de datos silenciosa |

Sí se toma: la separación por tipo de dato, el provisioning como código y el
uso de volúmenes nombrados para datos con bind mounts para configuración.

---

## 7. Rollback

La capa nueva es aditiva y no intercepta tráfico de Zabbix:

1. `docker compose stop` de los servicios `loki`, `grafana` y `alloy`.
2. Dejar los volúmenes/datos intactos durante la ventana de retención.
3. Revertir el `.env` del sitio a la versión previa (los servicios de Zabbix
   no leen variables nuevas).
4. Verificar que Zabbix, web, nginx y las alertas siguen operativos.

No se requiere restaurar la base de Zabbix en ningún escenario de rollback de
esta capa.

---

## 8. Disparadores de revisión

Este ADR se revisa si ocurre alguno de estos:

- El volumen de logs excede el presupuesto de disco del sitio de forma
  sostenida, aun con el filtro previo.
- El plugin de Zabbix degrada la performance del server o de la UI.
- Un sitio queda por debajo del perfil mínimo y no puede sostener el trío.
- Aparece una familia de equipos sin syslog ni agente, o una necesidad real de
  logs de Windows.
- El buffer de archivo deja de alcanzar (volumen o duración de caída) y hay
  que evaluar una cola persistente del lado del emisor.
- Aparece una necesidad real de métricas que Zabbix no puede obtener; en ese
  caso se evalúa un exporter puntual con criterio explícito (sin template
  Zabbix mantenido, métrica pull-friendly, consumidor identificado) y su
  propio ADR.
- Se suma un segundo cliente con la capa desplegada: la vista multi-sitio pasa
  a ser una decisión aparte.

---

## 9. Alternativas consideradas

| Alternativa | Evaluación |
| --- | --- |
| **Seguir Zabbix-only** | Descarta el hueco de logs y de análisis; es la opción de costo cero que se descarta por el objetivo de observabilidad |
| **Híbrido completo con Prometheus** (repo de referencia) | Duplica recolección y alertas en un entorno de red donde Zabbix ya es superior; alto costo por sitio |
| **Solo Loki + CLI/consultas** | Resuelve logs pero no la correlación visual ni la presentación; Grafana es el costo marginal |
| **SaaS (Grafana Cloud u otro)** | Datos de clientes fuera del sitio, costo recurrente y dependencia externa; contrario a la política de despliegue por cliente |
| **Loki + Grafana sin datasource Zabbix** | Deja la vista partida en dos UIs; no cumple el objetivo de capa única |

---

## 10. Notas de implementación

Versiones fijadas para el despliegue de laboratorio (2026-11-19):

| Componente | Versión | Nota |
| --- | --- | --- |
| `grafana/loki` | `3.7.10` | distroless: sin shell ni healthcheck propio |
| `grafana/grafana` | `13.3.1` | |
| `grafana/alloy` | `v1.22.0` | imagen sin `wget`/`curl` |
| `rsyslog/rsyslog` | `2026-10` | corre como uid 101 (`syslog`) |
| `alpine` (retención) | `3.22` | solo `find` por edad |
| plugin `alexanderzobnin-zabbix-app` | `6.10.3` | horneado; `GF_INSTALL_PLUGINS` no fija versión |
| plugin `yesoreyeram-infinity-datasource` | `4.1.8` | horneado; consultas JSON a la API de Zabbix |
| `alpine` (cliente de prueba) | `3.22` | verificación manual de Loki/Alloy |

- El plugin de Zabbix se instala con versión fijada, horneado en imagen si el
  runtime no permite fijarla. Se instala en `/opt/grafana-plugins` y no en
  `/var/lib/grafana`, que se monta desde `DATA_DIR` y taparía el plugin.
- El usuario/token de Zabbix para Grafana es de solo lectura y su rotación
  entra en el runbook de operación del sitio.
- `site` es la etiqueta obligatoria en todos los streams de Loki; sin ella no
  se acepta un job en el manifiesto.
- Los dashboards curados se guardan con su ID y revisión de origen en el
  manifiesto, junto al commit que los incorporó. Un dashboard propio se
  registra como local, con la revisión del commit.
- La regla de firewall del receptor syslog se documenta en el runbook del
  sitio, con las redes de origen permitidas y el puerto elegido.
- El receptor rsyslog usa `imudp`/`imtcp` sobre la IP de gestión y escribe un
  archivo diario por sitio (`AAAA-MM-DD.log`); la identificación del origen va
  en el contenido de cada línea, no en el nombre del archivo, para no
  multiplicar archivos con cientos de equipos.
- Antes de promover a un cliente se mide RAM y disco libres y se registra el
  perfil (§D8) en el repo privado del sitio.

Hallazgos verificados al construir el laboratorio:

- **Docker no publica puertos de un contenedor conectado solo a redes
  `internal`.** El receptor syslog va en la red no interna (`frontend`); es el
  único servicio que debe escuchar desde afuera.
- **`loki.source.file` con un glob sin coincidencias al arrancar descarta la
  fuente y no reintenta.** Hay que usar `local.file_match`, que re-evalúa el
  glob; si no, un despliegue nuevo queda ciego hasta reiniciar Alloy.
- **Loki rechaza timestamps futuros** (`timestamp too new`). Un equipo con
  reloj adelantado pierde sus logs: NTP en los equipos de origen es
  requisito, no buena práctica.
- **La ventana de desorden de Loki 3.x es `max_chunk_age / 2`** (1 h con el
  default de 2 h), no la retención. Verificado: un atraso de 4 días se
  descartó con `400 entry too far behind` aun con `reject_old_samples_max_age`
  holgado. La siembra histórica del lab solo funciona sobre streams vacíos.
- **El tope de ingesta condiciona el drenaje del buffer.** Tras un corte,
  Alloy empuja el atraso en ráfaga; con `ingestion_rate_mb` bajo el atraso no
  drena. Se dimensiona con el volumen real del sitio.
- **`unordered_writes` es obligatorio** para que el atraso drene: al
  recuperarse, Alloy escribe líneas viejas sobre streams que ya tienen líneas
  nuevas.
- Los directorios bajo `DATA_DIR` deben pertenecer al UID de cada imagen
  (`10001` Loki, `472` Grafana, `101` rsyslog); root no sirve.
- El buffer se implementa con **archivos diarios y borrado por edad**
  (`find -mtime +N`), no con `logrotate`: nunca se renombra ni se trunca un
  archivo que Alloy está leyendo.

---

## 11. Futuro evaluado: analítica de flujos (Akvorado)

**Estado:** evaluado, no adoptado. Se registra para no re-litigarlo y para
tener criterios de entrada explícitos.

Akvorado recibe NetFlow v5/v9, IPFIX y sFlow, enriquece cada flujo con nombre y
velocidad de interfaz (SNMP o gNMI), GeoIP y, opcionalmente, rutas BGP por BMP,
y lo almacena en ClickHouse. Trae una consola web propia y un plugin de
Grafana.

Componentes: `inlet` (recibe UDP y publica en Kafka), `outlet` (decodifica,
enriquece y escribe en ClickHouse), `orchestrator` (configura el resto) y
`console` (UI). **Requiere Kafka y ClickHouse**, además de los cuatro
servicios de Akvorado.

### Por qué es atractivo

- Responde preguntas que los contadores SNMP de Zabbix no responden: qué
  conversaciones componen el tráfico de una interfaz, top talkers, mezcla por
  protocolo, detección de abuso o exfiltración, planificación de capacidad.
- El enriquecimiento por SNMP reutiliza el acceso que ya tenemos: Zabbix
  consulta los mismos equipos.
- Grafana ya está en el plan, así que el consumo es natural.

### Por qué no ahora

- Es un **tercer stack con estado** por sitio (Kafka + ClickHouse): respaldo,
  upgrade, tuning y disco propios. El costo operativo es muy superior al de
  Loki.
- Piso de recursos alto: 4 vCPU con AVX2, 8 GB de RAM (32 GB recomendado),
  50–100 GB de disco. ClickHouse exige x86-64-v3/AVX2 y algunas VMs lo ocultan.
  Con el relevamiento actual, un sitio queda excluido por RAM y otro por disco
  libre.
- Exige habilitar exportación de flujos en cada familia de equipos, definir
  muestreo y abrir otro receptor UDP sin autenticación.
- Sin una pregunta concreta y un consumidor identificado, es infraestructura
  sin uso.

### Criterios de entrada (para abrir un ADR de flujos)

1. Una pregunta real que los contadores SNMP no respondan, con consumidor
   nombrado (capacidad, abuso, QoS, facturación).
2. Un host con ≥ 4 vCPU, ≥ 8 GB de RAM y ≥ 100 GB de disco **por encima** del
   uso actual, con AVX2 expuesto.
3. Familias de equipos verificadas como exportadoras de NetFlow/IPFIX/sFlow,
   no supuestas.
4. Retención de flujos decidida y disco presupuestado.
5. Colector alcanzable solo desde la red de gestión; nunca desde la WAN.

### Ubicación si se adopta

| Opción | Ventaja | Costo |
| --- | --- | --- |
| Por sitio | Sin dependencia externa; datos en el sitio | Solo donde el perfil lo permita; un stack más por cliente |
| Hub central | Un solo despliegue; vista multi-sitio | Dependencia compartida y flujos de varios clientes en un host |

### Alternativas evaluadas

`ntopng` (más liviano, menos escalable), `ElastiFlow` (propietario),
`pmacct` + base propia (máximo control, máximo trabajo), o quedarse con
contadores SNMP de Zabbix y Grafana. El diferencial de Akvorado es el pipeline
de flujos empaquetado y su consola.
