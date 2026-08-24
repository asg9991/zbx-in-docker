#!/usr/bin/env python3
"""lab-simulator: alimenta items trapper de los hosts simulados del lab.

Cada metrica es una funcion pura del reloj (sin estado): el valor en el
instante t se deriva del baseline + ventanas de incidente ciclicas. Esto
hace el simulador determinista, reanudable y facil de razonar.

Configuracion: docker/simulator/scenarios.yml (montado read-only).
Requiere zabbix_sender en PATH y ZABBIX_SERVER alcanzable.
"""

import os
import random
import subprocess
import sys
import time

import yaml

SCENARIOS_FILE = os.getenv("LAB_SCENARIOS", "/etc/lab-sim/scenarios.yml")
SERVER = os.getenv("ZABBIX_SERVER", "zabbix-server")
PORT = os.getenv("ZABBIX_TRAPPER_PORT", "10051")


def send(host: str, key: str, value) -> None:
    """Envia un valor al trapper y loguea el resultado de una linea."""
    result = subprocess.run(
        ["zabbix_sender", "-z", SERVER, "-p", PORT, "-s", host, "-k", key,
         "-o", str(value)],
        capture_output=True, text=True)
    output = (result.stdout.strip().splitlines() or [result.stderr.strip()])[-1]
    stamp = time.strftime("%H:%M:%S")
    print(f"[{stamp}] {host} {key}={value} :: {output}", flush=True)


def in_window(now: float, incident: dict) -> bool:
    """True si 'now' cae dentro de la ventana ciclica del incidente."""
    return (now % incident["every"]) < incident["duration"]


class Metric:
    """Un item trapper con baseline, jitter, rampas e incidentes."""

    def __init__(self, host: str, spec: dict, t0: float):
        self.host = host
        self.key = spec["key"]
        self.baseline = float(spec.get("baseline", 0))
        self.jitter = float(spec.get("jitter", 0))
        self.incidents = spec.get("incidents", [])
        self.ramp = spec.get("ramp")
        self.integer = bool(spec.get("integer")) or self.key.endswith(".status")
        self.t0 = t0

    def value_at(self, now: float):
        value = self.baseline

        if self.ramp:
            # Crecimiento lineal desde t0 hasta clavarse en target.
            span = self.ramp["minutes"] * 60
            rate = (float(self.ramp["target"]) - self.baseline) / span
            value = min(float(self.ramp["target"]),
                        max(value, self.baseline + (now - self.t0) * rate))

        # El primer incidente cuya ventana matchee gana; el jitter solo se
        # aplica sobre el baseline sano (fuera de ventanas y sin rampa).
        for incident in self.incidents:
            if in_window(now, incident):
                value = float(incident["value"])
                break

        if self.jitter and value == self.baseline:
            value += random.uniform(-self.jitter, self.jitter)

        return int(round(value)) if self.integer else round(value, 2)


def main() -> int:
    try:
        with open(SCENARIOS_FILE, encoding="utf-8") as handle:
            config = yaml.safe_load(handle)
    except FileNotFoundError:
        print(f"ERROR: no encuentro {SCENARIOS_FILE}", file=sys.stderr)
        return 1

    interval = int(config.get("interval", 10))
    devices = config.get("devices", {})
    t0 = time.time()

    metrics = []
    for host, device in devices.items():
        for spec in device.get("metrics", []):
            metrics.append(Metric(host, spec, t0))

    print(f"lab-simulator arriba: {len(metrics)} metricas en "
          f"{len(devices)} equipos, intervalo {interval}s", flush=True)

    while True:
        started = time.time()
        for metric in metrics:
            send(metric.host, metric.key, metric.value_at(started))
        # Mantener cadencia estable aunque el envio tarde.
        elapsed = time.time() - started
        time.sleep(max(1.0, interval - elapsed))


if __name__ == "__main__":
    sys.exit(main())
