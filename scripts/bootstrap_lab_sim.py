#!/usr/bin/env python3
"""Bootstrap del laboratorio simulado del NOC Agent.

Crea (de forma idempotente) todo lo necesario para Fase 1:

  1. Importa el template "Lab Simulado" (templates/template_lab_simulado.yaml)
  2. Crea el host group "Lab/Simulados"
  3. Crea los 4 hosts simulados linkeando el template

Si algo ya existe, lo deja como esta (no toca ni recrea nada).

Uso (sin dependencias externas, solo Python 3 stdlib):

  export ZABBIX_URL=http://127.0.0.1/api_jsonrpc.php   # default
  export ZABBIX_USER=Admin                             # default
  export ZABBIX_PASSWORD='tu-password'
  python3 scripts/bootstrap_lab_sim.py
"""

import json
import os
import sys
import urllib.request

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEMPLATE_FILE = os.path.join(REPO_ROOT, "templates", "template_lab_simulado.yaml")

URL = os.getenv("ZABBIX_URL", "http://127.0.0.1/api_jsonrpc.php")
USER = os.getenv("ZABBIX_USER", "Admin")
PASSWORD = os.getenv("ZABBIX_PASSWORD", "")

HOSTGROUP = "Lab/Simulados"
SIM_HOSTS = ["olt-sim-01", "router-sim-02", "server-sim-03", "ap-sim-04"]

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

    # 1. Template -----------------------------------------------------------
    print("* Importando template 'Lab Simulado'...")
    with open(TEMPLATE_FILE, encoding="utf-8") as handle:
        source = handle.read()
    api(token, "configuration.import", {
        "format": "yaml",
        "source": source,
        "rules": {
            "templates": {"createMissing": True, "updateExisting": True},
            "items": {"createMissing": True, "updateExisting": True},
            "triggers": {"createMissing": True, "updateExisting": True},
            "valueMaps": {"createMissing": True, "updateExisting": True},
        },
    })

    # 2. Host group ---------------------------------------------------------
    print(f"* Asegurando host group '{HOSTGROUP}'...")
    found = api(token, "hostgroup.get", {"filter": {"name": [HOSTGROUP]}})
    if found:
        groupid = found[0]["groupid"]
        print(f"  ya existe (id {groupid})")
    else:
        created = api(token, "hostgroup.create", {"name": HOSTGROUP})
        groupid = created["groupids"][0]
        print(f"  creado (id {groupid})")

    # 3. Hosts --------------------------------------------------------------
    template = api(token, "template.get",
                   {"filter": {"host": ["Lab Simulado"]}})
    if not template:
        sys.exit("ERROR: el template no quedó disponible tras el import.")
    templateid = template[0]["templateid"]

    for hostname in SIM_HOSTS:
        print(f"* Asegurando host '{hostname}'...")
        found = api(token, "host.get", {"filter": {"host": [hostname]}})
        if found:
            print("  ya existe")
            continue
        api(token, "host.create", {
            "host": hostname,
            "groups": [{"groupid": groupid}],
            "templates": [{"templateid": templateid}],
        })
        print("  creado")

    api(token, "user.logout", [])
    print("\nBootstrap OK. Levanta el simulador con:")
    print("  docker compose --profile lab up -d --build")
    return 0


if __name__ == "__main__":
    sys.exit(main())
