#!/usr/bin/env python3
"""Digest de problemas: clasifica, atribuye a servicios y trae evidencia.

Es el primer paso de la fase N: sin agente todavia, pero con el mismo
contrato. Lee clases.yaml (clases + reglas) y un servicios.yml del sitio,
consulta Zabbix y Loki (via proxy de Grafana) y emite un resumen.

Uso:
  python3 scripts/digest.py                         # markdown del lab
  python3 scripts/digest.py --servicios X.yml       # otro sitio
  python3 scripts/digest.py --json                  # contrato para el agente
  python3 scripts/digest.py --check                 # valida el contexto
"""

import base64
import json
import os
import sys
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts/observability"))
import clases as cat  # noqa: E402

CLASES = cat.CLASES
SERVICIOS = ROOT / "docker/observability/clases/servicios-lab.yml"

ZBX_URL = os.getenv("ZBX_API_URL", "http://127.0.0.1/api_jsonrpc.php")
GRAFANA = os.getenv("GRAFANA_URL", "http://127.0.0.1/grafana")

ESTADO = {0: "OK", 1: "DEGRADADO", 2: "CRITICO"}


def _env(k: str) -> str:
    v = os.getenv(k)
    if v:
        return v
    env = ROOT / "docker/.env"
    if env.exists():
        for line in env.read_text().splitlines():
            if line.startswith(f"{k}="):
                return line.split("=", 1)[1].strip()
    return ""


def zbx(method: str, params: dict):
    body = {"jsonrpc": "2.0", "method": method, "params": params, "id": 1}
    req = urllib.request.Request(ZBX_URL, data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json-rpc",
                 "Authorization": f"Bearer {_env('ZBX_API_TOKEN')}"})
    with urllib.request.urlopen(req, timeout=20) as r:
        data = json.loads(r.read())
    if "error" in data:
        raise RuntimeError(f"{method}: {data['error']}")
    return data["result"]


def _grafana_auth() -> dict:
    """Token de service account (Viewer) o, en su defecto, admin con aviso.

    El digest solo lee logs: no tiene por que usar la cuenta admin. El token
    se crea una vez por sitio (ver README de observability) y vive en
    GF_READ_TOKEN del .env, igual que el resto de los secretos.
    """
    token = _env("GF_READ_TOKEN")
    if token:
        return {"Authorization": f"Bearer {token}"}
    print("aviso: GF_READ_TOKEN no configurado; usando admin de Grafana",
          file=sys.stderr)
    auth = base64.b64encode(
        f"{_env('GF_ADMIN_USER')}:{_env('GF_ADMIN_PASSWORD')}".encode()).decode()
    return {"Authorization": "Basic " + auth}


def loki(logql: str, since_min: int, limit: int = 3):
    now = int(datetime.now(timezone.utc).timestamp())
    q = urllib.parse.quote(logql)
    url = (f"{GRAFANA}/api/datasources/proxy/uid/loki/loki/api/v1/query_range"
           f"?query={q}&limit={limit}"
           f"&start={now - since_min * 60}000000000&end={now}000000000")
    req = urllib.request.Request(url, headers=_grafana_auth())
    with urllib.request.urlopen(req, timeout=20) as r:
        data = json.loads(r.read())
    # Orden por timestamp y sin duplicados: el orden del response depende del
    # stream, no del tiempo, y repetir la misma línea como "evidencia" es ruido.
    con_ts = []
    for stream in data.get("data", {}).get("result", []):
        for ts, linea in stream.get("values", []):
            con_ts.append((int(ts), linea))
    vistos, ordenadas = set(), []
    for _, linea in sorted(con_ts):
        if linea in vistos:
            continue
        vistos.add(linea)
        ordenadas.append(linea)
    return ordenadas[-limit:]


def cargar_contexto(servicios_path: Path):
    clases_cfg, clases, reglas, _ = cat.cargar(CLASES)
    servicios_cfg = yaml.safe_load(servicios_path.read_text())
    return clases_cfg, clases, reglas, servicios_cfg


# Alias: el modo consulta (preguntar.py) usa la misma clasificación.
clasificar = cat.clasificar


def main() -> int:
    args = sys.argv[1:]
    servicios_path = SERVICIOS
    if "--servicios" in args:
        servicios_path = Path(args[args.index("--servicios") + 1])
    salida_json = "--json" in args
    solo_check = "--check" in args
    since = 120
    if "--since" in args:
        since = int(args[args.index("--since") + 1])

    _, clases, reglas, servicios_cfg = cargar_contexto(servicios_path)
    _, _, _, regla_desconocido = cat.cargar(CLASES)
    errores = cat.validar(clases, reglas, servicios_cfg, regla_desconocido)
    if errores:
        print("CONTEXTO INVALIDO:")
        for e in errores:
            print(f"  - {e}")
        return 1
    if solo_check:
        print(f"contexto OK: {len(clases)} clases, "
              f"{len(servicios_cfg['servicios'])} servicios")
        return 0

    declarados = [x for s in servicios_cfg["servicios"] for x in s.get("hosts", [])]
    ids = {h["host"]: h["hostid"] for h in zbx(
        "host.get", {"output": ["hostid", "host"], "filter": {"host": declarados}})}
    # Un host declarado que no existe en Zabbix dejaría su servicio en verde
    # por omisión: se reporta, no se ignora.
    ausentes = sorted({h for h in declarados if h not in ids})
    if ausentes:
        print(f"aviso: hosts declarados que no existen en Zabbix: "
              f"{', '.join(ausentes)}", file=sys.stderr)

    resultado = {"site": servicios_cfg.get("site", "?"),
                 "generado": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                 "servicios": [], "sin_servicio": [], "hosts_ausentes": ausentes}
    usados = set()

    for s in servicios_cfg["servicios"]:
        reglas_svc = {}
        for cid, r in reglas.items():
            ov = (s.get("reglas") or {}).get(cid)
            reglas_svc[cid] = {"critico": int(ov["critico"]) if ov else int(r["critico"]),
                               "degradado": int(ov["degradado"]) if ov else int(r["degradado"])}
        hallazgos, estado = [], 0
        for host in s.get("hosts", []):
            hid = ids.get(host)
            if not hid:
                continue
            for pr in zbx("problem.get", {"output": ["eventid", "name", "severity", "clock"],
                                          "hostids": [hid], "recent": False}):
                usados.add(pr["eventid"])
                cid = clasificar(pr["name"], clases)
                sev = int(pr["severity"])
                # Una clase sin regla propia (incluye `desconocido`) usa la
                # regla por defecto: Alta+ escala a critico, avisos no mueven.
                regla = reglas_svc.get(cid, regla_desconocido)
                if sev >= regla["critico"]:
                    estado = max(estado, 2)
                elif sev >= regla["degradado"]:
                    estado = max(estado, 1)
                regla = clases.get(cid, {})
                evidencia = []
                if regla.get("logql"):
                    try:
                        evidencia = loki(regla["logql"].replace("$HOST", host), since)
                    except Exception as exc:  # noqa: BLE001
                        evidencia = [f"(sin evidencia: {exc})"]
                hallazgos.append({
                    "host": host, "problema": pr["name"], "severidad": sev,
                    "clase": cid, "clase_nombre": regla.get("nombre", cid),
                    "accion": regla.get("accion", ""), "evidencia": evidencia,
                })
        hallazgos.sort(key=lambda h: -h["severidad"])
        resultado["servicios"].append({
            "nombre": s["nombre"], "criticidad": s.get("criticidad", "media"),
            "estado": ESTADO[estado], "problemas": len(hallazgos),
            "hallazgos": hallazgos,
        })

    for pr in zbx("problem.get", {"output": ["eventid", "name", "severity"],
                                  "recent": False}):
        if pr["eventid"] in usados:
            continue
        resultado["sin_servicio"].append({
            "problema": pr["name"], "severidad": int(pr["severity"]),
            "clase": clasificar(pr["name"], clases)})

    if salida_json:
        print(json.dumps(resultado, indent=2, ensure_ascii=False))
        return 0

    print(f"# Digest {resultado['site']} — {resultado['generado']}\n")
    print("## Servicios\n")
    for s in resultado["servicios"]:
        print(f"- **{s['nombre']}**: {s['estado']} ({s['problemas']} problemas)")
    if resultado["sin_servicio"]:
        print(f"\n- Sin servicio asignado: {len(resultado['sin_servicio'])} problemas")
    if resultado["hosts_ausentes"]:
        print(f"- Hosts declarados que no existen en Zabbix: "
              f"{', '.join(resultado['hosts_ausentes'])}")
    print("\n## Detalle\n")
    for s in resultado["servicios"]:
        for h in s["hallazgos"]:
            print(f"### [{s['estado']}] {s['nombre']} — {h['host']}")
            print(f"- Problema: {h['problema']} (severidad {h['severidad']})")
            print(f"- Clase: {h['clase_nombre']}")
            if h["accion"]:
                print(f"- Acción sugerida: {h['accion']}")
            for linea in h["evidencia"]:
                print(f"- Evidencia: {linea[:160]}")
            print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
