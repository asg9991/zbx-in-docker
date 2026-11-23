# Contrato del digest (fase N)

El digest es la salida que consume el agente (o un humano) para saber **qué
pasa, a quién afecta y con qué evidencia**. Hoy lo genera
`scripts/digest.py`; mañana lo puede generar el noc-agent con el mismo formato.

## Comando

```bash
python3 scripts/digest.py                     # markdown legible
python3 scripts/digest.py --json              # contrato para el agente
python3 scripts/digest.py --check             # valida el contexto del sitio
python3 scripts/digest.py --servicios X.yml --since 60
```

Es **solo lectura**: consulta Zabbix y Loki (a través del proxy de Grafana) y
no escribe nada.

## Estructura (JSON)

```json
{
  "site": "lab",
  "generado": "2026-11-22T18:45:09+00:00",
  "servicios": [
    {
      "nombre": "Red de acceso",
      "criticidad": "alta",
      "estado": "CRITICO",
      "problemas": 1,
      "hallazgos": [
        {
          "host": "sw-sim-09",
          "problema": "Link caido: sw-sim-09",
          "severidad": 4,
          "clase": "enlace",
          "clase_nombre": "Enlace caído o inestable",
          "accion": "Revisar energía del equipo y el siguiente salto...",
          "evidencia": ["sw-sim-09 | LINK-3-DOWN ..."]
        }
      ]
    }
  ],
  "sin_servicio": [
    { "problema": "...", "severidad": 2, "clase": "desconocido" }
  ]
}
```

## Semántica

| Campo | Significado |
| --- | --- |
| `estado` | `OK` / `DEGRADADO` / `CRITICO`, calculado con las reglas por clase |
| `clase` | id del catálogo (`clases.yaml`) |
| `severidad` | la de Zabbix (0–5), sin reinterpretar |
| `accion` | sugerencia para el humano; **no** es un comando |
| `evidencia` | hasta 3 líneas de log del **mismo equipo**, en la ventana pedida, ordenadas por hora y sin duplicados |
| `sin_servicio` | problemas que no pertenecen a ningún servicio declarado |

## Garantías

1. **Trazable**: cada hallazgo tiene host, problema y evidencia del mismo host.
2. **Sin acciones**: el digest no ackea, no silencia ni ejecuta nada.
3. **Un dueño de la verdad**: severidad y estado salen de Zabbix + reglas; el
   agente no inventa umbrales.
4. **Contexto validado**: `--check` falla si un servicio no declara hosts, si
   una clase referenciada no existe o si una clase no tiene `logql`. La
   existencia de cada host en Zabbix se verifica al correr el digest: un host
   declarado que no existe se reporta, no se ignora en silencio.

## Límites conocidos

- La evidencia son líneas de log, no un análisis. Interpretar es del agente.
- `sin_servicio` no está priorizado: los servicios declarados mandan.
- La ventana (`--since`) es fija por corrida; no hay deduplicación entre
  corridas.

## Envío (N4)

```bash
python3 scripts/notify_digest.py --dry-run      # imprime el payload
python3 scripts/notify_digest.py --solo-alertas # no envía si todo está OK
```

Destinos por variable de entorno (nunca en el repo):

| Variable | Destino |
| --- | --- |
| `DIGEST_WEBHOOK_URL` + `DIGEST_FORMATO=discord|slack` | webhook |
| `TELEGRAM_BOT_TOKEN` + `TELEGRAM_CHAT_ID` | Telegram |

Sin destinatario configurado imprime y no falla: es seguro correrlo en el lab.

## Consulta (N5)

```bash
python3 scripts/preguntar.py "¿qué pasó con server-sim-03?"
python3 scripts/preguntar.py "¿qué pasó con server-sim-03?" --since 1440
python3 scripts/preguntar.py "buscar LINK-3-DOWN"
```

Resolución determinista: si el texto nombra un host, devuelve sus problemas con
clase, acción y evidencia; si no, busca el texto en los logs de 24 h. Es el
mismo camino que usará el agente, sin LLM todavía.
