#!/usr/bin/env python3
"""lab-simulator: alimenta el lab por dos caminos.

1. Items trapper de Zabbix (metricas): cada metrica es una funcion pura del
   reloj (baseline + ventanas de incidente ciclicas), determinista y sin
   estado.
2. Syslog a rsyslog (logs): eventos por clase de equipo, con severidad real y
   una siembra historica de N dias para que los dashboards tengan tendencia.

Los dos caminos son independientes: las ventanas de incidente son por metrica
y los logs se eligen por peso. No hay correlacion garantizada metrica-log.

Configuracion: docker/simulator/scenarios.yml (montado read-only).
"""

import os
import random
import socket
import subprocess
import sys
import time
from datetime import datetime, timedelta, timezone

import yaml

SCENARIOS_FILE = os.getenv("LAB_SCENARIOS", "/etc/lab-sim/scenarios.yml")
SERVER = os.getenv("ZABBIX_SERVER", "zabbix-server")
PORT = os.getenv("ZABBIX_TRAPPER_PORT", "10051")
SYSLOG_HOST = os.getenv("SYSLOG_HOST", "rsyslog")
SYSLOG_PORT = int(os.getenv("SYSLOG_PORT", "1514"))

# facility local0 (16) * 8 + severidad syslog
SEVERITY_PRI = {"emerg": 0, "alert": 1, "crit": 2, "err": 3,
                "warning": 4, "notice": 5, "info": 6, "debug": 7}


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
            span = self.ramp["minutes"] * 60
            rate = (float(self.ramp["target"]) - self.baseline) / span
            value = min(float(self.ramp["target"]),
                        max(value, self.baseline + (now - self.t0) * rate))

        for incident in self.incidents:
            if in_window(now, incident):
                value = float(incident["value"])
                break

        if self.jitter and value == self.baseline:
            value += random.uniform(-self.jitter, self.jitter)

        if value < 0:
            value = 0

        return int(round(value)) if self.integer else round(value, 2)


class SyslogSim:
    """Genera syslog por clase de equipo y lo manda al receptor."""

    def __init__(self, config: dict):
        self.devices = config.get("devices", [])
        self.events = config.get("events", {})
        self.backfill_days = int(os.getenv(
            "LAB_BACKFILL_DAYS", config.get("backfill_days", 0)))
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sent = 0

    def _line(self, when: datetime, host: str, event: dict) -> bytes:
        pri = 16 * 8 + SEVERITY_PRI.get(event.get("severity", "info"), 6)
        # RFC5424 con zona explicita (Z). Con RFC3164 el receptor interpreta
        # la hora en SU zona y, si el emisor esta en UTC, el mensaje queda
        # 3 h en el futuro y Loki lo rechaza ("timestamp too new").
        stamp = when.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3]
        tag = event["tag"]
        msg = event["msg"].replace("$HOST", host)
        # RFC5424: PRI VERSION TS HOST APP-NAME PROCID MSGID STRUCTURED-DATA MSG.
        # Sin el campo STRUCTURED-DATA el receptor no parsea el formato real
        # que mandan los equipos, y la demo no probaria lo que hay en el sitio.
        return f"<{pri}>1 {stamp}Z {host} {tag} - - - {msg}\n".encode()

    def _emit(self, when: datetime, host: str, cls: str, count: int) -> None:
        catalog = self.events.get(cls, [])
        if not catalog:
            return
        weights = [e.get("weight", 1) for e in catalog]
        for _ in range(count):
            event = random.choices(catalog, weights=weights, k=1)[0]
            try:
                self.sock.sendto(self._line(when, host, event),
                                 (SYSLOG_HOST, SYSLOG_PORT))
                self.sent += 1
            except OSError:
                return

    def run_backfill(self) -> None:
        """Siembra historica: N dias hacia atras, repartido por hora."""
        if self.backfill_days <= 0:
            return
        now = datetime.now()
        total = 0
        for day in range(self.backfill_days, 0, -1):
            for device in self.devices:
                per_hour = float(device.get("per_hour", 0))
                # Menos volumen cuanto mas atras, para que se vea natural.
                factor = 1.0 if day <= 2 else 0.6
                for hour in range(24):
                    n = int(round(per_hour * factor))
                    if n <= 0:
                        continue
                    base = now - timedelta(days=day)
                    when = base.replace(hour=hour, minute=random.randint(0, 59),
                                        second=random.randint(0, 59))
                    self._emit(when, device["host"], device.get("class", ""), n)
                    total += n
        print(f"syslog backfill: {total} lineas en {self.backfill_days} dias "
              f"({self.sent} enviadas)", flush=True)

    def tick(self, interval: float) -> None:
        for device in self.devices:
            rate = float(device.get("per_hour", 0)) / 3600.0 * interval
            n = int(rate)
            if random.random() < (rate - n):
                n += 1
            if n:
                self._emit(datetime.now(), device["host"],
                           device.get("class", ""), n)


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

    # Trafico de interfaces: se sintetiza desde el bloque `traffic` para no
    # repetir dos metricas por equipo en scenarios.yml.
    for dev in config.get("traffic", {}).get("devices", []):
        for key, base, mult in (("lab.net.if.in", dev.get("in_mbps", 10), 1.0),
                                ("lab.net.if.out", dev.get("out_mbps", 5), 1.0)):
            spec = {
                "key": key,
                "baseline": base,
                "jitter": round(base * 0.15, 2),
                "incidents": [{
                    "every": dev.get("every", 900),
                    "duration": dev.get("duration", 180),
                    "value": round(base * 3, 2),
                }],
            }
            metrics.append(Metric(dev["host"], spec, t0))

    syslog_cfg = config.get("syslog", {})
    sim = SyslogSim(syslog_cfg)

    print(f"lab-simulator arriba: {len(metrics)} metricas, "
          f"{len(syslog_cfg.get('devices', []))} equipos con syslog, "
          f"intervalo {interval}s", flush=True)

    sim.run_backfill()

    if os.getenv("LAB_BACKFILL_ONLY") == "1":
        print("backfill-only: saliendo", flush=True)
        return 0

    while True:
        started = time.time()
        for metric in metrics:
            send(metric.host, metric.key, metric.value_at(started))
        sim.tick(max(1.0, interval))
        elapsed = time.time() - started
        time.sleep(max(1.0, interval - elapsed))


if __name__ == "__main__":
    sys.exit(main())
