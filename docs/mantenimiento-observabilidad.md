# Mantenimiento de la capa de observabilidad

Qué hay que cuidar, cada cuánto, y cómo explicar las piezas nuevas.

---

## 1. Qué es el datasource "Zabbix API" (Infinity)

### En una frase

Infinity es un **cliente HTTP genérico**: hace una request a una URL y convierte
la respuesta JSON en una tabla. No sabe nada de Zabbix; nosotros le decimos qué
llamar y cómo leer la respuesta.

```
Grafana ──▶ Infinity (datasource) ──POST──▶ api_jsonrpc.php
                    │                        (token Bearer, solo lectura)
                    └──◀── JSON {result:[...]} ──▶ root_selector + columnas ──▶ tabla
```

### Cómo se configura una consulta

| Pieza | Qué hace |
| --- | --- |
| `url` | a dónde llamar (`http://zabbix-web:8080/api_jsonrpc.php`) |
| `url_options` | método POST, body JSON y `Content-Type: application/json-rpc` |
| `parser` + `root_selector` | cómo llegar al array de datos (`result`, o JSONata si empieza con `$`) |
| `columns` | qué campos del JSON son columnas y cómo se llaman |

### Por qué lo usamos

El plugin oficial de Zabbix entiende el modelo de Zabbix y dibuja sus propios
paneles, pero:

- **no expone** las consultas de problemas/items por la API de Grafana
  (`non-metrics queries are not supported`), y
- **no tiene traducciones**: sus columnas y severidades salen en inglés.

Infinity nos da las filas crudas y armamos tablas nuestras, en español, con
nuestros colores y links.

### Costo y riesgos

- Hay que escribir las consultas y mapear columnas: es más trabajo inicial.
- Si Zabbix cambia el formato de respuesta, se ajusta el dashboard.
- Seguridad: el datasource es server-side (`proxy`), con `allowedHosts`
  limitado a `zabbix-web` y un token **Bearer de solo lectura** guardado en
  `secureJsonData` (no se ve en el JSON del dashboard).

---

## 2. Versiones y política de actualización

| Componente | Versión fijada | Por qué |
| --- | --- | --- |
| `grafana/grafana` | 13.3.1 | presentación |
| `grafana/loki` | 3.7.10 | logs |
| `grafana/alloy` | v1.22.0 | colector |
| `rsyslog/rsyslog` | 2026-10 | receptor + buffer |
| plugin `alexanderzobnin-zabbix-app` | 6.10.3 | datasource Zabbix |
| plugin `yesoreyeram-infinity-datasource` | 4.1.8 | tablas desde la API |
| `alpine` (retención/diagnóstico) | 3.22 | utilidades |

Reglas:

- **Nunca `latest`.** Un tag rodante es un cambio sin revisión.
- Los plugins se **hornean en la imagen**: `GF_INSTALL_PLUGINS` no fija versión.
- Actualizar en el lab primero, con el mismo `.env` y los datos del lab.
- Registrar en este archivo y en el ADR (§10) la versión y la fecha.

### Cada cuánto revisar

| Qué | Frecuencia | Señal |
| --- | --- | --- |
| Parches de seguridad (Grafana, Loki) | mensual | CVE o aviso del proyecto |
| Minor de Grafana / Alloy / Loki | cada 6 meses | releases estables, no RC |
| Plugins (Zabbix, Infinity) | con cada minor de Grafana | compatibilidad |
| Zabbix | solo LTS | no mezclar con el ciclo de observabilidad |

### Checklist de actualización (siempre igual)

1. `docker compose config --quiet` con los tres archivos.
2. Levantar en el lab y esperar `healthy`.
3. Verificar todos los dashboards presentes (200) y los datasources (`health` OK).
   `scripts/check_all.sh` los recorre desde los archivos, sin lista fija.
4. Revisar logs: sin `error`, sin `timestamp too new`, sin `dropping data`.
5. Repetir una consulta de cada datasource (Loki, Zabbix, Infinity).
6. Anotar la versión nueva en la tabla y en el ADR.

---

## 3. Riesgos de mediano plazo

| Riesgo | Impacto | Mitigación |
| --- | --- | --- |
| El **WAL de Alloy** es experimental | puede cambiar entre versiones | versión fijada; si rompe, se desactiva y el buffer de archivo sigue cubriendo |
| Infinity 4.x cambia el esquema de consulta | dashboards de problemas/salud dejan de traer datos | las consultas están en 3 dashboards; probar tras cada upgrade |
| Crecimiento de Loki | disco del sitio | retención y tope de ingesta por sitio (`.env`), ya definidos |
| Node Graph / Canvas evolucionan | el mapa puede requerir ajustes | el mapa usa solo campos estándar (`id/title/color`) y aristas inline |
| Token de API sin rotación | credencial de largo plazo | rotación en el runbook del sitio; el usuario es de solo lectura |
| Token de lectura de Grafana (`GF_READ_TOKEN`) | credencial de largo plazo | es de una service account con rol Viewer; se revoca y regenera en Grafana |
| Un solo host para todo | cae Grafana y se pierde la vista (Zabbix sigue alertando) | el ADR ya define el perfil por sitio; Zabbix es independiente |

---

## 4. Deuda técnica conocida

- Los KPIs no enlazan a Zabbix: falta definir `ZABBIX_PUBLIC_URL` por sitio.
- `Tráfico de Red` y `Capacidades` usan un selector de grupo cuyo valor por
  defecto es el del lab: en un sitio se fija al grupo del cliente.
- El "por qué" de un problema (no solo el dato) depende del noc-agent (fase N).
- El dashboard de servicios evalúa la clase en JSONata (dashboard en vivo) y en
  Python (digest): las dos salen del mismo `clases.yaml`, pero la lógica está
  escrita dos veces (una por lenguaje).

---

## 5. Respaldo

| Qué | Cómo | Frecuencia |
| --- | --- | --- |
| Dashboards y datasources | están en el repo (provisioning) | con cada commit |
| Base de Grafana (usuarios, preferencias) | `${DATA_DIR}/grafana/grafana.db` | diario |
| Loki | `${DATA_DIR}/loki` (retención corta, no crítico) | opcional |
| Zabbix | fuera de alcance de esta capa | ya cubierto |

La prueba de restauración se hace en el lab: borrar la DB de Grafana, levantar y
confirmar que dashboards/datasources vuelven del repositorio.
