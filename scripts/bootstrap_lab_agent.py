#!/usr/bin/env python3
"""Bootstrap del agente para el propio lab del NOC Agent.

La instalacion limpia de Zabbix trae el host "Zabbix server" con interfaz
agent 127.0.0.1:10050. Desde el contenedor del server ese IP es el mismo
contenedor (donde no hay agente), por lo que la disponibilidad queda en
rojo y el log spamea "connection refused".

Este script repunta esa interfaz al DNS "zabbix-agent" (el servicio del
compose) y queda en verde. Es idempotente: si ya apunta al DNS, no toca nada.

Uso (sin dependencias externas, solo Python 3 stdlib):

  export ZABBIX_URL=http://127.0.0.1/api_jsonrpc.php   # default
  export ZABBIX_USER=Admin                             # default
  export ZABBIX_PASSWORD='tu-password'
  python3 scripts/bootstrap_lab_agent.py

Requisito previo: docker compose up -d zabbix-agent
"""

import json
import os
import sys
import urllib.request

URL = os.getenv("ZABBIX_URL", "http://127.0.0.1/api_jsonrpc.php")
USER = os.getenv("ZABBIX_USER", "Admin")
PASSWORD = os.getenv("ZABBIX_PASSWORD", "")

HOST = "Zabbix server"
AGENT_DNS = "zabbix-agent"
AGENT_PORT = "10050"

_request_id = 0


def api(token: str | None, method: str, params: dict):
    """Ejecuta una llamada JSON-RPC y devuelve el result o aborta con error.

    Zabbix 7.x ya no acepta el campo "auth" en el body: el token viaja
    en el header Authorization: Bearer.
    """
    global _request_id
    _request_id += 1
    payload = {"jsonrpc": "2.0", "method": method, "params": params,
               "id": _request_id}
    headers = {"Content-Type": "application/json-rpc"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = urllib.request.Request(
        URL, data=json.dumps(payload).encode(), headers=headers)
    with urllib.request.urlopen(request, timeout=30) as response:
        body = json.load(response)
    if "error" in body:
        sys.exit(f"ERROR en {method}: {body['error']}")
    return body["result"]


def main() -> int:
    if not PASSWORD:
        sys.exit("ERROR: exporta ZABBIX_PASSWORD antes de correr el bootstrap.")

    print(f"* Login en {URL} como {USER}...")
    token = api(None, "user.login",
                {"username": USER, "password": PASSWORD})

    hosts = api(token, "host.get", {
        "filter": {"host": [HOST]},
        "selectInterfaces": ["interfaceid", "type", "useip", "ip", "dns",
                             "port"],
    })
    if not hosts:
        sys.exit(f"ERROR: no se encontro el host '{HOST}'.")
    agent_ifaces = [i for i in hosts[0]["interfaces"] if i["type"] == "1"]
    if not agent_ifaces:
        sys.exit(f"ERROR: el host '{HOST}' no tiene interfaz agent.")

    iface = agent_ifaces[0]
    if iface["dns"] == AGENT_DNS and iface["useip"] == "0":
        print(f"* La interfaz agent de '{HOST}' ya apunta a "
              f"{AGENT_DNS}:{AGENT_PORT}. Nada que hacer.")
    else:
        print(f"* Repunteando interfaz agent de '{HOST}': "
              f"{iface['ip']} -> {AGENT_DNS}:{AGENT_PORT}...")
        api(token, "host.update", {
            "hostid": hosts[0]["hostid"],
            "interfaces": [{
                "interfaceid": iface["interfaceid"],
                "useip": 0,
                "dns": AGENT_DNS,
                "port": AGENT_PORT,
            }],
        })
        print("  listo.")

    api(token, "user.logout", [])
    print("\nBootstrap OK. En ~1 minuto la disponibilidad agent deberia "
          "quedar en verde y el log del server deja de quejarse.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
