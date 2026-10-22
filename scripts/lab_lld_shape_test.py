#!/usr/bin/env python3
"""T1 — contrato verificado de la LLD de VLANs con master trapper (Zabbix 7.4).

Alcance: SOLO el lab local (Zabbix 7.4.13 en http://127.0.0.1/api_jsonrpc.php).
Este script NO toca site-a ni ningun sistema en produccion.

Que verifica (y por que importa)
---------------------------------
La LLD de produccion `net.vlan.discovery` usa como master un item SNMP
`net.vlan.walk` (walk de 4 columnas de la ifTable). En los CHR de site-a la
ifTable tiene 2.190 filas, un walk de UNA columna son 118.784 bytes y el valor
de un item Zabbix se corta a 65.535 bytes -> el master devuelve texto
truncado -> el motor LLD parsea un subconjunto arbitrario y descubre 2 de 8
VLANs.

La opcion B reemplaza el master por un item TRAPPER (tipo 2 en 7.4) alimentado
por un script que publica un JSON chico y exacto. Al cambiar el master a un
item que no es SNMP, las macros `{#IFDESCR}`, `{#IFNAME}` y `{#SNMPINDEX}`
dejan de autogenerarse: hay que declararlas explicitamente.

Este script determina empiricamente (iterando sobre candidatos y mirando lo
que el motor LLD acepta de verdad):

  1. La forma del JSON que el motor parsea.
  2. La sintaxis de los macro paths para un master no-SNMP.
  3. Como se declaran las macros (API `lld_macro_paths` vs. tabla
     `lld_macro_path` de la base).
  4. Que los items descubiertos tienen el key y el OID esperados Y reciben
     datos (para eso levanta un respondedor SNMP minimo dentro del container
     `zabbix-server`, que solo existe en el lab).

CONTRATO VERIFICADO (Zabbix 7.4.13)
-----------------------------------
  JSON (valor del master trapper):  array de objetos, un objeto por VLAN
      [{"ifdescr":"vlan175","ifname":"vlan175","index":102}, ...]

  Macro paths (declarados con `lld_macro_paths` en discoveryRule.create/update):
      {#IFDESCR}   -> $.ifdescr
      {#IFNAME}    -> $.ifname
      {#SNMPINDEX} -> $.index

  NO funcionan (verificado en este lab): `$.[0].ifdescr`, `$.[*].ifdescr`,
  un JSON que sea un objeto en vez de un array, y una regla sin
  `lld_macro_paths` (esa ultima descubre NADA y sin error en el log).

  Calls de API exactas (ver `ensure_*` mas abajo, que son las que se ejecutan):
      item.create          type 2 (Zabbix trapper), value_type 4 (text), delay 0
      discoveryRule.create type 18 (dependent), delay 0, master_itemid=<master>
                          lld_macro_paths=[{lld_macro, path}, ...]
      itemPrototype.create type 20 (SNMP agent), interfaceid=<id de la
                          interfaz SNMP del host>, snmp_oid con {#SNMPINDEX}

  Nota 7.4: `discoveryRule.create` NO acepta `item_prototypes` (los prototipos
  se crean con `itemPrototype.create`) y NO acepta `macros` (las macros de LLD
  van en `lld_macro_paths`, con claves `lld_macro` y `path`).

Ejecucion:  python3 scripts/lab_lld_shape_test.py
Salida:     exit 0 si el contrato canonico quedo verificado.

Nota: el respondedor SNMP minimo se levanta y se baja solo (dentro del
container `zabbix-server`). Al terminar, los items del host de prueba quedan
sin SNMP: es esperado, es un banco de pruebas.
Para borrar el host de prueba del lab:
    host.delete {"hostids": ["<hostid del host vlan-lld-shape-lab>"]}
(cuidado: eso borra items, rules y prototipos del host, no el grupo)
"""

import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request

# --------------------------------------------------------------------------
# Configuracion (todo parametrizable por entorno; defaults = lab local)
# --------------------------------------------------------------------------
API_URL = os.getenv("ZBX_API_URL", "http://127.0.0.1/api_jsonrpc.php")
API_USER = os.getenv("ZBX_API_USER", "Admin")
API_PASSWORD = os.getenv("ZBX_API_PASSWORD", "zabbix")

LAB_HOST_NAME = os.getenv("T1_LAB_HOST", "vlan-lld-shape-lab")
LAB_GROUP_NAME = os.getenv("T1_LAB_GROUP", "Lab LLD Shape")

SENDER_CONTAINER = os.getenv("T1_SENDER_CONTAINER", "zabbix-server")
SENDER_SERVER = os.getenv("T1_SENDER_SERVER", "127.0.0.1")
SENDER_PORT = os.getenv("T1_SENDER_PORT", "10051")

SNMP_PORT = int(os.getenv("T1_SNMP_PORT", "1161"))
SNMP_COMMUNITY = os.getenv("T1_SNMP_COMMUNITY", "public")

# Payload canonico: las 8 VLANs de 703 con su ifIndex (hechos verificados).
CANONICAL_VLANS = [
    ("vlan250", 98),
    ("vlan301", 99),
    ("vlan305", 100),
    ("vlan175", 102),
    ("vlan190", 103),
    ("vlan220", 104),
    ("vlan225", 105),
    ("vlan235", 106),
]

IN_OID = "1.3.6.1.2.1.31.1.1.1.6.{#SNMPINDEX}"
OUT_OID = "1.3.6.1.2.1.31.1.1.1.10.{#SNMPINDEX}"

MINI_SNMP_MARKER = "VLAB_LLD_MINI_SNMP"


# --------------------------------------------------------------------------
# Cliente JSON-RPC
# --------------------------------------------------------------------------
class ApiError(RuntimeError):
    pass


def api_call(method, params, token=None, request_id=1):
    payload = {"jsonrpc": "2.0", "method": method, "params": params, "id": request_id}
    request = urllib.request.Request(
        API_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json-rpc"},
    )
    if token:
        request.add_header("Authorization", "Bearer " + token)
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            body = json.loads(response.read().decode("utf-8"))
    except urllib.error.URLError as exc:
        raise ApiError("no se pudo contactar la API %s: %s" % (API_URL, exc))
    if "error" in body:
        raise ApiError("%s -> %s" % (method, body["error"]))
    return body["result"]


def login():
    token = api_call("user.login", {"username": API_USER, "password": API_PASSWORD})
    print("[api] user.login ok (%s)" % API_USER)
    return token


# --------------------------------------------------------------------------
# Respondedor SNMP minimo (solo lab): responde GET con Counter64 en
# 1.3.6.1.2.1.31.1.1.1.6.<idx> y .10.<idx> -> <idx>*1000+7.
# Vive dentro del container zabbix-server (127.0.0.1:<SNMP_PORT>).
# --------------------------------------------------------------------------
MINI_SNMP_SOURCE = r'''
# VLAB_LLD_MINI_SNMP - respondedor SNMPv2c minimo para el lab.
import socket

def enc_len(n):
    if n < 0x80:
        return bytes([n])
    raw = n.to_bytes((n.bit_length() + 7) // 8, "big")
    return bytes([0x80 | len(raw)]) + raw

def tlv(tag, payload):
    return bytes([tag]) + enc_len(len(payload)) + payload

def enc_int(n):
    return tlv(0x02, n.to_bytes((n.bit_length() // 8) + 1, "big", signed=True))

def enc_oid(oid):
    parts = [int(x) for x in oid.strip(".").split(".")]
    body = bytes([parts[0] * 40 + parts[1]])
    for part in parts[2:]:
        if part < 0x80:
            body += bytes([part])
        else:
            stack = []
            while part:
                stack.insert(0, part & 0x7F)
                part >>= 7
            for i in range(len(stack) - 1):
                stack[i] |= 0x80
            body += bytes(stack)
    return tlv(0x06, body)

def enc_counter64(value):
    return tlv(0x46, int(value).to_bytes(8, "big"))

def parse_tlv(buf, pos):
    tag = buf[pos]
    pos += 1
    length = buf[pos]
    pos += 1
    if length & 0x80:
        count = length & 0x7F
        length = int.from_bytes(buf[pos:pos + count], "big")
        pos += count
    return tag, buf[pos:pos + length], pos + length

def dec_oid(body):
    first = body[0]
    parts = [first // 40, first % 40] if first < 80 else [2, first - 80]
    value = 0
    for byte in body[1:]:
        value = (value << 7) | (byte & 0x7F)
        if not byte & 0x80:
            parts.append(value)
            value = 0
    return ".".join(str(part) for part in parts)

def value_for(oid):
    if oid.startswith("1.3.6.1.2.1.31.1.1.1.6.") or oid.startswith("1.3.6.1.2.1.31.1.1.1.10."):
        try:
            index = int(oid.rsplit(".", 1)[1])
        except ValueError:
            return tlv(0x80, b"")
        return enc_counter64(index * 1000 + 7)
    return tlv(0x80, b"")

def handle(data):
    _, seq, _ = parse_tlv(data, 0)
    _, _, pos = parse_tlv(seq, 0)
    _, community, pos = parse_tlv(seq, pos)
    _, pdu, _ = parse_tlv(seq, pos)
    _, request_id_raw, pos = parse_tlv(pdu, 0)
    request_id = int.from_bytes(request_id_raw, "big", signed=True) if request_id_raw else 0
    _, _, pos = parse_tlv(pdu, pos)
    _, _, pos = parse_tlv(pdu, pos)
    _, varbinds, _ = parse_tlv(pdu, pos)
    out = b""
    pos = 0
    while pos < len(varbinds):
        _, varbind, pos = parse_tlv(varbinds, pos)
        _, oid_raw, _ = parse_tlv(varbind, 0)
        oid = dec_oid(oid_raw)
        out += tlv(0x30, enc_oid(oid) + value_for(oid))
    response = tlv(0xA2, enc_int(request_id) + enc_int(0) + enc_int(0) + tlv(0x30, out))
    return tlv(0x30, enc_int(1) + tlv(0x04, community) + response)

def serve(port, host):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind((host, port))
    print("mini snmp responder listening on %s:%d" % (host, port), flush=True)
    while True:
        data, addr = sock.recvfrom(65535)
        try:
            sock.sendto(handle(data), addr)
        except Exception:
            pass

if __name__ == "__main__":
    serve(int(__import__("os").environ.get("T1_SNMP_PORT", "1161")), "127.0.0.1")
'''


def docker(*args, check=True):
    result = subprocess.run(["docker"] + list(args), capture_output=True, text=True)
    if check and result.returncode != 0:
        raise RuntimeError("docker %s fallo: %s" % (" ".join(args), result.stderr.strip()))
    return result


def stop_mini_snmp():
    """Mata el respondedor de una corrida anterior (idempotencia)."""
    docker("exec", SENDER_CONTAINER, "pkill", "-f", MINI_SNMP_MARKER, check=False)


def start_mini_snmp():
    """Levanta el respondedor SNMP minimo dentro del container del lab."""
    stop_mini_snmp()
    time.sleep(0.5)
    docker("exec", "-d", SENDER_CONTAINER, "python3", "-c", MINI_SNMP_SOURCE)
    deadline = time.time() + 15
    while time.time() < deadline:
        probe = docker(
            "exec", SENDER_CONTAINER, "python3", "-c",
            "import socket;s=socket.socket(socket.AF_INET,socket.SOCK_DGRAM);"
            "s.connect(('127.0.0.1',%d));s.send(b'\\x30\\x00');print('up')" % SNMP_PORT,
            check=False,
        )
        if probe.returncode == 0:
            print("[snmp] respondedor minimo escuchando en 127.0.0.1:%d (container %s)"
                  % (SNMP_PORT, SENDER_CONTAINER))
            return
        time.sleep(1)
    raise RuntimeError("el respondedor SNMP minimo no arranco en el container %s" % SENDER_CONTAINER)


# --------------------------------------------------------------------------
# Helpers de configuracion (todo idempotente: reutiliza lo que ya existe)
# --------------------------------------------------------------------------
def ensure_group(token):
    groups = api_call("hostgroup.get", {"filter": {"name": LAB_GROUP_NAME}}, token)
    if groups:
        return groups[0]["groupid"]
    created = api_call("hostgroup.create", {"name": LAB_GROUP_NAME}, token)
    print("[api] hostgroup.create %s -> %s" % (LAB_GROUP_NAME, created["groupids"]))
    return created["groupids"][0]


def ensure_host(token, group_id):
    hosts = api_call("host.get", {"filter": {"host": LAB_HOST_NAME}}, token)
    if hosts:
        return hosts[0]["hostid"]
    created = api_call(
        "host.create",
        {"host": LAB_HOST_NAME, "name": "VLAN LLD Shape Lab", "groups": [{"groupid": group_id}]},
        token,
    )
    print("[api] host.create %s -> %s" % (LAB_HOST_NAME, created["hostids"]))
    return created["hostids"][0]


def ensure_snmp_interface(token, host_id):
    """Interfaz SNMP del host de prueba (127.0.0.1:<puerto> del lab)."""
    interfaces = api_call(
        "hostinterface.get",
        {"hostids": [host_id], "filter": {"type": "2"}, "output": ["interfaceid", "ip", "port"]},
        token,
    )
    for interface in interfaces:
        if interface["ip"] == "127.0.0.1" and interface["port"] == str(SNMP_PORT):
            return interface["interfaceid"]
    created = api_call(
        "hostinterface.create",
        {
            "hostid": host_id,
            "type": 2,
            "main": 1,
            "useip": 1,
            "ip": "127.0.0.1",
            "dns": "",
            "port": str(SNMP_PORT),
            "details": {"version": 2, "community": SNMP_COMMUNITY},
        },
        token,
    )
    print("[api] hostinterface.create (SNMP 127.0.0.1:%d) -> %s" % (SNMP_PORT, created["interfaceids"]))
    return created["interfaceids"][0]


def ensure_master_item(token, host_id, key, description):
    """Item TRAPPER (tipo 2 en 7.4) que hace de master de la LLD."""
    items = api_call(
        "item.get",
        {"hostids": [host_id], "filter": {"key_": key}, "output": ["itemid", "key_"]},
        token,
    )
    if items:
        return items[0]["itemid"]
    created = api_call(
        "item.create",
        {
            "hostid": host_id,
            "name": description,
            "key_": key,
            "type": 2,          # 2 = Zabbix trapper en 7.4
            "value_type": 4,    # texto
            "delay": "0",
            "history": "1h",
            "trends": "0",
            "description": description,
        },
        token,
    )
    print("[api] item.create (trapper master %s) -> %s" % (key, created["itemids"]))
    return created["itemids"][0]


def ensure_rule(token, host_id, key, master_id, macro_paths, discovery_filter=None):
    """Regla LLD dependiente (tipo 18) con macro paths explicitos."""
    rules = api_call(
        "discoveryRule.get",
        {"hostids": [host_id], "filter": {"key_": key}, "output": ["itemid", "key_"]},
        token,
    )
    payload = {
        "type": 18,          # 18 = dependent (la cadencia la hereda del master)
        "delay": "0",        # una regla dependiente exige delay 0
        "master_itemid": master_id,
        "lld_macro_paths": [{"lld_macro": macro, "path": path} for macro, path in macro_paths],
    }
    if discovery_filter is not None:
        payload["filter"] = discovery_filter

    if rules:
        rule_id = rules[0]["itemid"]
        if not macro_paths:
            # Una regla sin macros no se puede "dejar vacia" con update:
            # se borra y se vuelve a crear (asi el caso negativo es real).
            api_call("discoveryRule.delete", [rule_id], token)
            print("[api] discoveryRule.delete %s (se recrea sin macros)" % key)
        else:
            api_call("discoveryRule.update", dict(payload, itemid=rule_id), token)
            return rule_id
    created = api_call(
        "discoveryRule.create",
        dict(payload, hostid=host_id, name="T1 %s" % key, key_=key),
        token,
    )
    print("[api] discoveryRule.create %s -> %s" % (key, created["itemids"]))
    return created["itemids"][0]


def ensure_prototype(token, host_id, rule_id, key, snmp_oid, interface_id, direction):
    """Prototipo de item SNMP (tipo 20) que hereda las macros de la LLD."""
    prototypes = api_call(
        "itemPrototype.get",
        {"hostids": [host_id], "filter": {"key_": key}, "output": ["itemid", "key_"]},
        token,
    )
    if prototypes:
        api_call(
            "itemPrototype.update",
            {"itemid": prototypes[0]["itemid"], "interfaceid": interface_id},
            token,
        )
        return prototypes[0]["itemid"]
    created = api_call(
        "itemPrototype.create",
        {
            "hostid": host_id,
            "ruleid": rule_id,
            "name": "VLAN {#IFDESCR}: %s" % direction,
            "type": 20,           # SNMP agent
            "key_": key,
            "snmp_oid": snmp_oid,
            "interfaceid": interface_id,
            "value_type": 3,      # numeric unsigned
            "delay": "30s",
            "history": "1h",
            "trends": "0",
        },
        token,
    )
    print("[api] itemPrototype.create %s -> %s" % (key, created["itemids"]))
    return created["itemids"][0]


def publish(host_name, key, payload, attempts=8, delay=3):
    """Publica el JSON del master con zabbix_sender (dentro del container).

    Reintenta: un item recien creado todavia puede no estar en la cache de
    configuracion del server, y el trapper rechaza el valor hasta que lo esta.
    """
    last_output = ""
    for attempt in range(1, attempts + 1):
        result = docker(
            "exec", SENDER_CONTAINER, "zabbix_sender",
            "-z", SENDER_SERVER, "-p", SENDER_PORT,
            "-s", host_name, "-k", key, "-o", payload,
            check=False,
        )
        last_output = result.stdout.strip()
        if result.returncode == 0 and "failed: 0" in last_output and "sent: 1" in last_output:
            return last_output
        time.sleep(delay)
    raise RuntimeError("zabbix_sender no pudo publicar %s: %s" % (key, last_output))


def reload_config_cache():
    """Fuerza al server a releer la configuracion (items/reglas recien creados)."""
    docker("exec", SENDER_CONTAINER, "zabbix_server", "-R", "config_cache_reload", check=False)


def master_value(token, host_id, key):
    """Ultimo valor recibido por el master (prueba de que el dato llego)."""
    items = api_call(
        "item.get",
        {"hostids": [host_id], "filter": {"key_": key}, "output": ["itemid", "lastvalue", "lastclock"]},
        token,
    )
    if not items:
        return None
    return items[0]["lastvalue"]


def wait_for_items(token, host_id, key_prefix, expected_count=8, timeout=90):
    """Espera a que la LLD cree los items cuyo key empieza por `key_prefix`.

    `expected_count` = 0 significa "esperar el timeout completo y ver si
    aparecio ALGO" (se usa para los casos negativos).
    """
    deadline = time.time() + timeout
    items = []
    while True:
        raw = api_call(
            "item.get",
            {
                "hostids": [host_id],
                "search": {"key_": key_prefix},
                "output": ["itemid", "key_", "snmp_oid", "name", "lastvalue", "lastclock",
                           "state", "flags"],
            },
            token,
        )
        # flags 4 = descubierto por LLD (2 = prototipo, 0 = item normal)
        items = [item for item in raw if item.get("flags") == "4"]
        if expected_count and len(items) >= expected_count:
            return items
        if time.time() >= deadline:
            return items
        time.sleep(3)


def purge_discovered(token, host_id, key_prefix):
    """Borra los items YA descubiertos de un caso (flags=4) para que el conteo
    post-discovery sea significativo (idempotencia del test)."""
    items = api_call(
        "item.get",
        {"hostids": [host_id], "search": {"key_": key_prefix}, "output": ["itemid", "flags"]},
        token,
    )
    discovered = [item["itemid"] for item in items if item.get("flags") == "4"]
    if discovered:
        api_call("item.delete", discovered, token)
        print("[api] item.delete %d items descubiertos de %s" % (len(discovered), key_prefix))
    return len(discovered)


def wait_for_value(token, item_ids, timeout=120):
    """Espera a que los items descubiertos tengan un valor collected."""
    def read():
        return api_call(
            "item.get",
            {
                "itemids": item_ids,
                "output": ["itemid", "key_", "snmp_oid", "lastvalue", "lastclock", "state"],
            },
            token,
        )

    deadline = time.time() + timeout
    items = read()
    while time.time() < deadline:
        if items and all(item["lastclock"] != "0" and item["lastvalue"] not in ("", None)
                          for item in items):
            return items
        time.sleep(5)
        items = read()
    return items


def history_values(token, item_ids, limit=3):
    if not item_ids:
        return []
    return api_call(
        "history.get",
        {
            "itemids": item_ids,
            "history": 3,
            "output": ["itemid", "value", "clock"],
            "sortfield": "clock",
            "sortorder": "DESC",
            "limit": limit * len(item_ids),
        },
        token,
    )


# --------------------------------------------------------------------------
# Casos a probar
# --------------------------------------------------------------------------
def canonical_entries(extra_pppoe=0):
    entries = [
        {"ifdescr": name, "ifname": name, "index": index}
        for name, index in CANONICAL_VLANS
    ]
    for i in range(extra_pppoe):
        entries.append({
            "ifdescr": "pppoe-cliente%d" % i,
            "ifname": "pppoe-cliente%d" % i,
            "index": 15738670 + i,
        })
    return entries


def canonical_payload(extra_pppoe=0):
    """JSON canonico. El orden se rota para que el valor cambie entre corridas
    (el motor LLD solo rediscovering cuando el valor del master cambia) sin
    alterar el contenido."""
    entries = canonical_entries(extra_pppoe)
    rotation = int(time.time()) % max(len(entries), 1)
    entries = entries[rotation:] + entries[:rotation]
    return json.dumps(entries, separators=(",", ":"))


CASES = [
    {
        "id": "canonical",
        "title": "array de objetos + macro paths '$.<campo>'",
        "paths": [("{#IFDESCR}", "$.ifdescr"), ("{#IFNAME}", "$.ifname"), ("{#SNMPINDEX}", "$.index")],
        "payload": canonical_payload(),
        "expect": "discover",
    },
    {
        "id": "index0",
        "title": "macro paths '$.[0].<campo>'",
        "paths": [("{#IFDESCR}", "$.[0].ifdescr"), ("{#IFNAME}", "$.[0].ifname"), ("{#SNMPINDEX}", "$.[0].index")],
        "payload": canonical_payload(),
        "expect": "no-discover",
    },
    {
        "id": "star",
        "title": "macro paths '$.[*].<campo>'",
        "paths": [("{#IFDESCR}", "$.[*].ifdescr"), ("{#IFNAME}", "$.[*].ifname"), ("{#SNMPINDEX}", "$.[*].index")],
        "payload": canonical_payload(),
        "expect": "no-discover",
    },
    {
        "id": "object",
        "title": "JSON con objeto en vez de array",
        "paths": [("{#IFDESCR}", "$.ifdescr"), ("{#IFNAME}", "$.ifname"), ("{#SNMPINDEX}", "$.index")],
        "payload": json.dumps({"vlans": canonical_entries()}, separators=(",", ":")),
        "expect": "no-discover",
    },
    {
        "id": "nomacros",
        "title": "sin lld_macro_paths (macros no declaradas)",
        "paths": [],
        "payload": canonical_payload(),
        "expect": "no-discover",
    },
    {
        "id": "nomacro",
        "title": "array de objetos + filtro LLD sobre una macro INEXISTENTE",
        "paths": [("{#IFDESCR}", "$.ifdescr"), ("{#IFNAME}", "$.ifname"), ("{#SNMPINDEX}", "$.index")],
        "payload": canonical_payload(extra_pppoe=3),
        "discovery_filter": {
            "evaltype": 0,  # AND
            "conditions": [
                {"macro": "{#IFDESCR}", "operator": 8, "value": "{$T1.MACRO.INEXISTENTE}"},
            ],
        },
        "expect": "no-discover",
        "note": "macro del filtro que no esta definida en ningun lado: que hace el motor?",
    },
    {
        "id": "filter",
        "title": "array de objetos + filtro LLD sobre {#IFDESCR} (excluye pppoe)",
        "paths": [("{#IFDESCR}", "$.ifdescr"), ("{#IFNAME}", "$.ifname"), ("{#SNMPINDEX}", "$.index")],
        "payload": canonical_payload(extra_pppoe=3),
        "discovery_filter": {
            "evaltype": 0,  # AND
            "conditions": [
                {"macro": "{#IFDESCR}", "operator": 8, "value": "^vlan"},    # 8 = matches regex
                {"macro": "{#IFDESCR}", "operator": 9, "value": "^pppoe-"},  # 9 = does not match regex
            ],
        },
        "expect": "discover",
        "expect_count": 8,
    },
]


def run_case(token, host_id, interface_id, case):
    case_id = case["id"]
    master_key = "t1.master.%s" % case_id
    rule_key = "t1.rule.%s" % case_id
    proto_in = "net.vlan.t1%s.in[ifHCInOctets.{#SNMPINDEX}]" % case_id
    proto_out = "net.vlan.t1%s.out[ifHCOutOctets.{#SNMPINDEX}]" % case_id

    master_id = ensure_master_item(token, host_id, master_key, "T1 master trapper %s" % case_id)
    rule_id = ensure_rule(
        token, host_id, rule_key, master_id, case["paths"], case.get("discovery_filter")
    )
    ensure_prototype(token, host_id, rule_id, proto_in, IN_OID, interface_id, "in")
    ensure_prototype(token, host_id, rule_id, proto_out, OUT_OID, interface_id, "out")
    reload_config_cache()

    # Purga lo descubierto en corridas anteriores: el conteo post-discovery
    # tiene que ser el de ESTA corrida.
    purge_discovered(token, host_id, "net.vlan.t1%s." % case_id)

    # Publica el JSON candidato (el valor cambio => el motor LLD rediscover).
    payload = case["payload"]
    publish(LAB_HOST_NAME, master_key, payload)
    received = master_value(token, host_id, master_key)
    if received is None:
        raise RuntimeError("el master %s no registro el valor publicado" % master_key)

    expected_prefix = "net.vlan.t1%s.in[ifHCInOctets." % case_id
    if case["expect"] == "discover":
        items = wait_for_items(token, host_id, expected_prefix,
                               expected_count=case.get("expect_count", 8), timeout=120)
    else:
        items = wait_for_items(token, host_id, expected_prefix, expected_count=0, timeout=45)
    result = {
        "id": case_id,
        "title": case["title"],
        "expect": case["expect"],
        "items": items,
        "ok": False,
        "detail": "",
    }
    if items:
        items = sorted(items, key=lambda item: item["key_"])
        result["ok"] = case["expect"] == "discover"
        result["detail"] = "descubiertos %d items (ej. %s / %s)" % (
            len(items), items[0]["key_"], items[0]["snmp_oid"])
    else:
        result["ok"] = case["expect"] == "no-discover"
        result["detail"] = "ningun item descubierto (las macros no resolvieron)"
    return result


def run_integration(token, host_id, interface_id):
    """Integracion con los nombres que se usaran en produccion.

    item trapper `net.vlan.map` + regla `net.vlan.discovery` + prototipos
    `net.vlan.in/out[ifHC{In,Out}Octets.{#SNMPINDEX}]` -> 8 items descubiertos
    con el OID correcto y con dato.
    """
    master_id = ensure_master_item(token, host_id, "net.vlan.map",
                                   "VLAN map (trapper) - master de la LLD de VLANs")
    rule_id = ensure_rule(
        token, host_id, "net.vlan.discovery", master_id,
        [("{#IFDESCR}", "$.ifdescr"), ("{#IFNAME}", "$.ifname"), ("{#SNMPINDEX}", "$.index")],
    )
    ensure_prototype(token, host_id, rule_id, "net.vlan.in[ifHCInOctets.{#SNMPINDEX}]",
                     IN_OID, interface_id, "in")
    ensure_prototype(token, host_id, rule_id, "net.vlan.out[ifHCOutOctets.{#SNMPINDEX}]",
                     OUT_OID, interface_id, "out")
    reload_config_cache()
    purge_discovered(token, host_id, "net.vlan.in[ifHCInOctets.")

    publish(LAB_HOST_NAME, "net.vlan.map", canonical_payload())
    items = wait_for_items(token, host_id, "net.vlan.in[ifHCInOctets.", expected_count=8, timeout=120)
    result = {"id": "integracion", "title": "net.vlan.map + net.vlan.discovery (nombres de produccion)",
              "expect": "discover", "items": items, "ok": bool(items), "detail": ""}
    if items:
        discovered = {item["key_"]: item.get("snmp_oid", "") for item in items}
        missing = []
        for _name, index in CANONICAL_VLANS:
            key = "net.vlan.in[ifHCInOctets.%d]" % index
            oid = "1.3.6.1.2.1.31.1.1.1.6.%d" % index
            if discovered.get(key) != oid:
                missing.append(key)
        result["ok"] = not missing
        result["detail"] = "descubiertos %d items con los keys y OIDs de produccion" % len(items)
        if missing:
            result["detail"] += " (faltan: %s)" % ", ".join(missing)
    else:
        result["detail"] = "no seelio ningun item descubierto"
    return result


CONTRACT_TEXT = """
| JSON del master (valor del item trapper tipo 2):
    [ {"ifdescr":"vlan175","ifname":"vlan175","index":102}, ... ]
    (array de objetos; un objeto por VLAN; "index" es el ifIndex)

| Macro paths (lld_macro_paths de discoveryRule.create/update):
    {#IFDESCR}   -> $.ifdescr
    {#IFNAME}    -> $.ifname
    {#SNMPINDEX} -> $.index

| NO funciona (verificado en este lab):
    '$.[0].<campo>', '$.[*].<campo>', un JSON con objeto en vez de array,
    y una regla sin lld_macro_paths (descubre NADA y no deja error en el log).

| Calls de API exactas:
    item.create          {hostid, key_, type:2, value_type:4, delay:"0"}
    discoveryRule.create {hostid, key_, type:18, delay:"0", master_itemid,
                          lld_macro_paths:[{lld_macro,path}]}
    itemPrototype.create {hostid, ruleid, type:20, key_, snmp_oid, interfaceid}

| Publicacion:
    docker exec <container> zabbix_sender -z <server> -p <port> -s <zabbix-host> -k net.vlan.map -o '<json>'
"""


def main():
    print("=" * 78)
    print("T1 — contrato LLD con master trapper (Zabbix 7.4, lab local)")
    print("API: %s  host: %s" % (API_URL, LAB_HOST_NAME))
    print("=" * 78)

    token = login()
    group_id = ensure_group(token)
    host_id = ensure_host(token, group_id)
    interface_id = ensure_snmp_interface(token, host_id)
    start_mini_snmp()

    try:
        results = []
        for case in CASES:
            print("\n--- caso %s: %s" % (case["id"], case["title"]))
            result = run_case(token, host_id, interface_id, case)
            results.append(result)
            print("    %s -> %s" % ("OK" if result["ok"] else "FALLA", result["detail"]))

            # Que hace el motor cuando el filtro usa una macro que no existe?
        for case in CASES:
            if "note" not in case:
                continue
            rules = api_call("discoveryRule.get", {"hostids": [host_id], "filter": {"key_": "t1.rule.%s" % case["id"]},
                                                    "output": ["itemid", "key_", "error"]}, token)
            error = rules[0].get("error", "") if rules else "(regla inexistente)"
            print("\n--- caso %s (macro inexistente en el filtro)" % case["id"])
            print("    error de la regla: %r" % error)
            log = docker("logs", "zabbix-server", check=False).stdout.splitlines()
            hits = [line for line in log if "t1.rule.%s" % case["id"] in line][-5:]
            print("    log del server (%d lineas con la regla):" % len(hits))
            for line in hits:
                print("      %s" % line.strip())

    # Integracion con los nombres de produccion.
        print("\n--- integracion: net.vlan.map + net.vlan.discovery")
        integration = run_integration(token, host_id, interface_id)
        results.append(integration)
        print("    %s -> %s" % ("OK" if integration["ok"] else "FALLA", integration["detail"]))
    finally:
        # El respondedor SNMP minimo es solo para este test: se baja solo.
        stop_mini_snmp()
        print("[snmp] respondedor minimo bajado (los items del host de prueba quedan sin SNMP)")

    # Verificacion de datos sobre el caso canonico.
    canonical = next(r for r in results if r["id"] == "canonical")
    data_ok = False
    keys_ok = False
    if canonical["items"]:
        discovered = {item["key_"]: item.get("snmp_oid", "") for item in canonical["items"]}
        missing = []
        for name, index in CANONICAL_VLANS:
            key = "net.vlan.t1canonical.in[ifHCInOctets.%d]" % index
            oid = "1.3.6.1.2.1.31.1.1.1.6.%d" % index
            if discovered.get(key) != oid:
                missing.append("%s (oid=%s)" % (key, discovered.get(key, "<ausente>")))
        keys_ok = not missing
        print("\n--- keys y OIDs de los items descubiertos (caso canonico)")
        for key in sorted(discovered):
            print("    %-46s %s" % (key, discovered[key]))
        if missing:
            print("    FALTAN o no coinciden: %s" % "; ".join(missing))

        item_ids = [item["itemid"] for item in canonical["items"]]
        if integration["items"]:
            item_ids += [item["itemid"] for item in integration["items"]]
        with_data = wait_for_value(token, item_ids, timeout=120)
        print("\n--- valores de los items descubiertos (caso canonico)")
        for item in with_data:
            print("    %-42s snmp_oid=%-34s lastvalue=%s" % (
                item["key_"], item.get("snmp_oid", "?"), item["lastvalue"]))
        history = history_values(token, item_ids)
        data_ok = bool(history) and all(item["lastvalue"] not in ("", "0") for item in with_data)
        print("    filas de history: %d | con dato: %s" % (len(history), data_ok))

    # El filtro tiene que dejar solo las 8 VLANs (las pppoe se filtran).
    filter_case = next(r for r in results if r["id"] == "filter")
    filter_ok = filter_case["ok"] and len(filter_case["items"]) == 8
    print("\n--- caso filter: %d items descubiertos (se esperaban 8)" % len(filter_case["items"]))

    failures = [r["id"] for r in results if not r["ok"]]

    print("\n" + "=" * 78)
    print("CONTRATO VERIFICADO (Zabbix 7.4.13)")
    print("=" * 78)
    print(CONTRACT_TEXT)
    print("| Resultados por caso:")
    for result in results:
        print("    %-10s %-6s %s" % (result["id"], "OK" if result["ok"] else "FALLA", result["detail"]))
    print("| Datos en los items descubiertos: %s" % ("OK" if data_ok else "NO"))
    print("| Keys y OIDs de las 8 VLANs: %s" % ("OK" if keys_ok else "NO"))
    print("| Filtro LLD sobre {#IFDESCR}: %s" % ("OK" if filter_ok else "NO"))

    if failures or not data_ok or not filter_ok or not keys_ok:
        print("\nRESULTADO: FALLA (casos fallidos: %s)" % (", ".join(failures) or "ninguno"))
        return 1
    print("\nRESULTADO: OK — contrato verificado")
    return 0


if __name__ == "__main__":
    sys.exit(main())
