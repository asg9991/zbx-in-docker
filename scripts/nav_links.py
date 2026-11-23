#!/usr/bin/env python3
"""Unifica la navegacion entre dashboards.

En vez de listar cada dashboard en la barra superior (se desactualiza y
ocupa lugar), cada dashboard lleva UN link de tipo `dashboards` filtrado por
la etiqueta `nav`. Grafana arma el desplegable solo: agregar un dashboard es
ponerle la etiqueta.

Uso: python3 scripts/nav_links.py [--check]
"""

import json
import sys
from pathlib import Path

DASH = Path(__file__).resolve().parents[1] / "docker/observability/grafana/dashboards"
TAG = "nav"

# Dos menus separados por audiencia. Grafana filtra por TODAS las etiquetas
# (and), asi cada desplegable muestra solo su grupo.
NAV_LINKS = [
    {"type": "dashboards", "title": "Estado General", "tags": [TAG, "cliente"],
     "asDropdown": True, "icon": "user", "includeVars": False,
     "keepTime": True, "targetBlank": False},
    {"type": "dashboards", "title": "Técnico", "tags": [TAG, "tecnico"],
     "asDropdown": True, "icon": "wrench", "includeVars": False,
     "keepTime": True, "targetBlank": False},
    {"type": "dashboards", "title": "Mapas", "tags": [TAG, "mapa"],
     "asDropdown": True, "icon": "sitemap", "includeVars": False,
     "keepTime": True, "targetBlank": False},
]

# Dashboards que NO se listan: se llega por link directo (drill-down).
OCULTOS = {"equipo"}
AUDIENCIAS = ("cliente", "tecnico", "mapa")


def main() -> int:
    check = "--check" in sys.argv
    cambios = 0
    errores = 0
    for path in sorted(DASH.rglob("*.json")):
        dash = json.loads(path.read_text())
        tags = [t for t in dash.get("tags", []) if t != TAG]
        aud = [t for t in tags if t in AUDIENCIAS]
        oculto = dash.get("uid") in OCULTOS

        if oculto:
            if aud:
                print(f"ERROR {path.name}: oculto pero tiene audiencia {aud}")
                errores += 1
            nuevo_tags = tags
        else:
            if len(aud) != 1:
                print(f"ERROR {path.name}: debe tener una sola audiencia {AUDIENCIAS}, tiene {aud}")
                errores += 1
            nuevo_tags = [TAG] + tags
        # Reemplaza TODOS los links: la barra queda con los tres menus.
        nuevo_links = list(NAV_LINKS)
        if dash.get("links") != nuevo_links or dash.get("tags") != nuevo_tags:
            cambios += 1
            if not check:
                dash["links"] = nuevo_links
                dash["tags"] = nuevo_tags
                path.write_text(json.dumps(dash, indent=2, ensure_ascii=False) + "\n")
                print(f"actualizado: {path.relative_to(DASH)}")
    if errores:
        print(f"{errores} dashboard(s) con audiencia invalida")
        return 1
    if check and cambios:
        print(f"{cambios} dashboard(s) sin menu de navegacion")
        return 1
    print(f"{'ok' if check else 'listo'}: {cambios} dashboard(s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
