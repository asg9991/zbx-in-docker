# Riesgos de mantenimiento y alternativas

Evaluación de cada pieza que puede doler en 6–12 meses, con el costo real de
cambiarla. Ordenado por impacto.

---

## 1. Datasource Infinity (tablas desde la API de Zabbix)

**Riesgo.** Infinity 4.x es un plugin de terceros con cambios de esquema entre
minor (ya nos pasó con `auth_method`, `url_options.data` y los selectores). Si
cambia, los dashboards que lo usan dejan de traer datos (hoy: estado de la red,
servicios, problemas, salud del monitoreo, equipo y los mapas).

| Alternativa | Costo de mantenimiento | Veredicto |
| --- | --- | --- |
| **Quedarse con Infinity** y centralizar las consultas | Bajo: 3 dashboards, consultas repetidas que se pueden copiar de un archivo de referencia | **Recomendado** |
| Volver al panel del plugin de Zabbix | Cero plugins, pero vuelve el inglés y no hay tablas propias | Solo como plan B |
| Exportador propio a Loki/Postgres | Medio-alto: un servicio más, copia de datos, drift | No |
| Script que consulte la API y genere JSON estáticos | Alto: pierde el tiempo real | No |

**Mitigación concreta:** las consultas viven en un solo archivo
(`scripts/observability/queries.py`) y los dashboards solo las referencian por
nombre; `scripts/gen_queries.py --check` detecta cualquier variante suelta.
Antes de subir de versión de Grafana, probar los dashboards que usan Infinity.

---

## 2. WAL de Alloy (experimental)

**Riesgo.** Requiere `--stability.level=experimental`. Puede cambiar o
desaparecer entre versiones.

| Alternativa | Costo | Veredicto |
| --- | --- | --- |
| **WAL activo** | Bajo: si se rompe, se quita el bloque y vuelve al buffer de archivo | **Recomendado hoy** |
| Sin WAL | Se pierde solo la ventana de crash sucio (segundos) | Aceptable |
| Buffer propio (rsyslog con cola en disco) | Medio: más configuración | Innecesario: el archivo ya es el buffer |

**Mitigación:** el WAL es una mejora, no un requisito. Documentado cómo
desactivarlo en una línea.

---

## 3. Mapa de red

**Riesgo.** Node Graph no permite posicionar nodos: el layout es automático.
En radial se superpone (ilegible), en grilla pierde la topología (es una lista,
no un mapa).

| Alternativa | Costo de mantenimiento | Veredicto |
| --- | --- | --- |
| Node Graph | Cero: estado automático por host | Descartado: layout automático, no es un mapa |
| **Canvas generado desde `topology.yml`** | Medio: un generador chico y una topología por sitio | **Implementado** (`scripts/gen_map.py`, D-M1) |
| Canvas a mano | Alto: cada cambio de red se edita a mano | No |
| Plugin Flowcharting | Medio-alto: plugin extra, compatibilidad con cada Grafana | No |
| Mapa nativo de Zabbix | Bajo, pero saca al cliente de Grafana y sigue siendo manual | Solo si el cliente ya vive en Zabbix |
| Imagen estática | Cero, pero no refleja estado | No |

**Implementado:** `topology.yml` por sitio (niveles, enlaces) → `gen_map.py`
→ JSON de Canvas con un elemento por equipo, color según problemas y link al
detalle (ver `docs/mapas-red.md`).

---

## 4. Crecimiento de Loki

**Riesgo.** Un equipo ruidoso llena el disco del sitio.

| Alternativa | Costo | Veredicto |
| --- | --- | --- |
| **Retención + tope por sitio** (actual) | Bajo | **Recomendado** |
| Sin retención | Ninguno, pero el disco es finito | No |
| Enviar todo al hub | Depende de la red del sitio | Solo en perfil reducido |

**Mitigación:** ya hay `LOKI_RETENTION` e `ingestion_rate_mb` por sitio y
`scripts/check_disk.sh` para cron; falta el trigger de Zabbix sobre el
filesystem del host, que es la alerta confiable.

---

## 5. Token de API sin rotación

**Riesgo.** Credencial de largo plazo, sin vencimiento.

| Alternativa | Costo | Veredicto |
| --- | --- | --- |
| **Token de solo lectura + rotación manual en el runbook** | Bajo | **Recomendado** |
| Token con expiración | Medio: hay que renovarlo o el dashboard se rompe | Riesgoso sin automatización |
| Usuario/password en el datasource | Peor: credencial reutilizable en más lugares | No |

**Mitigación:** documentar la rotación y probar que el dashboard sigue andando
con el token nuevo (es un campo del `.env`). Lo mismo aplica a `GF_READ_TOKEN`
(service account `Viewer` de Grafana): se revoca y regenera sin tocar la
cuenta admin.

---

## 6. Un solo host para todo

**Riesgo.** Si cae el host, se pierde la vista. **Zabbix sigue alertando** por
Telegram: las alertas no dependen de Grafana.

| Alternativa | Costo | Veredicto |
| --- | --- | --- |
| **Perfil por sitio** (ADR D8) | Bajo | **Recomendado** |
| Hub central para varios clientes | Medio: datos de varios clientes en un host | Solo si el cliente lo acepta |
| Alta disponibilidad | Alto: fuera de escala para estos sitios | No por ahora |

---

## 7. Regla general

Antes de agregar una pieza nueva, dos preguntas:

1. **¿Reemplaza algo o se suma?** Si se suma, tiene que resolver un problema que
   hoy duele en un sitio real.
2. **¿Quién la actualiza en 12 meses?** Si la respuesta es "nadie", no entra.

Estado actual: 4 contenedores nuevos (Loki, Grafana, Alloy, rsyslog) + 1 sidecar
de retención + 2 plugins. Es el mínimo razonable para logs y presentación sin
meter Prometheus.
