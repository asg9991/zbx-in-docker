# Respaldo y restauración de la observabilidad

Qué se respalda, qué no, y cómo se prueba. **Un respaldo sin restauración
probada no es un respaldo.**

---

## 1. Qué se respalda

| Dato | ¿Respaldo? | Por qué |
| --- | --- | --- |
| Dashboards y datasources | **No hace falta** | están en el repo (provisioning) |
| `grafana.db` (usuarios, preferencias) | **Sí** | no está en el repo |
| Loki (`${DATA_DIR}/loki`) | No | retención corta; no es fuente de verdad |
| Zabbix (PostgreSQL) | Fuera de alcance | ya tiene su propio respaldo |
| `docker/.env` | **Sí** (fuera de git) | token y credenciales |

```bash
sudo ./scripts/backup_observability.sh /ruta/de/backups
```

Genera `grafana-AAAAMMDD-HHMM.db.gz`. El `sudo` no es opcional: Grafana
escribe la base como uid `472` y el operador no puede leerla. La copia usa la
API de backup de SQLite (consistente con la base abierta) y verifica
`integrity_check`; si el archivo no se puede leer, el script lo dice y sale.

---

## 2. Restauración (drill, en el lab)

Se corre **con confirmación explícita** porque reemplaza la base local.

```bash
# 1. parar Grafana
cd docker
docker compose -f docker-compose.yml -f docker-compose.lab.yml \
  -f docker-compose.observability.yml --profile observability stop grafana

# 2. respaldar la actual y restaurar
cp "$DATA_DIR/grafana/grafana.db" /tmp/grafana.db.pre-restore
gunzip -c /ruta/backups/grafana-XXXX.db.gz > "$DATA_DIR/grafana/grafana.db"
chown 472:0 "$DATA_DIR/grafana/grafana.db"

# 3. levantar y verificar
docker compose ... up -d grafana
```

Verificación (las tres cosas):

1. Grafana responde 200 y los **datasources** están (vienen del repo).
2. Los **dashboards** están todos (vienen del repo, no de la base).
3. El usuario admin entra con la contraseña del `.env`.

Si algo falla: restaurar `/tmp/grafana.db.pre-restore` y volver a levantar.

---

## 3. Prueba periódica

| Cuándo | Qué |
| --- | --- |
| Antes de cada actualización de Grafana | respaldo |
| Cada 6 meses | **drill completo** de restauración en el lab |
| Al cerrar un cliente | documentar en su repo la ruta y la fecha del respaldo |

### Lo que el drill demuestra

Que perder la base de Grafana **no pierde dashboards**: vuelven del repo. El
respaldo de la base solo conserva usuarios y preferencias, que es lo único
irrecuperable.
