# Clases de incidente y servicios críticos

Las dos piezas que convierten un dato en una respuesta: **qué significa** una
alarma y **qué importa** para el cliente.

---

## 1. Catálogo de clases (D9)

Archivo canónico: `docker/observability/clases/clases.yaml`.

Cada clase une tres cosas:

| Campo | Para qué |
| --- | --- |
| `patrones_zabbix` | reconocer la alarma por su nombre |
| `logql` | traer la evidencia del log (`$HOST` se reemplaza) |
| `accion` | qué sugeriría el técnico |

Clases cubiertas (13): enlace, fibra, tráfico, wifi, disco, memoria, ruteo,
servicios, energía, seguridad, cpu, latencia y *desconocido*. **El orden importa**: las específicas van antes que las genéricas.

Todas las consultas están **validadas contra Loki** con datos reales del lab.

### Cómo se usa

- **Dashboards**: el filtro de logs de una clase es la misma consulta.
- **Agente (fase N)**: dado un problema de Zabbix, busca la clase por
  `patrones_zabbix` y consulta `logql` para la evidencia.
- **Depuración de ruido**: si una clase no tiene evidencia útil, probablemente
  sea ruido.

### Extender

Agregar una clase es agregar un bloque a `clases.yaml` y validar su consulta:

```bash
# valida sintaxis y que devuelva algo
python3 - <<'PY'
...  # ver §Validación
PY
```

Reglas: un `id` estable, patrones en minúscula, y una `accion` que un técnico
pueda ejecutar sin investigar.

---

## 2. Servicios críticos (D10)

Esquema: `docker/observability/clases/servicios.ejemplo.yaml`.
Ejemplo funcional del lab: `docker/observability/clases/servicios-lab.yml`.
El archivo real vive en el **repo privado del cliente**.

### Generación

```bash
python3 scripts/gen_servicios.py docker/observability/clases/servicios-lab.yml --resolve
```

Crea el dashboard **Cliente → Estado de servicios** (uid `servicios`): un panel
por servicio con tres estados.

### Reglas por clase de incidente

El estado **no** sale de la severidad pelada: sale de qué clase de incidente
es y de cuánto afecta a ese servicio. La tabla vive en
`clases.yaml › reglas_por_clase`:

| Clase | Crítico desde | Degradado desde | Por qué |
| --- | --- | --- | --- |
| enlace | Media (3) | Aviso (2) | un enlace caído es servicio caído |
| latencia | Alta (4) | Aviso (2) | degrada antes de romper |
| wifi | Alta (4) | Aviso (2) | usuarios afectados |
| fibra | Aviso (2) | Aviso (2) | pérdida de señal es crítica |
| disco | Desastre (5) | Media (3) | avisa antes de llenarse |
| memoria | Alta (4) | Media (3) | OOM rompe |
| cpu | Desastre (5) | Alta (4) | picos altos pero transitorios |
| energía | Media (3) | Aviso (2) | batería tiene autonomía |
| servicios | Alta (4) | Media (3) | servicio detenido |
| ruteo | Media (3) | Aviso (2) | afecta alcance |
| seguridad | Desastre (5) | Alta (4) | no degrada por un deny aislado |
| *desconocido* | Alta (4) | — | un problema que no matchea ninguna clase y es Alta o superior nunca deja el servicio en verde; los avisos desconocidos no mueven el semáforo (ruido) |

Un problema se clasifica buscando su nombre contra `patrones_zabbix` de cada
clase. **Los patrones tienen que cubrir los nombres reales del sitio**: en el
lab el trigger dice `Perdida 40%` y el patrón era `perdida de paquetes`; no
matcheaba y el servicio quedaba OK con pérdida de paquetes activa.

### Override por servicio

Un servicio puede endurecer o relajar una clase:

```yaml
- nombre: Internet
  hosts: [RTR-WAN, FW-SITIO]
  reglas:
    latencia: {critico: 3, degradado: 2}   # Internet es más sensible
```

Debajo del estado hay una tabla con los problemas de todos los servicios.

Define, por sitio:

- qué servicios existen (con nombre de negocio, no de host),
- su criticidad y horario,
- de qué dependen.

Con eso: el dashboard puede mostrar "Internet: degradado" en vez de "RTR-WAN
tiene pérdida", y el agente puede priorizar y evitar reportar hijos cuando el
padre está caído.

---

## 3. Por qué esto destraba al agente

Sin catálogo, el agente puede describir el síntoma pero no decidir. Con
catálogo puede responder:

> "Facturación está degradada porque el enlace de Internet perdió paquetes
> desde las 14:32 (log: LINK down en RTR-WAN). Sugiero revisar el enlace y no
> tocar el servidor."

Eso es lo que pediste: que el técnico no tenga que buscar dónde mirar.

---

## 4. Evaluación del clasificador (N6)

`scripts/evaluar_clasificador.py` mide contra un banco de **incidentes reales**
anonymizados (`tests/fixtures/incidentes.yaml`).

Dos conjuntos, con roles distintos:

| Conjunto | Uso | Casos |
| --- | --- | --- |
| **calibración** | se mira para corregir patrones | 31 |
| **retención** (`holdout`) | **no se toca**; es la medición real | 10 |

La puerta es la **retención**: sin ≥ 80 % ahí, no se habilitan acciones.

### Resultado actual

- Retención: **90 %** (9/10) → cumple.
- Calibración: 100 % (31/31) → esperado, porque se usó para ajustar.

### Huecos documentados (no se "arreglan" mirando la retención)

| Caso | Esperado | Obtenido | Por qué |
| --- | --- | --- | --- |
| `Interface Gi1/0/4: high error rate` | enlace | desconocido | "high error rate" en inglés no matchea "tasa de errores" (wifi) ni enlace |

Cuando el patrón se corrija, se valida con el **próximo lote** de casos, no con
este. Regla: los casos del banco se agregan **antes** de ajustar, y la
retención entra en circulación una sola vez.

### Hallazgos que la medición ya destapó

- `Enlace caído` (con acento) no matcheaba.
- `Sin respuesta a ping` no estaba como patrón de enlace.
- `PON-2-LOS: perdida de senal` caía en latencia (genérica) en vez de fibra.
- `pon` matcheaba dentro de `responses` → `Disk read/write...` se clasificaba
  como fibra.
- `High swap space usage` caía en disco por el patrón `space`.

---

## 5. Evaluación automática (sin etiquetado humano)

`scripts/evaluar_real.py` mide contra incidentes **reales**, y la "verdad" no la
decide una persona: sale de la **clave del item** que disparó el trigger
(`mapeo_items` en `clases.yaml`).

```bash
python3 scripts/evaluar_real.py --list     # qué estamos listando como incidentes
python3 scripts/evaluar_real.py            # precisión + discrepancias
python3 scripts/evaluar_real.py --append   # guarda discrepancias como candidatos
python3 scripts/evaluar_real.py --promote  # pasa los confirmados a retención
```

### El ciclo

```
trigger → item (clave) → clase esperada        (automático)
        → nombre del trigger → clase obtenida  (clasificador)
        → si difieren: candidato a revisar     (append)
        → humano confirma                     (estado: confirmado)
        → entra a retención                   (promote)
```

El técnico **solo interviene cuando se le pide**: para ver la tabla
(`--list`) o para confirmar una discrepancia. No etiqueta de cero.

**Dónde viven los archivos.** Los incidentes reales llevan nombres de equipos
del sitio: candidatos y banco del sitio van a `client/` del repo privado
(`client/incidentes-candidatos.yaml`, `client/incidentes.yaml`).
`tests/fixtures/incidentes.yaml` es el banco genérico **anonimizado** y no se
toca desde un sitio. `evaluar_real.py` se niega a escribir dentro de
`tests/fixtures/` a propósito.

### Última medición (lab, 30 días)

- 500 incidentes, 499 con clase derivada, **100 % de coincidencia**.
- 1 sin etiqueta: el item no está en `mapeo_items` (queda visible como hueco).

### Corregir la tabla

1. `--list` muestra los prefijos de item y su clase.
2. Se agrega o corrige un prefijo en `clases.yaml › mapeo_items`.
3. Se vuelve a medir. Los candidatos confirmados se promueven con `--promote`.
