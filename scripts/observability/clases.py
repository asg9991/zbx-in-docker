"""Fuente única del catálogo de clases de incidente y de su lógica.

Antes estaba duplicada en `digest.py`, `evaluar_clasificador.py`,
`evaluar_real.py` y, en versión JSONata, en `gen_servicios.py`. Si cambia la
semántica (orden, subcadena, mayúsculas), cambia en un solo lugar.

El orden de `clases` importa: la primera que matchea gana, así que las clases
específicas van antes que las genéricas (ver `clases.yaml`).
"""

from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
CLASES = ROOT / "docker/observability/clases/clases.yaml"

# Se usa cuando una clase no tiene regla propia (incluye `desconocido`).
# Una severidad Alta o superior nunca puede dejar un servicio en verde;
# un aviso desconocido no mueve el semáforo (control de ruido).
REGLA_DESCONOCIDO = {"critico": 4, "degradado": 6}


def cargar(path: Path | None = None):
    """Devuelve (cfg, clases, reglas, regla_desconocido).

    clases: {id: {"nombre", "patrones", "logql", "accion"}}
    reglas: {id: {"critico": int, "degradado": int}}
    """
    cfg = yaml.safe_load((path or CLASES).read_text())
    reglas = cfg.get("reglas_por_clase", {})
    regla_desconocido = dict(REGLA_DESCONOCIDO)
    regla_desconocido.update(cfg.get("regla_desconocido") or {})

    clases = {}
    for c in cfg["clases"]:
        clases[c["id"]] = {
            "nombre": c["nombre"],
            "patrones": [p.lower() for p in c.get("patrones_zabbix", []) if p],
            "logql": c.get("logql", ""),
            "accion": c.get("accion", ""),
        }
    return cfg, clases, reglas, regla_desconocido


def clasificar(nombre: str, clases: dict) -> str:
    """Primera clase cuyos patrones aparecen en el nombre del trigger."""
    n = nombre.lower()
    for cid, c in clases.items():
        if cid == "desconocido":
            continue
        if any(p in n for p in c["patrones"]):
            return cid
    return "desconocido"


def patrones_conocidos(clases: dict) -> list:
    """Todos los patrones de las clases reales, en el orden del catálogo."""
    return [p for cid, c in clases.items() if cid != "desconocido"
            for p in c["patrones"]]


def _jsonata_str(value: str) -> str:
    escaped = value.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


def jsonata_nombre_en(patrones) -> str:
    """Expresión JSONata: el nombre del problema matchea alguno de los patrones."""
    if not patrones:
        return "false"
    tests = " or ".join(
        f"$contains($lowercase(name), {_jsonata_str(p)})" for p in patrones)
    return f"({tests})"


def validar(clases: dict, reglas: dict, servicios_cfg: dict,
            regla_desconocido: dict) -> list:
    """Errores de coherencia del contexto del sitio (vacío = OK)."""
    errores = []
    if not 0 <= int(regla_desconocido.get("critico", 99)) <= 5:
        errores.append("regla_desconocido.critico fuera de 0..5")
    for s in servicios_cfg.get("servicios", []):
        if not s.get("hosts"):
            errores.append(f"servicio {s['nombre']}: sin hosts")
        for cid in (s.get("reglas") or {}):
            if cid not in clases:
                errores.append(f"servicio {s['nombre']}: clase desconocida '{cid}'")
    for cid, r in reglas.items():
        if cid not in clases:
            errores.append(f"regla para clase desconocida '{cid}'")
        elif not clases[cid]["patrones"]:
            errores.append(f"clase '{cid}' sin patrones: nunca matchearia")
        if cid in clases and not clases[cid]["logql"]:
            errores.append(f"clase '{cid}' sin logql: no habria evidencia")
    return errores
