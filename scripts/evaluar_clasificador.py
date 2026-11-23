#!/usr/bin/env python3
"""Mide la precisión del clasificador contra el banco de incidentes reales.

Es la puerta de N6: sin >= umbral no se habilitan acciones del agente.

Uso: python3 scripts/evaluar_clasificador.py [--verbose]
"""

import os
import sys
from collections import Counter, defaultdict
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts/observability"))
import clases as cat  # noqa: E402

CLASES = cat.CLASES
# Banco genérico (anonimizado) + banco del sitio en su repo privado.
BANCO = ROOT / "tests/fixtures/incidentes.yaml"
BANCO_SITIO = Path(os.getenv("OBS_CLIENT_DIR", ROOT / "client")) / "incidentes.yaml"


def cargar_banco() -> dict:
    """Banco genérico + banco del sitio (si existe), en ese orden."""
    banco = yaml.safe_load(BANCO.read_text())
    if BANCO_SITIO.exists():
        sitio = yaml.safe_load(BANCO_SITIO.read_text())
        banco["casos"] = list(banco.get("casos", [])) + list(sitio.get("casos", []))
        banco["holdout"] = list(banco.get("holdout", [])) + list(sitio.get("holdout", []))
    return banco


def main() -> int:
    verbose = "--verbose" in sys.argv
    _, clases, _, _ = cat.cargar(CLASES)
    banco = cargar_banco()
    umbral = float(banco.get("umbral", 0.8))
    if BANCO_SITIO.exists():
        sitio = yaml.safe_load(BANCO_SITIO.read_text())
        umbral = float(sitio.get("umbral", umbral))
    casos = banco["casos"]
    holdout = banco.get("holdout", [])

    aciertos, fallos = 0, []
    por_clase = defaultdict(lambda: [0, 0])   # [ok, total]
    matriz = Counter()

    for caso in casos:
        esperado = caso["esperado"]
        obtenido = cat.clasificar(caso["nombre"], clases)
        matriz[(esperado, obtenido)] += 1
        por_clase[esperado][1] += 1
        if obtenido == esperado:
            aciertos += 1
            por_clase[esperado][0] += 1
        else:
            fallos.append((caso["id"], caso["nombre"], esperado, obtenido))

    total = len(casos)
    precision = aciertos / total if total else 0

    if holdout:
        h_ok, h_fallos = 0, []
        for caso in holdout:
            obtenido = cat.clasificar(caso["nombre"], clases)
            if obtenido == caso["esperado"]:
                h_ok += 1
            else:
                h_fallos.append((caso["id"], caso["nombre"], caso["esperado"], obtenido))
        h_prec = h_ok / len(holdout)
        print(f"RETENCIÓN (no usada para ajustar): {h_ok}/{len(holdout)} = {h_prec:.1%}")
        for cid, nombre, esp, obt in h_fallos:
            print(f"  {cid} {nombre[:58]!r} -> esperado {esp}, obtenido {obt}")
        if h_prec < umbral:
            print(f"  RESULTADO RETENCIÓN: NO CUMPLE (< {umbral:.0%})")
        else:
            print(f"  RESULTADO RETENCIÓN: CUMPLE (>= {umbral:.0%})")
        print()

    print(f"calibración: {total} casos  aciertos: {aciertos}  precisión: {precision:.1%}  "
          f"umbral: {umbral:.0%}\n")
    print("por clase (aciertos/total):")
    for cid, (ok, tot) in sorted(por_clase.items()):
        marca = "OK " if ok == tot else "FALLA"
        print(f"  {marca} {cid:12} {ok}/{tot}")
    if fallos:
        print("\nfallos:")
        for cid, nombre, esp, obt in fallos:
            print(f"  {cid} {nombre[:60]!r} -> esperado {esp}, obtenido {obt}")
    if verbose:
        print("\nmatriz (esperado -> obtenido):")
        for (esp, obt), n in sorted(matriz.items()):
            if esp != obt:
                print(f"  {esp} -> {obt}: {n}")

    # La puerta es la retención: la calibración la usamos para ajustar.
    if holdout:
        if h_prec < umbral:
            print(f"\nRESULTADO: NO CUMPLE en retención ({h_prec:.1%} < {umbral:.0%})")
            return 1
        print(f"\nRESULTADO: CUMPLE en retención ({h_prec:.1%} >= {umbral:.0%})")
        return 0
    if precision < umbral:
        print(f"\nRESULTADO: NO CUMPLE ({precision:.1%} < {umbral:.0%})")
        return 1
    print(f"\nRESULTADO: CUMPLE ({precision:.1%} >= {umbral:.0%})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
