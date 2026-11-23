# Manifiesto de dashboards

El ADR 0001 (§D4, §10) exige registrar el origen de cada dashboard curado.
Un dashboard propio no tiene ID ni revisión de grafana.com: se registra como
local y su revisión es el commit del repo.

El árbol define la carpeta (`foldersFromFilesStructure: true`). La **audiencia**
sale de las etiquetas: `cliente`, `tecnico` o `mapa` (+ `nav`). Los dashboards
de drill-down no llevan `nav` y no se listan.

| Carpeta | UID | Título | Audiencia | Origen |
| --- | --- | --- | --- | --- |
| Cliente | `estado-servicio` | Estado de la Red | cliente | Local |
| Cliente | `red-capacidad` | Tráfico de Red | cliente | Local |
| Cliente | `capacidades` | Capacidades | cliente | Local |
| Cliente | `servicios` | Estado de servicios | cliente | Generado (`gen_servicios.py`) |
| Tecnico | `tecnico-observabilidad` | Tecnico - observabilidad y logs | tecnico | Local |
| Tecnico | `problemas` | Problemas | tecnico | Local |
| Tecnico | `eventos` | Eventos de red | tecnico | Local |
| Tecnico | `salud-monitoreo` | Salud del monitoreo | tecnico | Local |
| Tecnico | `mapa-lab` | Mapa de red | mapa | Generado (`gen_map.py`) |
| Tecnico | `mapa-lab-core` | Mapa - núcleo y servidores | mapa | Generado (`gen_map.py`) |
| Tecnico | `equipo` | Equipo (drill-down) | — (no listado) | Local |

Reglas:

- Ningún dashboard descargado de grafana.com: todos son propios o generados.
- `allowUiUpdates: false`: la UI no edita lo que se versiona.
- `disableDeletion: false`: si un dashboard se quita del repo, provisioning lo
  borra.
- Cambiar un dashboard es un cambio de código: JSON en el repo, no en la DB.
