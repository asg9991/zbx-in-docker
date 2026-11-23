#!/usr/bin/env python3
"""Modo consulta (N5): "¿qué pasó con X?"

Resolución determinista, sin LLM:
  1. Si el texto nombra un host de Zabbix -> reporte de ese equipo
     (problemas activos + evidencia de log).
  2. Si no, busca el texto en los logs de la ventana.

Uso: python3 scripts/preguntar.py "¿qué pasó con sw-sim-09?"
     python3 scripts/preguntar.py "¿qué pasó con sw-sim-09?" --since 1440
     python3 scripts/preguntar.py "buscar LINK-3-DOWN"
"""

import json
import os
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import digest as dg  # noqa: E402


def hosts_conocidos():
    return [h["host"] for h in dg.zbx("host.get", {"output": ["host", "hostid"]})]


def main() -> int:
    args = sys.argv[1:]
    since = 120
    if "--since" in args:
        i = args.index("--since")
        since = int(args[i + 1])
        del args[i:i + 2]
    texto = " ".join(args).strip()
    if not texto:
        print("uso: preguntar.py \"¿qué pasó con <equipo>?\" [--since MIN]")
        return 1
    t = texto.lower()

    # El nombre más largo que aparece gana: "sw-sim-1" no debe robarle
    # "sw-sim-10" solo por venir antes en la lista.
    candidatos = [h for h in hosts_conocidos() if h.lower() in t]
    host = max(candidatos, key=len) if candidatos else None
    if host:
        _, clases, reglas, _ = dg.cargar_contexto(dg.SERVICIOS)
        hid = dg.zbx("host.get", {"output": ["hostid"],
                                  "filter": {"host": [host]}})[0]["hostid"]
        problemas = dg.zbx("problem.get", {"output": ["name", "severity", "clock"],
                                           "hostids": [hid], "recent": False})
        print(f"# {host}\n")
        if not problemas:
            # "¿Qué pasó?" no es "¿qué está roto ahora?": si no hay problemas
            # activos, se muestran los últimos logs del equipo igual.
            print(f"Sin problemas activos en este momento. "
                  f"Últimos logs ({since} min):\n")
            logql = clases.get("desconocido", {}).get("logql", "")
            try:
                for linea in dg.loki(logql.replace("$HOST", host), since, 5):
                    print(f"- {linea[:160]}")
            except Exception as exc:  # noqa: BLE001
                print(f"(sin logs: {exc})")
            print()
        for p in problemas:
            cid = dg.clasificar(p["name"], clases)
            regla = clases.get(cid, {})
            print(f"- Problema: {p['name']} (severidad {p['severity']})")
            print(f"  Clase: {regla.get('nombre', cid)}")
            if regla.get("accion"):
                print(f"  Acción: {regla['accion']}")
            evidencia = []
            if regla.get("logql"):
                try:
                    evidencia = dg.loki(regla["logql"].replace("$HOST", host), since, 3)
                except Exception as exc:  # noqa: BLE001
                    evidencia = [f"(sin evidencia: {exc})"]
            for linea in evidencia:
                print(f"  Evidencia: {linea[:150]}")
            print()
        return 0

    # sin host: búsqueda textual en logs
    q = '{job="syslog"} |= ' + json.dumps(texto.split("buscar ")[-1])
    print(f"# búsqueda: {texto}\n")
    try:
        lineas = dg.loki(q, 1440, 10)
    except Exception as exc:  # noqa: BLE001
        print(f"error consultando Loki: {exc}")
        return 1
    if not lineas:
        print("Sin coincidencias en las últimas 24 h.")
        return 0
    for linea in lineas:
        print(f"- {linea[:160]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
