#!/usr/bin/env python3
"""Inyecta las consultas canonicas en los dashboards provisionados.

Cada target de Infinity lleva `"query": "<nombre>"`; este script reemplaza su
body/root_selector/columnas por la definicion de scripts/observability/queries.py.
Asi el API se cambia en un solo archivo.

Uso: python3 scripts/gen_queries.py [--check]
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "observability"))
import queries  # noqa: E402

DASH = Path(__file__).resolve().parents[1] / "docker/observability/grafana/dashboards"


def iter_targets(panels):
    for pan in panels:
        for t in pan.get("targets", []):
            yield t
        yield from iter_targets(pan.get("panels", []))


def main() -> int:
    check = "--check" in sys.argv
    cambios = 0
    for path in sorted(DASH.rglob("*.json")):
        dash = json.loads(path.read_text())
        tocado = False
        for t in iter_targets(dash.get("panels", [])):
            nombre = t.get("query")
            if not nombre or t.get("source") == "inline":
                continue
            if nombre not in queries.QUERIES:
                print(f"ERROR {path.name}: consulta desconocida '{nombre}'")
                return 1
            nuevo = queries.target(nombre, t.get("refId", "A"))
            nuevo["query"] = nombre
            if t != nuevo:
                if not check:
                    t.clear()
                    t.update(nuevo)
                tocado = True
                cambios += 1
        if tocado and not check:
            path.write_text(json.dumps(dash, indent=2, ensure_ascii=False) + "\n")
            print(f"actualizado: {path.relative_to(DASH)}")
    if check and cambios:
        print(f"{cambios} target(s) desactualizados")
        return 1
    print(f"{'ok' if check else 'listo'}: {cambios} target(s) {'verificados' if check else 'regenerados'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
