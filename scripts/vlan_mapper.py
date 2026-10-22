#!/usr/bin/env python3
"""vlan_mapper.py — publica el JSON de VLANs para la LLD de los CHR de site-a.

Problema que resuelve
---------------------
La regla LLD `net.vlan.discovery` (templates 10868/10869) usa como master el
item SNMP `net.vlan.walk`, que walkea 4 columnas de la ifTable. En los CHR de
site-a la ifTable tiene 2.190 filas (2.188 son interfaces dinamicas que crea el
propio servicio PPPoE "Enlace"). Un walk de UNA columna son 118.784 bytes y el
valor de un item Zabbix se corta a 65.535 bytes -> el master devuelve texto
truncado -> el motor LLD parsea un subconjunto arbitrario -> se descubren 2
de las 8 VLANs.

Este script reemplaza ese master por un item TRAPPER (tipo 2 en Zabbix 7.4):
hace un walk de UNA sola columna (ifDescr) por CHR, filtra las VLANs y
publica un JSON chico y exacto con `zabbix_sender`.

ALCANCE: esta solucion es ESPECIFICA de site-a (los CHR de site-a terminan el
PPPoE de ~2.000 usuarios y por eso la ifTable se infla). En los demas sitios
(site-b, otros clientes) la LLD por SNMP walk funciona y NO hay que portar
este diseno sin volver a medir la ifTable.

Contrato del JSON (verificado en el lab local, ver scripts/lab_lld_shape_test.py)
------------------------------------------------------------------------------
    [ {"ifdescr":"vlan175","ifname":"vlan175","index":102}, ... ]

array de objetos, un objeto por VLAN, con "index" = ifIndex. La regla LLD
debe declarar los macro paths `$.ifdescr`, `$.ifname` y `$.index`.

Uso
---
    python3 scripts/vlan_mapper.py --dry-run              # imprime, no publica
    python3 scripts/vlan_mapper.py --config <archivo>     # config propia
    python3 scripts/vlan_mapper.py --host SW-EDGE-703     # un solo CHR

El transporte y el destino son configurables (container, server, puerto, key):
no hay ningun `docker exec` ni `zabbix_sender` hardcodeado en el codigo.
"""

import argparse
import json
import os
import re
import subprocess
import sys
import time

# --------------------------------------------------------------------------
# Configuracion por defecto: los 7 CHR de site-a.
#
# IPs y hostids verificados contra la base de site-a (tabla `interface`) el
# 2026-10-21. OJO: el nombre->hostid de 601/602 esta invertido en varias
# notas del repo; la fuente de verdad es la base:
#   SW-EDGE-501 = 10844 = 192.0.2.57
#   SW-EDGE-502 = 10845 = 192.0.2.59
#   SW-EDGE-601 = 10848 = 192.0.2.60
#   SW-EDGE-602 = 10846 = 192.0.2.61
#   SW-EDGE-701 = 10877 = 192.0.2.62
#   SW-EDGE-702 = 10878 = 192.0.2.64
#   SW-EDGE-703 = 10879 = 192.0.2.65
# 501 y 502 no responden SNMP (estan caidos): el mapper los saltea con error.
# --------------------------------------------------------------------------
DEFAULT_CONFIG = {
    "zabbix": {
        "server": "127.0.0.1",
        "port": 10051,
        "key": "net.vlan.map",
        "docker_binary": "docker",
        "use_docker": True,
        "container": "zabbix-server",
        "sender_binary": "zabbix_sender",
    },
    "snmp": {
        "version": 2,
        "community": "public",
        "timeout": 15,
        "retries": 1,
        "oid": "1.3.6.1.2.1.2.2.1.2",
        "binary": "snmpwalk",
    },
    "vlan": {
        # El mapper NO lleva listas de VLANs: la autoridad de que se monitorea
        # una VLAN es la macro de host {$site-a.VLAN.MATCHES} (el filtro de la
        # LLD). El mapper publica todas las interfaces vlan* que encuentra en
        # el router y deja que el filtro las rechaze. Asi, agregar una VLAN a un
        # CHR es tocar UNA sola lista (su macro).
        "pattern": "^vlan",
        # Interfaces que se descartan aunque el pattern las acepte.
        "exclude_pattern": "^pppoe-",
    },
    "hosts": [
        {"zabbix_host": "SW-EDGE-501", "ip": "192.0.2.57"},
        {"zabbix_host": "SW-EDGE-502", "ip": "192.0.2.59"},
        {"zabbix_host": "SW-EDGE-601", "ip": "192.0.2.60"},
        {"zabbix_host": "SW-EDGE-602", "ip": "192.0.2.61"},
        {"zabbix_host": "SW-EDGE-701", "ip": "192.0.2.62"},
        {"zabbix_host": "SW-EDGE-702", "ip": "192.0.2.64"},
        {"zabbix_host": "SW-EDGE-703", "ip": "192.0.2.65"},
    ],
}

FIXTURE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fixtures", "vlan_mapper")


# --------------------------------------------------------------------------
# Config
# --------------------------------------------------------------------------
def load_config(path=None):
    """Carga la configuracion (JSON o YAML). Sin path -> DEFAULT_CONFIG."""
    path = path or os.getenv("VLAN_MAPPER_CONFIG")
    if not path:
        return json.loads(json.dumps(DEFAULT_CONFIG))
    with open(path, encoding="utf-8") as handle:
        text = handle.read()
    try:
        import yaml  # opcional
        data = yaml.safe_load(text)
    except ImportError:
        data = json.loads(text)
    if not isinstance(data, dict):
        raise ValueError("el archivo de configuracion debe ser un objeto: %s" % path)
    return data


# --------------------------------------------------------------------------
# SNMP
# --------------------------------------------------------------------------
# net-snmp no acepta "-v2": para SNMPv2c la sintaxis es "-v 2c".
SNMP_VERSION_FLAGS = {1: "1", 2: "2c", 3: "3"}


def build_snmpwalk_command(ip, community, oid, version=2, timeout=15, retries=1,
                            binary="snmpwalk"):
    """Arma el comando snmpwalk de UNA columna (ifDescr)."""
    version_flag = SNMP_VERSION_FLAGS.get(int(version), "2c")
    return [
        binary,
        "-v", version_flag,
        "-c", community,
        "-t", str(timeout),
        "-r", str(retries),
        "-Oq",          # numerico, sin nombres MIB
        ip,
        oid,
    ]


def run_snmpwalk(ip, community, oid, version=2, timeout=15, retries=1, binary="snmpwalk"):
    """Walk de UNA columna por SNMP. Devuelve la salida cruda (texto).

    Se separa en su propia funcion para que el test pueda inyectar un walker
    falso y no toque la red.
    """
    command = build_snmpwalk_command(ip, community, oid, version, timeout, retries, binary)
    result = subprocess.run(command, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError("snmpwalk fallo (rc=%d): %s" % (result.returncode, result.stderr.strip()))
    return result.stdout


def normalize_oid(raw_oid):
    """Normaliza el OID de la salida de snmpwalk a forma numerica.

    net-snmp imprime distinto segun la version y los MIBs cargados:
        .1.3.6.1.2.1.2.2.1.2.98      (punto inicial)
        iso.3.6.1.2.1.2.2.1.2.98     (net-snmp 5.9 en site-a: raiz "iso" siempre)
        1.3.6.1.2.1.2.2.1.2.98       (numerico pelado)
    """
    oid = raw_oid.strip().strip('"')
    # las raices con nombre se vuelven a su numero: iso. -> 1., ccitt. -> 0.
    for root, numeric in (("joint-iso-ccitt.", "2."), ("ccitt.", "0."), ("iso.", "1.")):
        if oid.startswith(root):
            oid = numeric + oid[len(root):]
            break
    return oid.lstrip(".")


def parse_walk_output(text, oid="1.3.6.1.2.1.2.2.1.2"):
    """Parsea la salida de `snmpwalk -Oq` -> lista de (ifIndex, nombre).

    Acepta las tres formas de OID que usa net-snmp (ver normalize_oid).
    """
    prefix = oid.strip(".") + "."
    rows = []
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        match = re.match(r'^"?(\S+)"?\s+(.*)$', line)
        if not match:
            continue
        raw_oid, raw_value = normalize_oid(match.group(1)), match.group(2).strip()
        if not raw_oid.startswith(prefix):
            continue
        try:
            index = int(raw_oid[len(prefix):].split(".")[0])
        except ValueError:
            continue
        if len(raw_value) >= 2 and raw_value.startswith('"') and raw_value.endswith('"'):
            raw_value = raw_value[1:-1]
        rows.append((index, raw_value))
    return rows


# --------------------------------------------------------------------------
# Filtro y payload
# --------------------------------------------------------------------------
def filter_vlans(rows, pattern=None, exclude_pattern=None):
    """Deja solo las interfaces VLAN que el router tiene.

    El mapper NO aplica ninguna lista de VLANs: la autoridad de que una VLAN
    se monitorea en un CHR es la macro de host {$site-a.VLAN.MATCHES}, que
    aplica el filtro de la LLD. Acá solo se descarta lo que no es una
    interfaz de VLAN (por ejemplo el churn `pppoe-*`).
    """
    pattern_re = re.compile(pattern) if pattern else None
    exclude_re = re.compile(exclude_pattern) if exclude_pattern else None

    vlans = []
    for index, name in rows:
        if pattern_re and not pattern_re.match(name):
            continue
        if exclude_re and exclude_re.match(name):
            continue
        if not name.startswith("vlan"):
            continue
        vlans.append({"ifdescr": name, "ifname": name, "index": index})
    vlans.sort(key=lambda entry: entry["index"])
    return vlans


def build_payload(vlans):
    """JSON del master (contrato verificado en T1): array de objetos."""
    return json.dumps(vlans, separators=(",", ":"))


# --------------------------------------------------------------------------
# Publicacion
# --------------------------------------------------------------------------
def publish(zabbix_config, zabbix_host, payload):
    """Publica el JSON con zabbix_sender. Devuelve (ok, salida)."""
    if zabbix_config.get("use_docker", True):
        command = [
            zabbix_config.get("docker_binary", "docker"),
            "exec",
            zabbix_config["container"],
            zabbix_config.get("sender_binary", "zabbix_sender"),
            "-z", str(zabbix_config["server"]),
            "-p", str(zabbix_config["port"]),
            "-s", zabbix_host,
            "-k", zabbix_config["key"],
            "-o", payload,
        ]
    else:
        command = [
            zabbix_config.get("sender_binary", "zabbix_sender"),
            "-z", str(zabbix_config["server"]),
            "-p", str(zabbix_config["port"]),
            "-s", zabbix_host,
            "-k", zabbix_config["key"],
            "-o", payload,
        ]
    result = subprocess.run(command, capture_output=True, text=True)
    output = (result.stdout.strip().splitlines() or [result.stderr.strip()])[-1]
    ok = result.returncode == 0 and "failed: 0" in result.stdout
    return ok, output


# --------------------------------------------------------------------------
# Flujo por host
# --------------------------------------------------------------------------
def collect_host(host_config, config, walker=run_snmpwalk):
    """Walk + filtro de un CHR. Devuelve (vlan_publicadas, filas, error)."""
    snmp = config.get("snmp", {})
    vlan = config.get("vlan", {})
    community = host_config.get("community") or snmp.get("community", "public")
    try:
        raw = walker(
            host_config["ip"],
            community,
            snmp.get("oid", "1.3.6.1.2.1.2.2.1.2"),
            version=snmp.get("version", 2),
            timeout=snmp.get("timeout", 15),
            retries=snmp.get("retries", 1),
            binary=snmp.get("binary", "snmpwalk"),
        )
    except Exception as exc:  # un CHR caido no debe tumbar al resto
        return [], 0, str(exc)
    rows = parse_walk_output(raw, snmp.get("oid", "1.3.6.1.2.1.2.2.1.2"))
    vlans = filter_vlans(
        rows,
        pattern=vlan.get("pattern"),
        exclude_pattern=vlan.get("exclude_pattern"),
    )
    return vlans, len(rows), None


def run(config, dry_run=False, only=None, walker=run_snmpwalk, verbose=False):
    """Procesa todos los hosts. Devuelve el codigo de salida (0 = todo bien)."""
    failures = 0
    for host in config.get("hosts", []):
        stamp = time.strftime("%Y-%m-%d %H:%M:%S")
        name = host.get("zabbix_host")
        if only and name != only:
            continue
        if not host.get("ip"):
            print("[%s] %s: sin IP configurada -> se saltea (completar la config)" % (stamp, name))
            failures += 1
            continue
        vlans, rows, error = collect_host(host, config, walker=walker)
        stamp = time.strftime("%Y-%m-%d %H:%M:%S")
        if error:
            print("[%s] %s (%s): ERROR %s" % (stamp, name, host["ip"], error))
            failures += 1
            continue
        payload = build_payload(vlans)
        published = ", ".join(vlan["ifdescr"] for vlan in vlans) or "(ninguna)"
        print("[%s] %s (%s): %d filas de ifTable, %d VLANs publicadas: %s" % (
            stamp, name, host["ip"], rows, len(vlans), published))
        if verbose:
            print("[%s] %s: %s" % (stamp, name, payload))
        if dry_run:
            continue
        if not vlans:
            print("[%s] %s: 0 VLANs -> no se publica (para no vaciar el LLD)" % (stamp, name))
            continue
        ok, output = publish(config.get("zabbix", {}), name, payload)
        if not ok:
            print("[%s] %s: ERROR publicando -> %s" % (stamp, name, output))
            failures += 1
        else:
            print("[%s] %s: publicado (%s)" % (stamp, name, output))
    return 1 if failures else 0


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--config", help="archivo de configuracion (JSON o YAML)")
    parser.add_argument("--dry-run", action="store_true", help="imprime el JSON y no publica")
    parser.add_argument("--host", help="procesa solo ese host (nombre Zabbix)")
    parser.add_argument("--verbose", action="store_true", help="detalle por host")
    args = parser.parse_args(argv)

    config = load_config(args.config)
    return run(config, dry_run=args.dry_run, only=args.host, verbose=args.verbose)


if __name__ == "__main__":
    sys.exit(main())
