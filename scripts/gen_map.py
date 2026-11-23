#!/usr/bin/env python3
"""Genera el dashboard de mapa de red (Canvas) desde un topology.yml.

Cada nodo tiene su propia consulta (`estado_host`) con campos de color unicos
(`c_<i>`), porque Canvas resuelve el campo por nombre recorriendo los frames.
Asi cada elemento toma SU estado y no el del primero.

Uso: python3 scripts/gen_map.py [topology.yml]
"""

import json
import os
import re
import sys
import urllib.request
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts/observability"))
import queries  # noqa: E402

SALIDA = ROOT / "docker/observability/grafana/dashboards/Tecnico/mapa-red.json"


API_URL = os.getenv("ZBX_API_URL", "http://127.0.0.1/api_jsonrpc.php")


def _token() -> str:
    tok = os.getenv("ZBX_API_TOKEN", "")
    if tok:
        return tok
    env = ROOT / "docker/.env"
    if env.exists():
        for line in env.read_text().splitlines():
            if line.startswith("ZBX_API_TOKEN="):
                return line.split("=", 1)[1].strip()
    return ""


def resolver_hostids(nombres) -> dict:
    """Resuelve nombre -> hostid contra la API de Zabbix."""
    tok = _token()
    if not tok:
        sys.exit("ERROR: falta ZBX_API_TOKEN para --resolve")
    body = {"jsonrpc": "2.0", "method": "host.get",
            "params": {"output": ["hostid", "host"],
                       "filter": {"host": list(nombres)}}, "id": 1}
    req = urllib.request.Request(API_URL, data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json-rpc",
                 "Authorization": f"Bearer {tok}"})
    with urllib.request.urlopen(req, timeout=20) as resp:
        data = json.loads(resp.read())
    if "error" in data:
        sys.exit(f"ERROR resolviendo hosts: {data['error']}")
    return {h["host"]: h["hostid"] for h in data["result"]}


def generar(topo_path: Path, resolve: bool, otros) -> dict:
    cfg = yaml.safe_load(topo_path.read_text())
    nodes = cfg["nodes"]
    edges = cfg.get("edges", [])
    slug = re.sub(r"[^a-z0-9]+", "-", (cfg.get("slug") or cfg.get("name") or topo_path.stem).lower()).strip("-")
    uid = f"mapa-{slug}"

    if resolve:
        faltan = [n["name"] for n in nodes if not n.get("hostid")]
        if faltan:
            ids = resolver_hostids(faltan)
            for n in nodes:
                if not n.get("hostid"):
                    n["hostid"] = ids.get(n["name"], "")
                    if not n["hostid"]:
                        sys.exit(f"ERROR: host '{n['name']}' no existe en Zabbix")

    layout = cfg.get("layout", {})
    node_w = int(layout.get("node_w", 140))
    node_h = int(layout.get("node_h", 44))
    icon_size = int(layout.get("icon_size", 40))
    x_gap = int(layout.get("x_gap", 170))
    y_gap = int(layout.get("y_gap", 34))
    ox = int(layout.get("origin_x", 20))
    oy = int(layout.get("origin_y", 60))
    line_color = layout.get("line_color", "#8fa6c1")
    line_size = float(layout.get("line_size", 1.5))

    columnas = {}
    for n in nodes:
        columnas.setdefault(int(n.get("level", 0)), []).append(n)
    filas_max = max(len(v) for v in columnas.values())
    posiciones = {}
    for nivel, grupo in columnas.items():
        alto_col = len(grupo) * (node_h + y_gap) - y_gap
        alto_max = filas_max * (node_h + y_gap) - y_gap
        y0 = oy + (alto_max - alto_col) // 2
        for idx, n in enumerate(grupo):
            posiciones[n["name"]] = (ox + nivel * x_gap, y0 + idx * (node_h + y_gap))

    por_nombre = {n["name"]: n for n in nodes}
    salientes = {}
    for src, dst in edges:
        if src not in por_nombre or dst not in por_nombre:
            sys.exit(f"ERROR: arista con nodo desconocido: {src} -> {dst}")
        salientes.setdefault(src, []).append(dst)

    elementos, targets = [], []
    for i, node in enumerate(nodes):
        nombre = node["name"]
        x, y = posiciones[nombre]
        hostid = str(node.get("hostid", ""))
        if not hostid:
            sys.exit(f"ERROR: el nodo {nombre} no tiene hostid (usa --resolve)")
        targets.append(queries.estado_host(hostid, i))

        if node.get("icon"):
            nodo_el = {
                "type": "icon", "name": f"n_{nombre}",
                "placement": {"left": x + (node_w - icon_size) // 2, "top": y,
                              "width": icon_size, "height": icon_size},
                "config": {"path": {"mode": "fixed",
                                    "fixed": f"img/icons/unicons/{node['icon']}.svg"},
                           "fill": {"field": f"c_{i}"}},
                "links": [{"title": f"Problemas de {nombre}",
                           "url": f"/d/equipo?var-host={nombre}&var-hostid={hostid}"}],
            }
            elementos.append(nodo_el)
            elementos.append({
                "type": "text", "name": f"l_{nombre}",
                "placement": {"left": x, "top": y + icon_size + 4,
                              "width": node_w, "height": 20},
                "config": {"text": {"mode": "fixed", "fixed": node.get("label", nombre)},
                           "size": 12, "align": "center", "valign": "middle",
                           "color": {"fixed": "#ffffff"}},
            })
        else:
            nodo_el = {
                "type": "text", "name": f"n_{nombre}",
                "placement": {"left": x, "top": y, "width": node_w, "height": node_h},
                "background": {"color": {"field": f"c_{i}"}},
                "border": {"color": {"fixed": line_color}, "width": 1},
                "config": {"text": {"mode": "fixed", "fixed": node.get("label", nombre)},
                           "size": 13, "align": "center", "valign": "middle",
                           "color": {"fixed": "#ffffff"}},
                "links": [{"title": f"Problemas de {nombre}",
                           "url": f"/d/equipo?var-host={nombre}&var-hostid={hostid}"}],
            }
            elementos.append(nodo_el)

        if nombre in salientes:
            nodo_el["connections"] = [
                {"source": {"x": 1, "y": 0}, "target": {"x": -1, "y": 0},
                 "targetName": f"n_{dst}", "path": "straight",
                 "color": {"fixed": line_color},
                 "size": {"fixed": line_size, "min": 1, "max": 3},
                 "lineStyle": {"fill": "solid"}}
                for dst in salientes[nombre]
            ]

    canvas = {
        "type": "canvas", "title": cfg.get("title", "Mapa de red"),
        "description": ("Verde = sin problemas activos. Rojo = tiene problemas "
                        "(detalle en la tabla de abajo). Cada equipo consulta "
                        "su propio estado."),
        "id": 1,
        "datasource": {"type": "yesoreyeram-infinity-datasource", "uid": "zabbix-api"},
        "gridPos": {"h": 16, "w": 24, "x": 0, "y": 0},
        "targets": targets,
        "fieldConfig": {"defaults": {}, "overrides": [
            {"matcher": {"id": "byName", "options": f"c_{i}"},
             "properties": [
                 {"id": "color", "value": {"mode": "thresholds"}},
                 {"id": "thresholds", "value": {"mode": "absolute", "steps": [
                     {"color": "green", "value": None}, {"color": "red", "value": 1}]}}]}
            for i in range(len(nodes))]},
        "options": {"inlineEditing": False, "panZoom": True, "showAdvancedTypes": False,
                    "zoomToContent": True,
                    "root": {"name": "root", "type": "frame", "elements": elementos},
                    "tooltip": {"mode": "single"}},
    }

    detalle = queries.problemas_de([str(n.get("hostid")) for n in nodes])
    tab = {
        "type": "table", "title": "Problemas de los equipos del mapa", "id": 2,
        "datasource": {"type": "yesoreyeram-infinity-datasource", "uid": "zabbix-api"},
        "gridPos": {"h": 8, "w": 24, "x": 0, "y": 16},
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
                        {"type": "value", "options": {"0": {"text": "Sin clasificar", "color": "text", "index": 0}}},
                        {"type": "value", "options": {"1": {"text": "Informacion", "color": "blue", "index": 1}}},
                        {"type": "value", "options": {"2": {"text": "Aviso", "color": "semi-dark-yellow", "index": 2}}},
                        {"type": "value", "options": {"3": {"text": "Media", "color": "semi-dark-orange", "index": 3}}},
                        {"type": "value", "options": {"4": {"text": "Alta", "color": "semi-dark-red", "index": 4}}},
                        {"type": "value", "options": {"5": {"text": "Desastre", "color": "dark-red", "index": 5}}}]},
                    {"id": "custom.cellOptions", "value": {"type": "color-background"}},
                    {"id": "custom.width", "value": 140}]},
                {"matcher": {"id": "byName", "options": "Antiguedad"},
                 "properties": [{"id": "custom.width", "value": 120}]}]},
    }

    links = [
        {"type": "dashboards", "title": "Estado General", "tags": ["nav", "cliente"],
         "asDropdown": True, "icon": "user", "includeVars": False,
         "keepTime": True, "targetBlank": False},
        {"type": "dashboards", "title": "Técnico", "tags": ["nav", "tecnico"],
         "asDropdown": True, "icon": "wrench", "includeVars": False,
         "keepTime": True, "targetBlank": False},
        {"type": "dashboards", "title": "Mapas", "tags": ["nav", "mapa"],
         "asDropdown": True, "icon": "sitemap", "includeVars": False,
         "keepTime": True, "targetBlank": False},
    ]
    dash = {
        "annotations": {"list": []}, "editable": False, "fiscalYearStartMonth": 0,
        "graphTooltip": 1, "id": None, "links": links, "panels": [canvas, tab],
        "refresh": "1m", "schemaVersion": 39, "tags": ["nav", "mapa", "red"],
        "templating": {"list": []}, "time": {"from": "now-1h", "to": "now"},
        "timepicker": {"hidden": False}, "timezone": "browser",
        "title": cfg.get("title", "Mapa de red"), "uid": uid, "version": 1,
        "weekStart": "",
    }
    destino = ROOT / "docker/observability/grafana/dashboards" / cfg.get(
        "folder", "Tecnico") / f"mapa-{slug}.json"
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text(json.dumps(dash, indent=2, ensure_ascii=False) + "\n")
    return {"uid": uid, "title": dash["title"], "destino": destino,
            "nodos": len(nodes), "aristas": len(edges)}


def main() -> int:
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    resolve = "--resolve" in sys.argv
    archivos = [Path(a) for a in args] if args else sorted(
        (ROOT / "docker/observability/maps").glob("*.yml"))

    # Primera pasada: nombres de todos los mapas (para enlazarlos entre si).
    titulos = []
    for f in archivos:
        cfg = yaml.safe_load(f.read_text())
        slug = re.sub(r"[^a-z0-9]+", "-", (cfg.get("slug") or cfg.get("name") or f.stem).lower()).strip("-")
        titulos.append((f"mapa-{slug}", cfg.get("title", f"Mapa {slug}")))

    for f in archivos:
        r = generar(f, resolve, titulos)
        print(f"{r['destino'].relative_to(ROOT)}: {r['nodos']} nodos, "
              f"{r['aristas']} aristas -> {r['uid']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
