#!/usr/bin/env python3
"""Genera el dashboard "Estado de servicios" desde servicios.yml.

Un panel por servicio con el estado derivado de los problemas de sus hosts:
0 = sin problemas, 1 = degradado (severidad >= Media), 2 = critico (>= Alta).

Uso: python3 scripts/gen_servicios.py [servicios.yml] [--resolve]
"""

import json
import os
import sys
import urllib.request
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts/observability"))
import clases as cat  # noqa: E402
import queries  # noqa: E402

API_URL = os.getenv("ZBX_API_URL", "http://127.0.0.1/api_jsonrpc.php")
CLASES = ROOT / "docker/observability/clases/clases.yaml"
SALIDA = ROOT / "docker/observability/grafana/dashboards/Cliente/servicios.json"

NAV = [
    {"type": "dashboards", "title": "Estado General", "tags": ["nav", "cliente"],
     "asDropdown": True, "icon": "user", "includeVars": False, "keepTime": True,
     "targetBlank": False},
    {"type": "dashboards", "title": "Técnico", "tags": ["nav", "tecnico"],
     "asDropdown": True, "icon": "wrench", "includeVars": False, "keepTime": True,
     "targetBlank": False},
    {"type": "dashboards", "title": "Mapas", "tags": ["nav", "mapa"],
     "asDropdown": True, "icon": "sitemap", "includeVars": False, "keepTime": True,
     "targetBlank": False},
]


def token() -> str:
    tok = os.getenv("ZBX_API_TOKEN", "")
    if tok:
        return tok
    env = ROOT / "docker/.env"
    if env.exists():
        for line in env.read_text().splitlines():
            if line.startswith("ZBX_API_TOKEN="):
                return line.split("=", 1)[1].strip()
    return ""


def resolver(nombres):
    body = {"jsonrpc": "2.0", "method": "host.get",
            "params": {"output": ["hostid", "host"],
                       "filter": {"host": list(nombres)}}, "id": 1}
    req = urllib.request.Request(API_URL, data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json-rpc",
                 "Authorization": f"Bearer {token()}"})
    with urllib.request.urlopen(req, timeout=20) as r:
        data = json.loads(r.read())
    if "error" in data:
        sys.exit(f"ERROR resolviendo hosts: {data['error']}")
    return {h["host"]: h["hostid"] for h in data["result"]}


def cargar_reglas():
    """{clase: {patrones, critico, degradado}} desde el catálogo único."""
    _, clases, reglas, _ = cat.cargar(CLASES)
    out = {}
    for cid, clase in clases.items():
        if cid == "desconocido" or cid not in reglas:
            continue
        if not clase["patrones"]:
            continue
        out[cid] = {
            "patrones": clase["patrones"],
            "critico": int(reglas[cid].get("critico", 5)),
            "degradado": int(reglas[cid].get("degradado", 3)),
        }
    return out


def condicion(sev: int, patrones) -> str:
    """Expresión JSONata: problemas con severidad >= sev y nombre que matchea."""
    return (f"$count(result[$number(severity) >= {sev} and "
            f"{cat.jsonata_nombre_en(patrones)}])")


def raiz_estado(idx: int, reglas_servicio: dict, patrones_conocidos,
                regla_desconocido: dict) -> str:
    """Estado del servicio: reglas por clase + desconocidos de severidad Alta+.

    Un problema que no matchea ninguna clase no puede dejar el servicio en
    verde si su severidad es Alta o superior. Los avisos desconocidos no
    mueven el semáforo (control de ruido), igual que en `digest.py`.
    """
    ramas_critico = [condicion(r["critico"], r["patrones"])
                     for r in reglas_servicio.values()]
    ramas_degradado = [condicion(r["degradado"], r["patrones"])
                       for r in reglas_servicio.values()]
    crit = " or ".join(f"{c} > 0" for c in ramas_critico)
    degr = " or ".join(f"{d} > 0" for d in ramas_degradado) or "false"

    sev_desc = int(regla_desconocido["critico"])
    altos = f"$count(result[$number(severity) >= {sev_desc}])"
    altos_conocidos = condicion(sev_desc, patrones_conocidos)
    desconocido_alto = f"{altos} > {altos_conocidos}"
    crit = f"({crit}) or {desconocido_alto}" if crit else desconocido_alto

    return (f'$map([1], function($x){{ {{"e_{idx}": {crit} ? 2 : ({degr} ? 1 : 0), '
            f'"n_{idx}": $string($count(result)) & " problemas"}} }})')


def estado_target(hostids, idx: int, reglas: dict, patrones_conocidos,
                  regla_desconocido: dict) -> dict:
    t = queries.target("problemas_host")
    body = {"jsonrpc": "2.0", "method": "problem.get", "params": {
        "output": ["eventid", "name", "severity"],
        "hostids": list(hostids), "recent": False, "limit": 200}, "id": 1}
    t.update({
        "refId": f"s{idx}",
        "root_selector": raiz_estado(idx, reglas, patrones_conocidos,
                                     regla_desconocido),
        "url_options": {"method": "POST", "data": json.dumps(body),
                        "headers": [{"key": "Content-Type", "value": "application/json-rpc"}]},
        "columns": [
            {"selector": f"e_{idx}", "text": f"e_{idx}", "type": "number"},
            {"selector": f"n_{idx}", "text": f"n_{idx}", "type": "string"},
        ],
    })
    return t


def main() -> int:
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    resolve = "--resolve" in sys.argv
    src = Path(args[0]) if args else \
        ROOT / "docker/observability/clases/servicios-lab.yml"
    cfg = yaml.safe_load(src.read_text())
    servicios = cfg["servicios"]

    if resolve:
        faltan = {h for s in servicios for h in s.get("hosts", [])}
        ids = resolver(faltan)
        for s in servicios:
            s["hostids"] = [ids.get(h, "") for h in s.get("hosts", [])]
            if any(not i for i in s["hostids"]):
                sys.exit(f"ERROR: servicio {s['nombre']} con host inexistente")
    elif not all(s.get("hostids") for s in servicios):
        sys.exit("ERROR: faltan hostids; usá --resolve")

    base = cargar_reglas()
    _, _, _, regla_desconocido = cat.cargar(CLASES)
    # Union de patrones de las clases CON regla: una clase sin regla se trata
    # como desconocida, igual que en digest.py.
    patrones_conocidos = [p for r in base.values() for p in r["patrones"]]
    paneles, estados, overrides = [], [], []
    for i, s in enumerate(servicios):
        reglas = {}
        for cid, r in base.items():
            override = (s.get("reglas") or {}).get(cid)
            reglas[cid] = {"patrones": r["patrones"],
                           "critico": int(override["critico"]) if override else r["critico"],
                           "degradado": int(override["degradado"]) if override else r["degradado"]}
        estados.append(reglas)
        paneles.append({
            "type": "stat", "title": s["nombre"], "id": i + 1,
            "datasource": {"type": "yesoreyeram-infinity-datasource", "uid": "zabbix-api"},
            "gridPos": {"h": 4, "w": 8, "x": (i % 3) * 8, "y": (i // 3) * 4},
            "targets": [estado_target(s["hostids"], i, reglas,
                                      patrones_conocidos, regla_desconocido)],
            "options": {"reduceOptions": {"calcs": ["lastNotNull"], "fields": f"e_{i}",
                                          "values": False},
                        "colorMode": "background", "graphMode": "none",
                        "justifyMode": "center", "orientation": "auto",
                        "textMode": "auto", "wideLayout": True},
            "fieldConfig": {"defaults": {
                "unit": "short", "noValue": "Sin datos",
                "mappings": [
                    {"type": "value", "options": {"0": {"text": "OK", "color": "semi-dark-green", "index": 0}}},
                    {"type": "value", "options": {"1": {"text": "Degradado", "color": "semi-dark-orange", "index": 1}}},
                    {"type": "value", "options": {"2": {"text": "Crítico", "color": "semi-dark-red", "index": 2}}}],
                "thresholds": {"mode": "absolute", "steps": [{"color": "text", "value": None}]}},
                "overrides": [{"matcher": {"id": "byName", "options": f"n_{i}"},
                               "properties": [{"id": "custom.hidden", "value": True}]}]},
        })

    detalle = queries.problemas_de([h for s in servicios for h in s["hostids"]])
    paneles.append({
        "type": "table", "title": "Problemas de los servicios críticos", "id": 90,
        "datasource": {"type": "yesoreyeram-infinity-datasource", "uid": "zabbix-api"},
        "gridPos": {"h": 9, "w": 24, "x": 0, "y": (len(servicios) + 2) // 3 * 4},
        "targets": [detalle],
        "options": {"cellHeight": "sm", "showHeader": True,
                    "footer": {"countRows": True, "fields": "", "reducer": ["count"], "show": True},
                    "sortBy": [{"desc": True, "displayName": "Gravedad"}]},
        "fieldConfig": {"defaults": {
            "custom": {"align": "auto", "cellOptions": {"type": "auto"}, "inspect": False},
            "mappings": [], "thresholds": {"mode": "absolute", "steps": [{"color": "green", "value": None}]}},
            "overrides": [
                {"matcher": {"id": "byName", "options": "Gravedad"}, "properties": [
                    {"id": "mappings", "value": [
                        {"type": "value", "options": {"2": {"text": "Aviso", "color": "semi-dark-yellow", "index": 0}}},
                        {"type": "value", "options": {"3": {"text": "Media", "color": "semi-dark-orange", "index": 1}}},
                        {"type": "value", "options": {"4": {"text": "Alta", "color": "semi-dark-red", "index": 2}}},
                        {"type": "value", "options": {"5": {"text": "Desastre", "color": "dark-red", "index": 3}}}]},
                    {"id": "custom.cellOptions", "value": {"type": "color-background"}},
                    {"id": "custom.width", "value": 140}]}]},
    })

    dash = {
        "annotations": {"list": []}, "editable": False, "fiscalYearStartMonth": 0,
        "graphTooltip": 1, "id": None, "links": NAV, "panels": paneles,
        "refresh": "1m", "schemaVersion": 39, "tags": ["nav", "cliente", "servicios"],
        "templating": {"list": []}, "time": {"from": "now-24h", "to": "now"},
        "timepicker": {"hidden": True}, "timezone": "browser",
        "title": "Estado de servicios", "uid": "servicios", "version": 1, "weekStart": "",
    }
    SALIDA.parent.mkdir(parents=True, exist_ok=True)
    SALIDA.write_text(json.dumps(dash, indent=2, ensure_ascii=False) + "\n")
    print(f"{SALIDA.relative_to(ROOT)}: {len(servicios)} servicios -> uid servicios")
    return 0


if __name__ == "__main__":
    sys.exit(main())
