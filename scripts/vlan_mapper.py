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
        # clave por proposito (una key por item que consume el valor)
        "keys": {
            "vlan_map": "net.vlan.map",
            "ppp_count": "mikrotik.ppp.active.count",
            "ppp_map": "net.ppp.map",
            # hw (piloto 704): CPU/disco/RAM publicados por el mapper para no
            # caminar hrProcessorLoad/hrStorage desde Zabbix cada minuto.
            "hw_cpu": "system.hw.cpu.avg",
            "hw_disk": "system.hw.disk.pused",
            "hw_ram": "system.hw.ram.util",
            "if_map": "net.if.map",
        },
        "docker_binary": "docker",
        "use_docker": True,
        "container": "zabbix-server",
        "sender_binary": "zabbix_sender",
    },
    "ppp": {
        # Tabla de sesiones PPP (MikoTik): 1.3.6.1.4.1.14988.1.1.2.1.1.2
        "session_oid": "1.3.6.1.4.1.14988.1.1.2.1.1.2",
        # La whitelist de dedicados se LEE del template (fuente unica), por
        # psql read-only contra la base de Zabbix. Fallback opcional (regex)
        # por si el psql no es viable en el host donde corre el mapper.
        "whitelist_source": {
            "type": "db",
            "docker_binary": "docker",
            "container": "zabbix-postgres",
            "template_hostid": 10870,
            "macro": "{$PPP.DEDICATED.MATCHES}",
        },
        "whitelist_fallback": None,
        # Normalizacion opcional del nombre publicado: mapa valor->valor.
        # Los datos concretos de cada sitio van en su config (fuera de git).
        "name_normalizations": {},
    },
    "snmp": {
        "version": 2,
        "community": "public",
        "timeout": 15,
        "retries": 1,
        "oid": "1.3.6.1.2.1.2.2.1.2",
        "binary": "snmpwalk",
    },
    # hw (CPU/disco/RAM por trapper). Deshabilitado por defecto: se activa por
    # host con "hw": true en su entrada de "hosts" (o global con enabled).
    # OIDs de tablas CHICAS: hrProcessorLoad son las filas de nucleos (18 en
    # un CHR con 18 nucleos) y hrStorage es la tabla de discos; nada
    # comparable a la ifTable (~2.200 filas), o sea el costo marginal de la
    # corrida del cron es despreciable.
    "if_map": {
        "enabled": False,
        "macro": "{$NET.IF.IFDESCR.MATCHES}",
        "source": {
            "docker_binary": "docker",
            "container": "zabbix-postgres",
        },
    },
    "hw": {
        "enabled": False,
        "cpu_oid": "1.3.6.1.2.1.25.3.3.1.2",        # hrProcessorLoad (%)
        "storage_descr_oid": "1.3.6.1.2.1.25.2.3.1.3",  # hrStorageDescr
        "storage_size_oid": "1.3.6.1.2.1.25.2.3.1.5",   # hrStorageSize
        "storage_used_oid": "1.3.6.1.2.1.25.2.3.1.6",   # hrStorageUsed
        "ram_index": 65536,         # fila de RAM (main memory, convencion Mikrotik)
        "disk_index": 131072,       # fila del disco (system disk)
        # Las tablas de hw son chicas (18 filas + decenas): walk con timeout
        # corto para que un CHR caido no frene la corrida (el default del SNMP
        # general es 60 s, pensado para la ifTable pesada).
        "timeout": 10,
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


def filter_if_map(rows, regex):
    """Mapa de interfaces -> JSON [{index, ifdescr}] filtrado por la macro del host.

    El mapper NO decide que se monitorea: publica las filas que matchean la
    regex {$NET.IF.IFDESCR.MATCHES} leida por psql. Sin regex o regex invalida
    -> no publica (mismo guard que el resto).
    """
    if not regex:
        return []
    try:
        rx = re.compile(regex)
    except re.error:
        return []
    return [{"index": int(idx), "ifdescr": name} for idx, name in rows if rx.match(name)]


def build_payload(vlans):
    """JSON del master (contrato verificado en T1): array de objetos."""
    return json.dumps(vlans, separators=(",", ":"))


# --------------------------------------------------------------------------
# Publicacion
# --------------------------------------------------------------------------
def publish(zabbix_config, zabbix_host, key, payload):
    """Publica un valor con zabbix_sender. Devuelve (ok, salida)."""
    if zabbix_config.get("use_docker", True):
        command = [
            zabbix_config.get("docker_binary", "docker"),
            "exec",
            zabbix_config["container"],
            zabbix_config.get("sender_binary", "zabbix_sender"),
            "-z", str(zabbix_config["server"]),
            "-p", str(zabbix_config["port"]),
            "-s", zabbix_host,
            "-k", key,
            "-o", payload,
        ]
    else:
        command = [
            zabbix_config.get("sender_binary", "zabbix_sender"),
            "-z", str(zabbix_config["server"]),
            "-p", str(zabbix_config["port"]),
            "-s", zabbix_host,
            "-k", key,
            "-o", payload,
        ]
    result = subprocess.run(command, capture_output=True, text=True)
    output = (result.stdout.strip().splitlines() or [result.stderr.strip()])[-1]
    ok = result.returncode == 0 and "failed: 0" in result.stdout
    return ok, output


def key_for(zabbix_config, purpose):
    """Key de cada proposito (con fallback al key unico legacy)."""
    keys = zabbix_config.get("keys") or {}
    if purpose in keys:
        return keys[purpose]
    return zabbix_config.get("key", "net.vlan.map")


# --------------------------------------------------------------------------
# Flujo por host
# --------------------------------------------------------------------------
def count_ppp_sessions(rows):
    """Cantidad de sesiones PPP activas = filas de la tabla de sesiones.

    La tabla 1.3.6.1.4.1.14988.1.1.2.1.1.2 tiene UNA fila por sesion PPP
    (medido en los 5 CHR vivos: el 100 % de las filas son sesiones `<pppoe-`).
    El conteo NO pasa por el valor del item (que se trunca a 64 KB en el
    historial), asi que no arrastra el truncamiento.
    """
    return len(rows)


def filter_dedicated(rows, whitelist_regex):
    """Sesiones que matchean la whitelist de dedicados, con su indice de fila.

    El indice de fila (el sufijo del OID) es el que usan los prototipos
    1.3.6.1.4.1.14988.1.1.2.1.1.8.{#SNMPINDEX} / .9.{#SNMPINDEX}.
    """
    if not whitelist_regex:
        return []
    try:
        regex = re.compile(whitelist_regex)
    except re.error as exc:
        raise ValueError("whitelist de dedicados invalida (%s): %s" % (whitelist_regex, exc))
    dedicated = []
    for index, name in rows:
        if regex.match(name):
            dedicated.append({"ppp_name": name, "index": index})
    dedicated.sort(key=lambda entry: entry["index"])
    return dedicated


def read_whitelist_from_db(source):
    """Lee la macro de la whitelist desde la base de Zabbix (psql read-only).

    source = {"type":"db", "docker_binary":"docker", "container":"zabbix-postgres",
              "template_hostid":10870, "macro":"{$PPP.DEDICATED.MATCHES}"}
    Devuelve el valor de la macro (regex) o None si no se pudo leer.
    """
    if not source or source.get("type") != "db":
        return None
    sql = ("select value from hostmacro where hostid = %s and macro = '%s';"
           % (int(source["template_hostid"]), source["macro"]))
    command = [source.get("docker_binary", "docker"), "exec", "-i", source["container"],
               "psql", "-U", "zabbix", "-d", "zabbix", "-At", "-c", sql]
    try:
        result = subprocess.run(command, capture_output=True, text=True, timeout=30)
    except Exception as exc:  # sin docker/psql no se puede leer: no es fatal
        print("[ppp] no pude leer la whitelist por psql: %s" % exc)
        return None
    if result.returncode != 0:
        print("[ppp] no pude leer la whitelist por psql: %s" % result.stderr.strip())
        return None
    value = result.stdout.strip()
    return value or None


def read_host_macro(dbcfg, zabbix_host, macro):
    """Lee la macro de un HOST; si no tiene, cae a la macro del TEMPLATE.

    Orden: macro de host (override por nodo) -> macro de template (default
    unificado). Devuelve el valor o None.
    """
    if not dbcfg:
        return None
    sql = ("select hm.value from hostmacro hm join hosts h on h.hostid = hm.hostid "
           "where h.host = '%s' and hm.macro = '%s';" % (zabbix_host, macro))
    value = _psql_scalar(dbcfg, sql)
    if value is None and dbcfg.get("template_hostid"):
        value = _psql_scalar(dbcfg, "select value from hostmacro where hostid = %s and macro = '%s';"
                             % (int(dbcfg["template_hostid"]), macro))
        if value:
            print("[if_map] %s: sin macro propia, uso la del template" % zabbix_host)
    return value


def _psql_scalar(dbcfg, sql):
    """Corre un psql read-only de un solo valor. Devuelve str o None."""
    command = [dbcfg.get("docker_binary", "docker"), "exec", "-i", dbcfg.get("container", "zabbix-postgres"),
               "psql", "-U", "zabbix", "-d", "zabbix", "-At", "-c", sql]
    try:
        result = subprocess.run(command, capture_output=True, text=True, timeout=30)
    except Exception as exc:
        print("[if_map] no pude leer por psql: %s" % exc)
        return None
    if result.returncode != 0:
        return None
    return result.stdout.strip() or None


def _community(host_config, config):
    """Community SNMP explicito: por host o global. Nunca un default silencioso.

    Devolver "public" al faltar la config hacia que un error de configuracion
    se viera como un equipo caido (o, peor, funcionara contra un equipo con el
    community de fabrica). Si no esta en ninguno de los dos niveles, se corta
    nombrando el host: configurar el community es parte del alta del equipo.
    """
    value = host_config.get("community") or config.get("snmp", {}).get("community")
    if not value:
        raise SystemExit(
            "config invalida: falta 'community' para %s "
            "(definilo por host o en snmp.community)"
            % (host_config.get("ip") or host_config.get("zabbix_host") or "host desconocido")
        )
    return value


def collect_host(host_config, config, walker=run_snmpwalk, ppp_walker=run_snmpwalk):
    """Walk + filtro de un CHR.

    Devuelve (vlan_publicadas, filas, ppp, error) con filas = lista completa
      ppp = {"sessions": N, "dedicated": [{ppp_name, index}, ...]} o None si
            el walk de sesiones PPP fallo (o no hay whitelist).
    """
    snmp = config.get("snmp", {})
    vlan = config.get("vlan", {})
    ppp_cfg = config.get("ppp", {})
    community = _community(host_config, config)

    def walk(oid):
        return walker(
            host_config["ip"],
            community,
            oid,
            version=snmp.get("version", 2),
            timeout=snmp.get("timeout", 15),
            retries=snmp.get("retries", 1),
            binary=snmp.get("binary", "snmpwalk"),
        )

    try:
        raw = walk(snmp.get("oid", "1.3.6.1.2.1.2.2.1.2"))
    except Exception as exc:  # un CHR caido no debe tumbar al resto
        return [], [], None, str(exc)
    rows = parse_walk_output(raw, snmp.get("oid", "1.3.6.1.2.1.2.2.1.2"))
    vlans = filter_vlans(
        rows,
        pattern=vlan.get("pattern"),
        exclude_pattern=vlan.get("exclude_pattern"),
    )

    ppp = None
    if ppp_cfg.get("session_oid"):
        try:
            ppp_raw = ppp_walker(
                host_config["ip"],
                community,
                ppp_cfg["session_oid"],
                version=snmp.get("version", 2),
                timeout=snmp.get("timeout", 15),
                retries=snmp.get("retries", 1),
                binary=snmp.get("binary", "snmpwalk"),
            )
            ppp_rows = parse_walk_output(ppp_raw, ppp_cfg["session_oid"])
            if not ppp_rows:
                # Un CHR con servicio PPPoE activo nunca tiene 0 sesiones: un
                # walk vacio significa que el OID no esta disponible o que el
                # agente no respondio. No publicar 0 evita pisar el ultimo
                # valor bueno con un dato falso (visto en 703 el 2026-10-22).
                raise RuntimeError("el walk de sesiones PPP devolvio 0 filas (OID no disponible o agente sin respuesta)")
            dedicated = filter_dedicated(ppp_rows, ppp_cfg.get("whitelist"))
            normalizaciones = ppp_cfg.get("name_normalizations") or {}
            for entry in dedicated:
                entry["ppp_name"] = normalizaciones.get(entry["ppp_name"], entry["ppp_name"])
            ppp = {
                "sessions": count_ppp_sessions(ppp_rows),
                "dedicated": dedicated,
                "rows": ppp_rows,
            }
        except Exception as exc:
            # el lado PPP no debe tumbar al lado VLAN
            print("[ppp] %s: fallo el walk de sesiones PPP: %s" % (host_config.get("zabbix_host"), exc))
            ppp = None
    return vlans, rows, ppp, None


def collect_hw(host_config, config, hw_walker=run_snmpwalk):
    """Walks de CPU y storage (tablas chicas) -> tres escalares.

    Devuelve un dict con las metricas que se pudieron calcular:
      cpu_avg    = media de hrProcessorLoad (%)
      disk_pused = hrStorageUsed/hrStorageSize*100 de la fila del disco
      ram_util   = idem de la fila "Memory"

    Mismo guard que el PPP: cada walk fallido (excepcion o 0 filas) deja
    fuera SU metrica, sin pisa el resto ni el lado VLAN/PPP.
    """
    hw_cfg = config.get("hw", {})
    snmp = config.get("snmp", {})
    community = _community(host_config, config)
    name = host_config.get("zabbix_host")

    def walk(oid):
        return hw_walker(
            host_config["ip"], community, oid,
            version=snmp.get("version", 2),
            # timeout corto: tablas chicas, un CHR caido no debe frenar
            timeout=hw_cfg.get("timeout", 10),
            retries=snmp.get("retries", 1),
            binary=snmp.get("binary", "snmpwalk"),
        )

    hw = {}

    # CPU: media de los nucleos.
    try:
        cpu_oid = hw_cfg.get("cpu_oid", "1.3.6.1.2.1.25.3.3.1.2")
        loads = []
        for _index, value in parse_walk_output(walk(cpu_oid), cpu_oid):
            try:
                loads.append(int(value))
            except (TypeError, ValueError):
                continue
        if loads:
            hw["cpu_avg"] = round(sum(loads) / len(loads), 1)
        else:
            print("[hw] %s: el walk de CPU devolvio 0 filas -> no se publica" % name)
    except Exception as exc:
        print("[hw] %s: fallo el walk de CPU: %s" % (name, exc))

    # Storage: RAM y disco sobre las 3 columnas de hrStorage.
    try:
        descr_oid = hw_cfg.get("storage_descr_oid", "1.3.6.1.2.1.25.2.3.1.3")
        size_oid = hw_cfg.get("storage_size_oid", "1.3.6.1.2.1.25.2.3.1.5")
        used_oid = hw_cfg.get("storage_used_oid", "1.3.6.1.2.1.25.2.3.1.6")
        descr = dict(parse_walk_output(walk(descr_oid), descr_oid))
        size = {}
        for index, value in parse_walk_output(walk(size_oid), size_oid):
            try:
                size[index] = float(value)
            except (TypeError, ValueError):
                continue
        used = {}
        for index, value in parse_walk_output(walk(used_oid), used_oid):
            try:
                used[index] = float(value)
            except (TypeError, ValueError):
                continue

        def pused(index):
            if index in size and index in used and size[index] > 0:
                return round(used[index] / size[index] * 100, 1)
            return None

        for row_key, config_key in (("ram_index", "ram_util"),
                                    ("disk_index", "disk_pused")):
            index = int(hw_cfg.get(row_key, 65536 if row_key == "ram_index" else 131072))
            if index in descr:
                value = pused(index)
                if value is not None:
                    hw[config_key] = value
                else:
                    print("[hw] %s: la fila %s (%s) no tiene size/used -> no se publica"
                          % (name, row_key, index))
            else:
                print("[hw] %s: la fila %s (%s) no esta en el walk -> no se publica"
                      % (name, row_key, index))
    except Exception as exc:
        print("[hw] %s: fallo el walk de storage: %s" % (name, exc))

    return hw


def run(config, dry_run=False, only=None, walker=run_snmpwalk, ppp_walker=run_snmpwalk,
        hw_walker=run_snmpwalk, verbose=False, whitelist=None, hw_only=False):
    """Procesa todos los hosts. Devuelve el codigo de salida (0 = todo bien).

    hw_only: corrida SOLO de CPU/disco/RAM (tablas chicas, pensada para el
    cron de 1 min). No toca los walks pesados de ifTable ni la tabla PPP.
    """
    failures = 0
    zabbix_config = config.get("zabbix", {})
    for host in config.get("hosts", []):
        stamp = time.strftime("%Y-%m-%d %H:%M:%S")
        name = host.get("zabbix_host")
        if only and name != only:
            continue
        if not host.get("ip"):
            print("[%s] %s: sin IP configurada -> se saltea (completar la config)" % (stamp, name))
            failures += 1
            continue

        # en modo hw_only se saltea todo el lado VLAN/PPP
        vlans, rows, ppp, error = (0, 0, None, None) if hw_only else collect_host(
            host, config, walker=walker, ppp_walker=ppp_walker)
        stamp = time.strftime("%Y-%m-%d %H:%M:%S")
        if error:
            print("[%s] %s (%s): ERROR %s" % (stamp, name, host["ip"], error))
            failures += 1
            continue
        if hw_only:
            pass  # sin resumen de ifTable: esta corrida solo publica hw
        else:
            published = ", ".join(vlan["ifdescr"] for vlan in vlans) or "(ninguna)"
            print("[%s] %s (%s): %d filas de ifTable, %d VLANs publicadas: %s" % (
                stamp, name, host["ip"], len(rows), len(vlans), published))
            if verbose:
                print("[%s] %s: %s" % (stamp, name, build_payload(vlans)))
        if dry_run:
            continue

        # 1) mapa de VLANs (master de la LLD de VLANs)
        if not hw_only:
            if vlans:
                ok, output = publish(zabbix_config, name, key_for(zabbix_config, "vlan_map"),
                                     build_payload(vlans))
                if not ok:
                    print("[%s] %s: ERROR publicando el mapa de VLANs -> %s" % (stamp, name, output))
                    failures += 1
                else:
                    print("[%s] %s: mapa de VLANs publicado (%s)" % (stamp, name, output))
            else:
                print("[%s] %s: 0 VLANs -> no se publica (para no vaciar el LLD)" % (stamp, name))

        # 2) conteo de sesiones PPP + 3) mapa de dedicados
        if not hw_only and ppp:
            count_payload = str(ppp["sessions"])
            dedicated_payload = build_payload(ppp["dedicated"])
            print("[%s] %s: %d sesiones PPP, %d dedicadas (%s)" % (
                stamp, name, ppp["sessions"], len(ppp["dedicated"]),
                ", ".join("%s@%d" % (d["ppp_name"], d["index"]) for d in ppp["dedicated"]) or "ninguna"))
            ok, output = publish(zabbix_config, name, key_for(zabbix_config, "ppp_count"), count_payload)
            if not ok:
                print("[%s] %s: ERROR publicando el conteo PPP -> %s" % (stamp, name, output))
                failures += 1
            else:
                print("[%s] %s: conteo PPP publicado (%s)" % (stamp, name, output))
            ok, output = publish(zabbix_config, name, key_for(zabbix_config, "ppp_map"), dedicated_payload)
            if not ok:
                print("[%s] %s: ERROR publicando el mapa de dedicados -> %s" % (stamp, name, output))
                failures += 1
            else:
                print("[%s] %s: mapa de dedicados publicado (%s)" % (stamp, name, output))

        # 3b) mapa de interfaces (para la LLD trapper de interfaces)
        #     En hw_only `rows` es 0 (no se camina la ifTable): este bloque
        #     debe saltarse, igual que VLAN/PPP.
        if_map_cfg = config.get("if_map", {})
        if not hw_only and if_map_cfg.get("enabled"):
            regex = read_host_macro(if_map_cfg.get("source"), name,
                                    if_map_cfg.get("macro", "{$NET.IF.IFDESCR.MATCHES}"))
            if_map = filter_if_map(rows, regex)
            if if_map:
                ok, output = publish(zabbix_config, name, key_for(zabbix_config, "if_map"),
                                     build_payload(if_map))
                if not ok:
                    print("[%s] %s: ERROR publicando el mapa de interfaces -> %s" % (stamp, name, output))
                    failures += 1
                else:
                    print("[%s] %s: mapa de interfaces publicado (%d interfaces)" % (stamp, name, len(if_map)))
            else:
                print("[%s] %s: mapa de interfaces vacio -> no se publica" % (stamp, name))

        # 4) CPU / disco / RAM por trapper (solo hosts con "hw": true)
        hw_enabled = host.get("hw")
        if hw_enabled is None:
            hw_enabled = bool(config.get("hw", {}).get("enabled", False))
        if hw_enabled:
            try:
                hw = collect_hw(host, config, hw_walker=hw_walker)
            except Exception as exc:  # el lado hw no debe tumbar VLAN/PPP
                print("[hw] %s: fallo colectando hw: %s" % (name, exc))
                hw = {}
            for purpose, value_key in (("hw_cpu", "cpu_avg"),
                                       ("hw_disk", "disk_pused"),
                                       ("hw_ram", "ram_util")):
                if value_key not in hw:
                    continue
                ok, output = publish(zabbix_config, name, key_for(zabbix_config, purpose),
                                     str(hw[value_key]))
                if not ok:
                    print("[%s] %s: ERROR publicando %s -> %s" % (stamp, name, value_key, output))
                    failures += 1
                else:
                    print("[%s] %s: %s publicado (%s)" % (stamp, name, value_key, output))
    return 1 if failures else 0


def resolve_whitelist(config, whitelist=None):
    """Whitelist de PPP dedicados: la del TEMPLATE (fuente unica).

    Orden de precedencia:
      1. la que se pasa por parametro (tests / dry-run manual)
      2. la leida por psql de la macro del template (fuente unica en prod)
      3. el fallback de la config (si el psql no es viable)
      4. None -> no se publica el mapa de dedicados (el conteo si se publica)
    """
    if whitelist:
        return whitelist
    ppp_cfg = config.get("ppp", {})
    if ppp_cfg.get("whitelist") is not None:
        return ppp_cfg["whitelist"]
    value = read_whitelist_from_db(ppp_cfg.get("whitelist_source"))
    if value:
        return value
    return ppp_cfg.get("whitelist_fallback")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--config", help="archivo de configuracion (JSON o YAML)")
    parser.add_argument("--dry-run", action="store_true", help="imprime el JSON y no publica")
    parser.add_argument("--host", help="procesa solo ese host (nombre Zabbix)")
    parser.add_argument("--verbose", action="store_true", help="detalle por host")
    parser.add_argument("--whitelist", help="regex de dedicados (override; por defecto se lee del template)")
    parser.add_argument("--hw-only", action="store_true",
                        help="solo CPU/disco/RAM (tablas chicas; para el cron de 1 min)")
    args = parser.parse_args(argv)

    config = load_config(args.config)
    whitelist = resolve_whitelist(config, args.whitelist)
    if whitelist:
        print("[ppp] whitelist de dedicados: %s" % whitelist[:120])
    else:
        print("[ppp] sin whitelist de dedicados: se publica el conteo pero no el mapa")
    config.setdefault("ppp", {})["whitelist"] = whitelist
    return run(config, dry_run=args.dry_run, only=args.host, verbose=args.verbose,
               hw_only=args.hw_only)


if __name__ == "__main__":
    sys.exit(main())
