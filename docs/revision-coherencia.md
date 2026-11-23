# Revisión de coherencia (2026-11-22)

Revisión completa del stack tras la fase D y el arranque de la fase N.
No agrega features: verifica que lo construido sea consistente entre sí.

---

## 1. Inventario por capa

| Capa | Artefactos |
| --- | --- |
| **Infra** | `docker-compose.observability.yml`, `observability/{rsyslog,loki,alloy,grafana}` |
| **Datos** | Zabbix (fuente), Loki (logs), `DATA_DIR` persistente |
| **Consultas** | `scripts/observability/queries.py` (11 consultas canónicas) |
| **Dashboards** | 11 (4 cliente, 6 técnico, 1 drill-down) |
| **Generadores** | `gen_queries.py`, `gen_map.py`, `gen_servicios.py`, `nav_links.py` |
| **Contexto** | `clases.yaml` (13 clases + reglas), `servicios*.yml` |
| **Agente (fase N)** | `digest.py`, `contrato-digest.md`, `evaluar_clasificador.py` |
| **Docs** | ADR + 8 documentos operativos |

Verificación automatizada: **`scripts/check_all.sh`** (compose, generadores,
contexto, clasificador, 10 dashboards). Estado actual: **TODO OK**.

---

## 2. Coherencias verificadas

| Verificación | Evidencia |
| --- | --- |
| Un solo motor de alertas | Ningún dashboard crea alertas; Zabbix sigue siendo el único |
| Una sola fuente de dato | Grafana y el digest leen la misma API y el mismo Loki |
| Consultas centralizadas | `gen_queries.py --check` sin drift (11 consultas) |
| Navegación consistente | `nav_links.py --check`; 3 menús, audiencias válidas |
| Contexto válido | `digest.py --check`: 13 clases, 5 servicios, sin referencias rotas |
| Clasificador medido | Retención 90 % (≥ 80 %) |
| Sin puertos nuevos | Solo el receptor syslog, en loopback |
| Sin secretos en git | Token en `docker/.env` (ignorado) |

---

## 3. Incoherencias encontradas

| # | Incoherencia | Estado |
| --- | --- | --- |
| 1 | `docs/` decía "12 clases"; hay 13 | **corregido** |
| 2 | `MANIFEST.md` listaba 2 de 10 dashboards | **corregido** |
| 3 | `README` de observabilidad no listaba `servicios` ni `equipo` | **corregido** |
| 4 | La descripción de `Estado del servicio` mencionaba "tendencia de 7 días" (ya no existe) | **corregido** |
| 5 | Función `estado_servicio` en `queries.py` era código muerto | **eliminado** |
| 6 | D11–D16 figuran como pendientes pero varias están parcialmente hechas | **estados corregidos** |
| 7 | **Dos dashboards de cliente se solapan**: `estado-servicio` y `servicios` | **decisión abierta** (§5.1) |

---

## 4. Deuda real (no cosmética)

| Deuda | Por qué importa |
| --- | --- |
| Sin test de backup/restauración de Grafana/Loki (D22) | es el único punto donde un error se descubre tarde |
| Sin alerta de disco libre del host | el riesgo #4 del documento de riesgos sigue abierto |
| `servicios.yml` de clientes sin completar | sin eso, el dashboard de servicios muestra datos del lab |
| Generadores sin tests unitarios | se validan corriéndolos; `check_all.sh` es la red de seguridad |
| Sin CI | `check_all.sh` está listo para enchufar |

---

## 5. Decisiones abiertas (necesitan tu criterio)

### 5.1 ¿Qué ve el cliente primero?

Hoy hay dos vistas de cliente:

- **Estado del servicio**: semáforos de problemas + tabla + logs.
- **Estado de servicios**: un panel por servicio de negocio (OK/Degradado/Crítico).

Mi recomendación: **`servicios` como entrada** (habla el idioma del cliente) y
`estado-servicio` como segundo nivel. Pero no lo cambio sin tu OK porque cambia
el home de la organización.

### 5.2 Alcance del "context pack"

Hoy son dos YAML (`clases.yaml` genérico + `servicios.yml` del sitio). Falta
definir si el cliente puede editar reglas o si solo las ajustamos nosotros.

---

## 6. N6 en contexto de cliente

El banco de evaluación no es un test de software: es el **contrato de
confianza** con ese sitio.

1. **Se arma con sus incidentes reales.** Se exportan los nombres de trigger de
   los últimos 90 días y el técnico etiqueta cada uno con su clase.
2. **Se divide en calibración y retención** (70/30). La calibración se usa para
   ajustar patrones; la retención **no se mira** hasta la medición.
3. **La puerta es por cliente**: ese sitio no habilita acciones del agente
   (N7/N8) hasta que *su* retención dé ≥ 80 %.
4. **El banco vive en el repo privado del cliente** (tiene nombres de equipos).
   El público mantiene solo casos anonimizados.
5. **Se re-mide** cuando cambian patrones, reglas o cuando aparecen clases
   nuevas. Cada lote de incidentes nuevos entra como retención del siguiente
   ciclo: así el número no se infla ajustando sobre lo mismo.
6. **El hueco se documenta, no se esconde.** El caso `high error rate` que hoy
   falla queda listado y se valida con el próximo lote.

Ese es el mecanismo que evita el riesgo mayor: un agente que "parece" acertar
porque se midió contra los mismos casos con los que se lo entrenó.

---

## 7. Correcciones de la revisión del 2026-11-23

Revisión integral con el stack corriendo. Lo corregido:

| Corrección | Evidencia |
| --- | --- |
| Un problema sin clase conocida ya no deja el servicio en verde si es Alta+ | `regla_desconocido` en `clases.yaml`, aplicada en `digest.py` y en `gen_servicios.py` |
| Los incidentes reales del banco van a `client/`, no a `tests/fixtures` | `evaluar_real.py` se niega a escribir en el banco genérico |
| Respaldo de Grafana consistente y ejecutable | `backup_observability.sh`: API de backup de SQLite + `integrity_check`; requiere `sudo` |
| `nav_links.py --check` falla si hay una audiencia inválida | exit code atado a los errores, no solo a los cambios |
| Loki acepta el atraso que promete drenar | `reject_old_samples_max_age` desde `LOKI_MAX_BACKLOG` |
| Scripts de lectura sin la cuenta admin | `GF_READ_TOKEN` (service account Viewer) |
| Se quitaron del ADR las referencias a un procesador de eventos externo | el ADR describe solo lo que vive en este repo |
| Se definió "sitio" y se corrigió la promesa de vista multi-sitio | ADR §1 y D8 |
| Se corrigió la promesa de drenaje del buffer | Loki acepta desorden solo dentro de `max_chunk_age/2` (~1 h): verificado con un atraso de 4 días que se descartó con `400 entry too far behind` |

Pendiente y no verificable acá: drill de restauración (D22), criterio 9 (corte
de 15 min), presupuesto de disco/RAM a 7 días en un sitio real.
