# Castellanización de alarmas (ES) — estrategia y procedimiento

Objetivo: que las alarmas Zabbix lleguen en español accesible para técnicos
hispanohablantes, sin tener que aprender inglés. Aplica a Telegram, mail, UI y API.

## Estrategia en dos capas (decidida 2026-10-13)

1. **Red de contención en el webhook Telegram** (táctico, barato, reversible):
   diccionario EN→ES dentro del script del mediatype Telegram. Traduce a la
   salida sin tocar triggers ni hosts. Cubre templates stock y futuros textos
   en inglés no relevados.
2. **Traducción en origen** (estratégico, planificado, NO iniciado):
   renombrar prototipos de triggers / event names / descripciones en los
   templates, versionados en este repo como fuente de verdad, importados a
   cada Zabbix. El trigger nace en español y sale bien en todos los canales.

Ambas capas se complementan; el webhook queda como red permanente.

## Estado actual (2026-10-13, solo site-a)

- Mediatype 97 `Telegram` en Zabbix site-a (198.51.100.252):
  - Mapeo de severidad ES previo (`Disaster→Crítica`, `High→Alta`, etc.).
  - Agregado `event_es`: 16 reglas regex EN→ES basadas en histórico real de
    60 días (ping, VLAN sin tráfico, link down, reinicios, memoria, VMs…).
  - PROBLEM y RECOVERY sin redundancia: el subject lleva `host + alarma` y el
    body ya NO repite `{EVENT.NAME}` (solo Severidad/Equipo/Duración/Resuelto).
- Backups en el server (`/tmp/mt97_*_20261013.*`) y locales (`/tmp/opencode/`).
- site-b (mediatype 65) y site-c: pendientes, sin tocar.

## Procedimiento futuro — traducción en origen (pendiente, no prioritario)

### Fase 1 — Relevamiento read-only (cero writes)
Por cada Zabbix (site-a, site-b, site-c):
- `media_type` Telegram: script + `media_type_message` actuales.
- Templates linkados y cantidad de hosts/triggers por template.
- Histórico `problem` 60 días: `SELECT name, COUNT(*) ... GROUP BY name`
  para rankear nombres EN por frecuencia → base del diccionario y prioridad
  de traducción.
- Entregable: inventario + lista priorizada para aprobar con el usuario.

Accesos: site-a `zabbix@198.51.100.252:14022`, site-b `198.51.100.43:6022` y
`zbx-site-b@198.51.100.38:14422` (definir cuál es el vigente), site-c
`zabbix@192.0.2.11:14022` vía VPN ipsec `site-c-vpn`.
Método: solo `SELECT` vía `ssh + docker exec <pg> psql`; tokens API solo
transient, jamás en archivos ni memoria persistente.

### Fase 2 — Traducción en repo
- Exportar templates vivos, diff contra `templates/*.yaml`.
- Traducir prototipos/descripciones al español validado con el usuario.
- Commit versionado (fuente de verdad = repo, no la UI).

### Fase 3 — Import por cliente
- Backup previo por mediatype/historial.
- Importar template, verificar recreación LLD (los triggers viejos quedan
  huérfanos hasta que expira el descubrimiento — ventana cuidada).
- Probar con alarma real; `zabbix_server -R config_cache_reload`.
- Antes: `SELECT` de verificación; después: `length/md5` + grep de marcador.

### Fase 4 — Publicación comunidad
- Publicar el set traducido en repo público y ofrecerlo a la comunidad
  hispanohablante (los templates oficiales se mantienen en inglés).

## Mantenimiento
- Al actualizar Zabbix o un template stock: re-aplicar traducción y
  re-verificar. Si aparece un texto EN nuevo en Telegram: agregar regla al
  `event_es` del webhook (una sola actualización por mediatype).
- Rollback: restaurar backup del script / re-importar template previo.

## Detalles técnicos aprendidos
- El mapeo de severidad vive en el webhook (`severity_es`, replace sobre el
  texto final ya con escape de markup) — mismo punto para `event_es`.
- Los mensajes `media_type_message` usan CRLF real (0x0D 0x0A); NO escribir
  `\`+`r` literal ni agregar `\n` extra con dollar-quoting
  (`= $tag$<contenido>$tag$` sin saltos agregados).
- `psql -c` no interpola variables `:'var'` en este entorno; usar SQL por
  stdin con dollar-quoting para updates de texto largo.
- `mediatype.update` vía API necesita token Bearer (header `Authorization`,
  no campo `auth`); sin token, update SQL directo + `config_cache_reload`.
