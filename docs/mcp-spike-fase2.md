# Spike Fase 2 — Hub MCP (lab, read-only)

Fecha: 2026-09-08. Alcance: lab local. Estado: validado, sin commitear.

## 1. Objetivo

Validar el hub MCP `initMAX/zabbix-mcp-server v1.36.1` como capa de
lectura hacia Zabbix: health, autenticación bearer, lista de tools
podada, dos lecturas reales y un intento de escritura bloqueado por
`read_only`.

## 2. Topología (texto)

```
host lab (127.0.0.1:8080)
  └─ zabbix-mcp (lab/zabbix-mcp-server:1.36.1, build local prístino, sin modificar)
       ├─ red backend (interna) → zabbix-server / postgres
       ├─ red frontend → zabbix-web / nginx
       └─ config: docker/zabbix-mcp-config.toml (ignorado por git, mount ro)
```

Notas de configuración verificada:

- Servicio `zabbix-mcp` en compose `zbx-in-docker`.
- Imagen `lab/zabbix-mcp-server:1.36.1`, build local prístino.
- Publish `127.0.0.1:8080`, sin exposición externa.
- Admin portal apagado.
- Token MCP `lab_ro`, modo `read_only`, scopes `monitoring` + `extensions`.
- API token de Zabbix tipo lab, expiración 7 días.

## 3. Cómo levantar (sin secretos)

```bash
# desde la raíz del repo
docker compose -f docker/docker-compose.yml --project-name zbx-in-docker up -d zabbix-mcp

docker compose --project-name zbx-in-docker ps zabbix-mcp
curl -s http://127.0.0.1:8080/health

# el bearer vive fuera del repo, con permisos 600
export MCP_BEARER="$(cat /tmp/.mcp_bearer)"
curl -s http://127.0.0.1:8080/mcp \
  -H "Authorization: Bearer $MCP_BEARER" \
  -H 'Content-Type: application/json' \
  -H 'Accept: application/json, text/event-stream' \
  -d '{"jsonrpc":"2.0","id":1,"method":"ping"}'
```

Config con secretos: `docker/zabbix-mcp-config.toml` está ignorado por
git y no se versiona. No copiar valores a docs, issues ni commits.

## 4. Transcript curl redactado

Valores sensibles reemplazados por `$MCP_BEARER` y `$SESSION_ID`.
Respuestas resumidas a lo relevante.

### 4.1 Health

```bash
curl -s http://127.0.0.1:8080/health
```

```json
{"status":"ok"}
```

### 4.2 /mcp sin bearer → 401

```bash
curl -s -o /dev/null -w '%{http_code}\n' http://127.0.0.1:8080/mcp \
  -H 'Content-Type: application/json' \
  -H 'Accept: application/json, text/event-stream' \
  -d '{"jsonrpc":"2.0","id":1,"method":"ping"}'
```

```text
401
```

### 4.3 initialize (sesión stateful)

Requiere el header dual `Accept`. Sin él, el servidor responde `406`.

```bash
curl -s -D - -o /tmp/mcp_init_body.json http://127.0.0.1:8080/mcp \
  -H "Authorization: Bearer $MCP_BEARER" \
  -H 'Content-Type: application/json' \
  -H 'Accept: application/json, text/event-stream' \
  -d '{
    "jsonrpc": "2.0",
    "id": 1,
    "method": "initialize",
    "params": {
      "protocolVersion": "2024-11-05",
      "capabilities": {},
      "clientInfo": {"name": "spike-lab", "version": "0.1"}
    }
  }'
```

Respuesta: `200 OK` con header `Mcp-Session-Id: $SESSION_ID`.
Guardar el id para el resto de las llamadas:

```bash
export SESSION_ID="<valor del header Mcp-Session-Id>"
```

Aviso de sesión: toda llamada posterior debe incluir
`Mcp-Session-Id: $SESSION_ID`.

### 4.4 tools/list (podada)

```bash
curl -s http://127.0.0.1:8080/mcp \
  -H "Authorization: Bearer $MCP_BEARER" \
  -H "Mcp-Session-Id: $SESSION_ID" \
  -H 'Content-Type: application/json' \
  -H 'Accept: application/json, text/event-stream' \
  -d '{"jsonrpc":"2.0","id":2,"method":"tools/list","params":{}}' \
  | head -c 512
```

Resultado verificado: 35 tools, ~133 KB de respuesta, frente a ~237
tools del servidor full.

### 4.5 tools/call: problem_active_get

```bash
curl -s http://127.0.0.1:8080/mcp \
  -H "Authorization: Bearer $MCP_BEARER" \
  -H "Mcp-Session-Id: $SESSION_ID" \
  -H 'Content-Type: application/json' \
  -H 'Accept: application/json, text/event-stream' \
  -d '{
    "jsonrpc": "2.0",
    "id": 3,
    "method": "tools/call",
    "params": {
      "name": "problem_active_get",
      "arguments": {"params": {}}
    }
  }'
```

Resultado: OK. Devuelve los problemas activos del lab.
Nota el wrapper `params` dentro de `arguments`: es obligatorio.

### 4.6 tools/call: host_status_get

```bash
curl -s http://127.0.0.1:8080/mcp \
  -H "Authorization: Bearer $MCP_BEARER" \
  -H "Mcp-Session-Id: $SESSION_ID" \
  -H 'Content-Type: application/json' \
  -H 'Accept: application/json, text/event-stream' \
  -d '{
    "jsonrpc": "2.0",
    "id": 4,
    "method": "tools/call",
    "params": {
      "name": "host_status_get",
      "arguments": {"params": {"host": "<host del lab>"}}
    }
  }'
```

Resultado: OK. La tool exige `host` o `host_id`; sin ese campo falla
por validación.

### 4.7 Bloqueo de escritura: host_create denegado

```bash
curl -s http://127.0.0.1:8080/mcp \
  -H "Authorization: Bearer $MCP_BEARER" \
  -H "Mcp-Session-Id: $SESSION_ID" \
  -H 'Content-Type: application/json' \
  -H 'Accept: application/json, text/event-stream' \
  -d '{
    "jsonrpc": "2.0",
    "id": 5,
    "method": "tools/call",
    "params": {
      "name": "host_create",
      "arguments": {"params": {"host": "<nombre de prueba no creado>"}}
    }
  }'
```

Respuesta (error esperado, texto exacto):

```text
Token 'spike lab read-only' is read-only. Write operations are not allowed.
```

Verificación posterior con `host_get`: vacío, nada fue creado.

## 5. Hallazgos

- `GET /health` responde `{"status":"ok"}` sin auth; `/mcp` sin bearer
  responde `401`.
- Podado efectivo: 35 tools (~133 KB) vs ~237 full.
- Lecturas validadas: `problem_active_get` y `host_status_get`.
- `read_only` funciona a nivel gate: bloquea `host_create` con el
  mensaje citado y no crea objetos.
- Peculiaridades del protocolo:
  - Header `Accept: application/json, text/event-stream` obligatorio
    (sin él, `406`).
  - Sesión stateful: tras `initialize`, enviar
    `Mcp-Session-Id` en cada request.
  - `tools/call` requiere wrapper `params` dentro de `arguments`.

## 6. Costos

- Imagen local pineada `1.36.1`; sin pulls en cada arranque.
- Respuesta de `tools/list` podada (~133 KB): menor contexto para el
  futuro orquestador.
- Sin costo de infraestructura adicional: reusa el compose existente.

## 7. Riesgos y notas

- Config `docker/zabbix-mcp-config.toml` con permisos abiertos (644)
  solo válido en lab. Nunca commitear ni replicar en prod.
- Bearer en `/tmp/.mcp_bearer` (600), fuera del repo. No imprimir ni
  persistir en logs.
- GHCR no permite pull anónimo: se usa build local pineado
  `lab/zabbix-mcp-server:1.36.1`.
- Las tools ocultas por configuración igual llegan al gate: no confiar
  solo en ocultar, el enforcement real es el modo `read_only` más los
  scopes `monitoring` + `extensions`.
- API token de lab con expiración de 7 días: requiere rotación si el
  spike se extiende.

## 8. Próximos pasos (Fase 3)

- Token por tenant en el orquestador (abandonar el token único del spike).
- VM dedicada para el hub MCP fuera del compose de lab.
- TLS frontal (terminar en reverse proxy, no en el MCP directo).
- Actualizar `docs/ROADMAP.md` Fase 6 / Fase 2 cuando se apruebe este spike.

## 9. Cierre (2026-09-12)

- Rotación: bearer + API token de Zabbix rotados, vigencia hasta
  2026-10-12; token anterior revocado. Sin valores en repo.
- Config `docker/zabbix-mcp-config.toml` con permisos 600 + ACL de
  lectura para uid 999; sigue ignorado por git, mount ro.
- Segundo token `lab_ro2` validado: podado a 1 tool (frente a 35 de
  `lab_ro`).
- Reportes PDF OK con link nativo del frontend; falta `public_url`
  para servir http correctamente.
- Graph pendiente: requiere `frontend_username`/`password` en config.

Spike Fase 2 cerrado; hub MCP read-only queda como base de lab.
