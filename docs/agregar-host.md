# Agregar un host o una métrica nueva

Dos caminos según el origen del dato. En los dos, la regla es la misma:
**si el host no existe en Zabbix, no hay dashboard ni agente que lo vea.**

---

## 1. Verificación previa (30 segundos, evita el 90 % de los dolores)

Antes de crear nada, comprobar que Zabbix puede asignar IDs. Es un fallo
clásico después de un restore o una importación de plantilla:

```bash
docker exec zabbix-postgres psql -U zabbix -d zabbix -tAc \
  "SELECT (SELECT nextid FROM ids WHERE table_name='items' AND field_name='itemid') AS next,
          (SELECT max(itemid)+1 FROM items) AS need;"
```

Si `next` < `need`, cualquier alta falla con `duplicate key ... items_pkey`.
Se repara una vez:

```sql
UPDATE ids SET nextid = (SELECT max(itemid)+1 FROM items)
 WHERE table_name='items' AND field_name='itemid';
```

Repetir para `hosts/hostid` y `triggers/triggerid` si hace falta.

---

## 2. Host real (métricas por agente, SNMP o HTTP)

### 2.1 Lo que hay que saber antes

| Pregunta | Por qué |
| --- | --- |
| ¿Cómo se monitorea? agente, SNMP, HTTP, IPMI | define el tipo de interfaz |
| ¿IP y puerto? | interfaz del host |
| ¿Grupo de hosts? | permisos y filtros de dashboard |
| ¿Plantilla? | qué se mide y qué dispara |
| ¿Es crítico para el cliente? | entra en el "context pack" |

### 2.2 Alta

1. Crear el host en Zabbix (UI o API) con la interfaz correspondiente.
2. Linkear la plantilla. **No crear items a mano** si la plantilla existe.
3. Esperar el primer ciclo de recolección (1–5 min).
4. Verificar que los items reportan: ningún item en estado *not supported*.

### 2.3 Verificación (obligatoria, no opcional)

```bash
# items sin datos de ese host
docker exec zabbix-postgres psql -U zabbix -d zabbix -tAc "
SELECT i.name, r.error FROM items i
JOIN hosts h ON h.hostid=i.hostid
LEFT JOIN item_rtdata r USING (itemid)
WHERE h.host='NOMBRE' AND i.status=0 AND r.state=1;"
```

Si devuelve filas, el host existe pero **no está midiendo**: eso es peor que no
tenerlo, porque el dashboard lo muestra verde. Corregir antes de dar por
cerrado el alta.

### 2.4 Cierre

- Confirmar que aparece en `Red y capacidad` (grupo elegido) y en `Salud del
  monitoreo` sin items sin datos.
- Si es crítico, agregarlo al context pack del cliente (servicio → hosts).

---

## 3. Host simulado (laboratorio)

1. Agregar el nombre a `SIM_HOSTS` en `scripts/bootstrap_lab_sim.py`.
2. Agregar sus métricas en `docker/simulator/scenarios.yml`
   (`devices.<host>.metrics`) y, si manda logs, en `syslog.devices`.
3. Correr el bootstrap y reiniciar el simulador:

```bash
ZABBIX_URL=http://<host-zabbix>/api_jsonrpc.php ZABBIX_PASSWORD=<admin> \
  python3 scripts/bootstrap_lab_sim.py
docker compose -f docker/docker-compose.yml -f docker/docker-compose.lab.yml \
  -f docker/docker-compose.observability.yml --profile lab --profile observability \
  up -d --build lab-simulator
```

4. Verificar que el trapper responde `sent: 1` (no `failed`) en los logs.

---

## 4. Métrica nueva en una plantilla existente

1. Editar la plantilla (`templates/*.yaml` o la UI).
2. Si es una plantilla del repo, importar con `bootstrap_lab_sim.py`
   (`updateExisting: True`) y confirmar propagación a los hosts linkeados.
3. Verificar en el host que el item apareció y no está *not supported*.
4. Si tiene trigger, probar el disparo con un valor fuera de umbral.

---

## 5. Reglas que evitan el dolor

- **Una métrica, un dueño.** Si la plantilla la define, no se replica a mano.
- **Nada de items huérfanos**: antes de crear, buscar si ya existe por clave.
- **El alta no termina en "creado"**, termina en "reportando y sin
  not-supported".
- **Si el host es crítico, se documenta** en el context pack del cliente.
- El agente (noc-agent) debe recibir del alta: nombre, grupo, plantilla y si
  es crítico. Sin eso no puede explicar ni priorizar nada.
