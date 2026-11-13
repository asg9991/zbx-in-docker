# Operación del hub MCP (zabbix-mcp-container)

Runbook para operadores de cualquier instalación (lab o cliente). Los valores
del sitio (URLs, IDs, usuarios, tokens) viven en el repo privado del cliente;
acá solo hay procedimiento genérico. El servicio corre como `zabbix-mcp`
(perfil `mcp` de `docker/docker-compose.yml`), lee `./zabbix-mcp-config.toml`
(montado read-only) y habla con Zabbix vía `api_token`. Corre en el host, en
el orden indicado. Tiempos: ~5 min.

## Criterio de identidad

Tres capas — no confundirlas:

1. **Infraestructura (hub → Zabbix)**: el `api_token` del toml. La identidad
   es el archivo: fuera de git, y legible **solo** por el dueño y el uid del
   servicio (ver §Permisos del toml). El toml define además los consumidores
   del hub por `token_hash` (hash, nunca el valor) + `scopes`.
2. **Aplicación (consumidor → hub)**: `MCP_BEARER` por consumidor. En prod el
   valor vive en un archivo `600` referenciado por `MCP_BEARER_FILE`
   (`$XDG_RUNTIME_DIR/noc-agent/mcp_bearer`), jamás en `/tmp` ni en git.
3. **Operación auditada (quién pidió qué)**: `actor`/`channel` tomados del
   canal autenticado, nunca del payload del mensaje (spoofeable). La identidad
   de sistema se audita por kernel (`pwd.getpwuid`), no por `$USER`.

Cadena completa de identidad y gobernanza: `noc-agent/docs/runbook-operativo.md` §4.

Notas de la API de tokens de Zabbix (7.x):

- `token.create` crea el **registro**; el valor se obtiene aparte con
  `token.generate` y se muestra **una sola vez**.
- El almacenamiento en Zabbix es `token_hash`: el valor original no se puede
  recuperar después — si se pierde, hay que rotar.
- `token.delete` da de baja (equivale a Revoke/Delete de la UI).

## Permisos del toml (leer antes de tocar nada)

El contenedor corre con su propio uid (descubrirlo, no asumirlo):

```bash
docker run --rm --entrypoint id <imagen-del-hub>
# Ejemplo lab: uid=999(zabbix-mcp) — en el HOST ese uid puede tener otro
# nombre (ej. dnsmasq); lo que importa es el número.
```

Estado correcto del archivo: `600` + **ACL de lectura para ese uid** (o
`640` + grupo del servicio):

```bash
setfacl -m u:<uid-servicio>:r-- ./zabbix-mcp-config.toml
getfacl ./zabbix-mcp-config.toml | grep -E 'user:|mask'   # ACL + mask r--
```

- Un `600` sin esa ACL deja al hub **sin config al reiniciar**
  (`Permission denied` → crash loop). El fallo es latente: el proceso no
  relee la config, así que solo aparece al recrear el contenedor.
- **Nunca** remover esa ACL por "huérfana": el nombre con que se muestra es
  el del host, no el del contenedor.

## Endpoint de la API de Zabbix

```bash
API=http://127.0.0.1/api_jsonrpc.php     # lab: zbx-nginx expone :80
# API=https://127.0.0.1/api_jsonrpc.php  # prod: vhost en :443 (como checklist-servicio.md)
```

Los comandos de este runbook usan `$API`; definirlo una vez por operación.

## 1. Alta de token

```bash
TOML=./docker/zabbix-mcp-config.toml
TOKEN=$(grep -m1 'api_token' "$TOML" | sed 's/.*= *"\([^"]*\)".*/\1/')

# a) crear el registro (nombre auditable: hub-<entorno>[-<motivo>]-<fecha>)
curl -sk $API -H 'Content-Type: application/json-rpc' \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"jsonrpc":"2.0","method":"token.create","params":{"name":"hub-lab-YYYYMMDD"},"id":1}'
# Esperado: {"result":{"tokenids":["N"]},...}

# b) generar el valor (SE MUESTRA UNA SOLA VEZ — copiarlo al toml sin imprimirlo)
curl -sk $API -H 'Content-Type: application/json-rpc' \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"jsonrpc":"2.0","method":"token.generate","params":["N"],"id":2}'
# Esperado: {"result":[{"tokenid":"N","token":"<secreto>"}],...}
```

3. Editar `api_token = "<secreto>"` en el toml (editor, nunca `echo` — el
   secreto no debe caer en historial ni en logs).
4. Recrear el servicio (conserva proyecto y perfil):
   `docker compose -p zbx-in-docker -f docker/docker-compose.yml --profile mcp up -d --force-recreate zabbix-mcp`
5. Smoke test (§Diagnóstico). ¿Verde? Token dado de alta.

## 2. Baja de token

```bash
curl -sk $API -H 'Content-Type: application/json-rpc' \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"jsonrpc":"2.0","method":"token.delete","params":["viejo_id"],"id":3}'
# Esperado: {"result":{"tokenids":["viejo_id"]},...}
```

(UI equivalente: User settings → API tokens → Delete/Revoke.)

- Borrar el valor del toml **sin** hacer `token.delete` deja la credencial
  viva en Zabbix: la baja real es el `token.delete`.
- Smoke test post-baja confirma que nada seguía dependiendo del token borrado.

## 3. Rotación (sin ventana de ciego)

El token viejo se revoca **solo después** de validar el nuevo. Orden exacto:

1. Alta del token nuevo (§1 a-b) **sin tocar** el viejo.
2. Swap del toml con el valor nuevo + recreate del contenedor.
3. Smoke test. ¿Rojo? **ROLLBACK**: restaurar el valor anterior en el toml,
   recreate, smoke, y abortar la rotación. No continuar.
4. ¿Verde? Recién ahora `token.delete` del token viejo (§2).
5. Smoke test final + inventario (`token.get`) confirmando el estado esperado.

Tiempo: ~5 min. Nunca invertir los pasos 3 y 4.

## 4. Diagnóstico

```bash
# permisos del secreto (esperado: dueño + uid del servicio, sin "other")
stat -c '%a %U %G' ./docker/zabbix-mcp-config.toml
getfacl ./docker/zabbix-mcp-config.toml | grep -E 'user:|mask'

# estado del servicio
docker compose --profile mcp ps zabbix-mcp
docker logs zabbix-mcp --tail 20   # sin errores de auth/config

# smoke test: el api_token del toml sigue resolviendo problemas
TOML=./docker/zabbix-mcp-config.toml
TOKEN=$(grep -m1 'api_token' "$TOML" | sed 's/.*= *"\([^"]*\)".*/\1/')
curl -sk $API -H 'Content-Type: application/json-rpc' \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"jsonrpc":"2.0","method":"problem.get","params":{"output":["eventid"],"limit":1},"id":1}'
# Esperado: {"result":[...]} — [] también es verde; "error" es rojo.
```

| Síntoma | Causa típica | Acción |
| --- | --- | --- |
| 401 / `Not authorized` | token revocado, rotado o mal copiado | rehacer swap desde el valor válido o rotar (§3) |
| `Permission denied` al leer `config.toml` | toml `600` sin ACL para el uid del servicio (aparece solo al reiniciar) | `setfacl -m u:<uid-servicio>:r--` y recrear (§Permisos del toml) |
| `error` de permisos en `token.*` | el usuario del token no es dueño o no tiene *Manage API tokens* | operar con su usuario en la UI, o usar un token con ese permiso |
| timeout | alcance/red hacia `api_jsonrpc.php` | revisar `url` del toml y conectividad |
| hub no arranca | toml mal formateado o montaje | `docker logs zabbix-mcp`; validar sintaxis TOML |

## 5. Checklist de operación (ejecutable)

Pre-alta (inventario):

- [ ] `token.get` muestra los tokens vigentes (guardar `tokenid`/`name`/`status`)
- [ ] toml legible por el uid del servicio (ACL/grupo), no solo `600`
- [ ] nombre elegido sigue `hub-<entorno>[-<motivo>]-<fecha>`

Rotación (siempre en este orden):

- [ ] `token.create` → `tokenid` nuevo
- [ ] `token.generate` → valor copiado al toml sin imprimirlo
- [ ] recreate del contenedor
- [ ] smoke test con el token nuevo → verde
- [ ] (si rojo) rollback ejecutado y abortado
- [ ] `token.delete` del token viejo
- [ ] smoke test final → verde
- [ ] inventario post: `token.get` confirma el estado esperado (el viejo ya no existe)

Auditoría:

- [ ] el valor no aparece en historial de git, logs, ni chat

---

Ejecutado en lab (2026-11-12): rotación completa con `token.create`/`generate`
(tokenid 4, `hub-lab-rot-20261112`) → swap → smoke verde → `token.delete`
del token viejo (tokenid 3, `lab_hub`) → smoke final verde → inventario post
limpio. El drill detectó y corrigió el modo de fallo de §Permisos del toml.
Rollback no ejercitado (sin rojo; sus pasos son los mecanismos ya probados).
