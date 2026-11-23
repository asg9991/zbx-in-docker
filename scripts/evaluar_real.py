#!/usr/bin/env python3
"""Evalúa el clasificador contra incidentes REALES, sin etiquetado humano.

La "verdad" no la decide una persona: sale de la clave del item que disparó el
trigger (`mapeo_items` en clases.yaml). Si el nombre y el item coinciden en
clase, el clasificador acierta.

Subcomandos:
  --list           qué estamos listando como incidentes (tabla + conteos)
  (sin flag)       mide precisión sobre la ventana y muestra discrepancias
  --append         agrega las discrepancias a incidentes-candidatos.yaml
  --promote        pasa los candidatos marcados `confirmado` a la retención

Uso: python3 scripts/evaluar_real.py --since 30
"""

import json
import os
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts/observability"))
import clases as cat  # noqa: E402

CLASES = cat.CLASES
# Los incidentes reales llevan nombres de equipos del sitio: viven SIEMPRE en
# el repo privado del cliente (`client/`), nunca en `tests/fixtures/`, que es
# genérico y se publica.
CLIENT_DIR = Path(os.getenv("OBS_CLIENT_DIR", ROOT / "client"))
CANDIDATOS = CLIENT_DIR / "incidentes-candidatos.yaml"
BANCO = CLIENT_DIR / "incidentes.yaml"
ZBX_URL = os.getenv("ZBX_API_URL", "http://127.0.0.1/api_jsonrpc.php")


def destino_privado(path: Path) -> Path:
    """Aborta si el destino cae en el banco genérico (datos de sitio)."""
    if (ROOT / "tests").resolve() in path.resolve().parents:
        sys.exit(f"ERROR: {path} es del repo genérico; los datos del sitio "
                 f"van a {CLIENT_DIR}/ (ver docs/clases-de-incidente.md §5)")
    return path


def env(k: str) -> str:
    v = os.getenv(k)
    if v:
        return v
    f = ROOT / "docker/.env"
    if f.exists():
        for line in f.read_text().splitlines():
            if line.startswith(f"{k}="):
                return line.split("=", 1)[1].strip()
    return ""


def zbx(method: str, params: dict):
    body = {"jsonrpc": "2.0", "method": method, "params": params, "id": 1}
    req = urllib.request.Request(ZBX_URL, data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json-rpc",
                 "Authorization": f"Bearer {env('ZBX_API_TOKEN')}"})
    with urllib.request.urlopen(req, timeout=30) as r:
        data = json.loads(r.read())
    if "error" in data:
        raise RuntimeError(f"{method}: {data['error']}")
    return data["result"]


def cargar():
    cfg, clases, _, _ = cat.cargar(CLASES)
    return cfg, clases, cfg.get("mapeo_items", {})


def clase_por_item(keys, mapeo) -> str | None:
    for key in keys:
        for prefijo, clase in mapeo.items():
            if key.startswith(prefijo):
                return clase
    return None


clasificar = cat.clasificar


def hechos(clases, mapeo, dias: int):
    """Devuelve [(nombre, esperado, obtenido, host)] desde eventos reales."""
    desde = int(datetime.now(timezone.utc).timestamp()) - dias * 86400
    eventos = zbx("event.get", {"output": ["eventid", "name", "objectid", "severity"],
                                "source": 0, "value": 1, "time_from": desde,
                                "sortfield": ["clock"], "sortorder": "DESC",
                                "limit": 500})
    if not eventos:
        return []
    tids = sorted({e["objectid"] for e in eventos})
    triggers = zbx("trigger.get", {"output": ["triggerid", "description"],
                                   "triggerids": tids,
                                   "selectItems": ["key_"],
                                   "selectHosts": ["host"]})
    por_trigger = {t["triggerid"]: t for t in triggers}
    out = []
    for e in eventos:
        t = por_trigger.get(e["objectid"])
        if not t:
            continue
        keys = [i["key_"] for i in t.get("items", [])]
        esperado = clase_por_item(keys, mapeo) if keys else None
        obtenido = clasificar(e["name"], clases)
        host = (t.get("hosts") or [{}])[0].get("host", "?")
        out.append((e["name"], esperado, obtenido, host, keys[:1]))
    return out


def main() -> int:
    args = sys.argv[1:]
    dias = 30
    if "--since" in args:
        dias = int(args[args.index("--since") + 1])
    cfg, clases, mapeo = cargar()
    filas = hechos(clases, mapeo, dias)

    if "--list" in args:
        print(f"Clases listadas ({len(clases)}):")
        for cid, patrones in clases.items():
            if cid == "desconocido":
                continue
            print(f"  {cid:12} patrones={len(patrones)}")
        print(f"\nMapeo item -> clase ({len(mapeo)} prefijos):")
        for prefijo, clase in mapeo.items():
            print(f"  {prefijo:26} -> {clase}")
        print(f"\nIncidentes en {dias} días: {len(filas)}")
        conteo = {}
        for _, esperado, _, _, _ in filas:
            conteo[esperado or "sin-etiqueta"] = conteo.get(esperado or "sin-etiqueta", 0) + 1
        for k, v in sorted(conteo.items(), key=lambda x: -x[1]):
            print(f"  {k:14} {v}")
        return 0

    etiquetados = [(n, e, o, h, k) for n, e, o, h, k in filas if e]
    sin_etiqueta = len(filas) - len(etiquetados)
    aciertos = sum(1 for _, e, o, _, _ in etiquetados if e == o)
    total = len(etiquetados)
    prec = aciertos / total if total else 0

    print(f"incidentes: {len(filas)}  con clase derivada: {total}  "
          f"sin etiqueta: {sin_etiqueta}")
    print(f"precisión automática: {aciertos}/{total} = {prec:.1%}")

    discrepancias = [(n, e, o, h, k) for n, e, o, h, k in etiquetados if e != o]
    if discrepancias:
        print("\ndiscrepancias (nombre vs item):")
        for n, e, o, h, k in discrepancias[:15]:
            print(f"  {h}: {n[:52]!r} item={k[0] if k else '?'} "
                  f"esperado={e} obtenido={o}")

    if "--append" in args and discrepancias:
        destino_privado(CANDIDATOS)
        cand = yaml.safe_load(CANDIDATOS.read_text()) if CANDIDATOS.exists() else {"casos": []}
        existentes = {c["nombre"] for c in cand.get("casos", [])}
        nuevos = 0
        for n, e, o, h, _ in discrepancias:
            if n in existentes:
                continue
            cand.setdefault("casos", []).append({
                "id": f"c{len(cand['casos']) + 1:03d}", "nombre": n,
                "esperado": e, "obtenido": o, "host_ejemplo": h,
                "estado": "pendiente"})
            nuevos += 1
        CANDIDATOS.parent.mkdir(parents=True, exist_ok=True)
        CANDIDATOS.write_text(yaml.safe_dump(cand, allow_unicode=True,
                                             sort_keys=False, width=100))
        print(f"\ncandidatos agregados: {nuevos} (revisar y marcar 'confirmado')")

    if "--promote" in args and CANDIDATOS.exists():
        destino_privado(BANCO)
        cand = yaml.safe_load(CANDIDATOS.read_text())
        confirmados = [c for c in cand.get("casos", []) if c.get("estado") == "confirmado"]
        if confirmados:
            banco = yaml.safe_load(BANCO.read_text()) if BANCO.exists() else \
                {"umbral": 0.80, "casos": [], "holdout": []}
            hold = banco.setdefault("holdout", [])
            nombres = {c["nombre"] for c in hold}
            agregados = 0
            for c in confirmados:
                if c["nombre"] in nombres:
                    continue
                hold.append({"id": f"h{len(hold) + 1:02d}", "nombre": c["nombre"],
                             "esperado": c["esperado"]})
                agregados += 1
            BANCO.write_text(yaml.safe_dump(banco, allow_unicode=True,
                                            sort_keys=False, width=100))
            cand["casos"] = [c for c in cand["casos"] if c.get("estado") != "confirmado"]
            CANDIDATOS.write_text(yaml.safe_dump(cand, allow_unicode=True,
                                                 sort_keys=False, width=100))
            print(f"promovidos a retención: {agregados}")
        else:
            print("no hay candidatos confirmados")

    return 0 if prec >= 0.8 or total == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
