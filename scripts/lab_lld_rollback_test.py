#!/usr/bin/env python3
"""Ensayo del rollback de la LLD por trapper — SOLO en el lab local.

Alcance: este script NO toca site-a. Ensaya en el lab (host `vlan-lld-shape-lab`
del Zabbix 7.4.13 local) el rollback completo del diseño de la opción B:

    1. quitar las `lld_macro_paths` de la regla
    2. re-apuntar el master de la regla al item SNMP walk
    3. deshabilitar el item trapper y rehabilitar el SNMP walk
    4. dejar de publicar el JSON (equivalente a sacar el cron)

y verifica en cada paso que el estado vuelve al previo:
    - la LLD deja de descubrir (las macros no resuelven / el master no tiene valor)
    - el item trapper queda deshabilitado
    - el valor del master queda vacío
    - no queda ningún item descubierto huérfano

El script usa SUS PROPIOS objetos (prefijo `rb.`), no toca los del test de
shape (`t1.*`, `net.vlan.discovery`), y al terminar borra todo lo que creó:
el lab queda como estaba y se puede correr dos veces seguidas.

Ejecucion:  python3 scripts/lab_lld_rollback_test.py
Salida:     exit 0 si el rollback se verificó en los 4 pasos.
"""

import json
import os
import subprocess
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import lab_lld_shape_test as T  # noqa: E402

# Nombres propios del ensayo (no tocan los del test de shape).
RULE_KEY = "rb.rule"
MASTER_KEY = "rb.master"
WALK_KEY = "rb.walk"
PROTO_IN = "net.vlan.rb.in[ifHCInOctets.{#SNMPINDEX}]"
PROTO_OUT = "net.vlan.rb.out[ifHCOutOctets.{#SNMPINDEX}]"
WALK_OID = ("walk[1.3.6.1.2.1.31.1.1.1.1,1.3.6.1.2.1.31.1.1.1.18,"
            "1.3.6.1.2.1.2.2.1.2,1.3.6.1.2.1.2.2.1.3]")

# (macro, path) -> el helper ensure_rule los convierte al formato de la API
MACRO_PATHS = [
    ("{#IFDESCR}", "$.ifdescr"),
    ("{#IFNAME}", "$.ifname"),
    ("{#SNMPINDEX}", "$.index"),
]

CHECKS = []


def check(name, ok, detail=""):
    CHECKS.append((name, ok, detail))
    print("    [%s] %s%s" % ("OK" if ok else "FALLA", name, (" -> " + detail) if detail else ""))
    return ok


def rule_state(token, rule_id):
    rules = T.api_call("discoveryRule.get", {"itemids": [rule_id], "output": ["itemid", "master_itemid", "error"]}, token)
    return rules[0] if rules else {}


def item_state(token, key):
    items = T.api_call("item.get", {"filter": {"key_": key}, "output": ["itemid", "key_", "status", "lastvalue", "lastclock"]}, token)
    return items[0] if items else {}


def discovered(token, host_id):
    raw = T.api_call("item.get", {"hostids": [host_id], "search": {"key_": "net.vlan.rb."},
                                  "output": ["itemid", "key_", "flags"]}, token)
    return [item for item in raw if item.get("flags") == "4"]


def lld_macro_paths_in_db(rule_id):
    """Las lld_macro_path no las expone la API 7.4: se leen de la base."""
    result = subprocess.run(
        ["docker", "exec", "-i", "zabbix-postgres", "psql", "-U", "zabbix", "-d", "zabbix",
         "-At", "-c", "select count(*) from lld_macro_path where itemid = %d;" % int(rule_id)],
        capture_output=True, text=True)
    try:
        return int(result.stdout.strip())
    except ValueError:
        return -1


def cleanup(token, host_id):
    """Borra todo lo que creo el ensayo: el lab queda como estaba."""
    for key in (RULE_KEY,):
        rules = T.api_call("discoveryRule.get", {"hostids": [host_id], "filter": {"key_": key},
                                                "output": ["itemid"]}, token)
        if rules:
            T.api_call("discoveryRule.delete", [rules[0]["itemid"]], token)
    protos = T.api_call("itemPrototype.get", {"hostids": [host_id], "search": {"key_": "net.vlan.rb."},
                                              "output": ["itemid"]}, token)
    if protos:
        T.api_call("itemPrototype.delete", [p["itemid"] for p in protos], token)
    items = T.api_call("item.get", {"hostids": [host_id], "search": {"key_": "net.vlan.rb."},
                                    "output": ["itemid"]}, token)
    if items:
        T.api_call("item.delete", [i["itemid"] for i in items], token)
    for key in (MASTER_KEY, WALK_KEY):
        found = T.api_call("item.get", {"hostids": [host_id], "filter": {"key_": key},
                                        "output": ["itemid"]}, token)
        if found:
            T.api_call("item.delete", [found[0]["itemid"]], token)


def main():
    print("=" * 78)
    print("Ensayo del rollback de la LLD por trapper — LAB LOCAL (no site-a)")
    print("=" * 78)

    token = T.login()
    group_id = T.ensure_group(token)
    host_id = T.ensure_host(token, group_id)
    interface_id = T.ensure_snmp_interface(token, host_id)

    # --- estado inicial: el ensayo usa objetos propios, asi que limpia lo suyo
    cleanup(token, host_id)

    try:
        # ---------------- SETUP: el estado "nuevo" (trapper) ----------------
        print("\n--- SETUP: estado con master trapper (como quedo en site-a)")
        master_id = T.ensure_master_item(token, host_id, MASTER_KEY, "rollback: master trapper")
        walk_id = T.ensure_master_item(token, host_id, WALK_KEY, "rollback: master SNMP walk")
        T.api_call("item.update", {"itemid": walk_id, "status": 1}, token)  # walk deshabilitado
        rule_id = T.ensure_rule(token, host_id, RULE_KEY, master_id, MACRO_PATHS)
        T.ensure_prototype(token, host_id, rule_id, PROTO_IN, T.IN_OID, interface_id, "in")
        T.ensure_prototype(token, host_id, rule_id, PROTO_OUT, T.OUT_OID, interface_id, "out")
        T.reload_config_cache()

        T.start_mini_snmp()
        payload = json.dumps(
            [{"ifdescr": name, "ifname": name, "index": index}
             for name, index in T.CANONICAL_VLANS], separators=(",", ":"))
        T.publish(T.LAB_HOST_NAME, MASTER_KEY, payload)
        found = T.wait_for_items(token, host_id, "net.vlan.rb.in[ifHCInOctets.", expected_count=8, timeout=90)
        check("SETUP: la LLD descubre las 8 VLANs con el master trapper", len(found) == 8,
              "%d items" % len(found))
        discovered_before = {item["key_"] for item in discovered(token, host_id)}
        check("SETUP: la regla tiene las 3 lld_macro_paths", lld_macro_paths_in_db(rule_id) == 3,
              "%d filas en lld_macro_path" % lld_macro_paths_in_db(rule_id))
        master = item_state(token, MASTER_KEY)
        check("SETUP: el master trapper tiene el JSON", bool(master.get("lastvalue")),
              str(master.get("lastvalue"))[:40])

        # ---------------- ROLLBACK 1: quitar las lld_macro_paths -------------
        print("\n--- ROLLBACK paso 1: quitar las lld_macro_paths de la regla")
        t0 = time.time()
        T.api_call("discoveryRule.update", {"itemid": rule_id, "lld_macro_paths": []}, token)
        T.reload_config_cache()
        elapsed = time.time() - t0
        check("paso 1: la regla ya no tiene lld_macro_paths", lld_macro_paths_in_db(rule_id) == 0,
              "%d filas en lld_macro_path" % lld_macro_paths_in_db(rule_id))
        # sin macros, la LLD no resuelve las entidades -> no descubre nada nuevo
        T.publish(T.LAB_HOST_NAME, MASTER_KEY, json.dumps(
            [{"ifdescr": "vlan999", "ifname": "vlan999", "index": 999}], separators=(",", ":")))
        time.sleep(20)
        after = discovered(token, host_id)
        check("paso 1: la LLD no descubre items nuevos sin macros",
              all(item["key_"] not in ("net.vlan.rb.in[ifHCInOctets.999]",) for item in after),
              "%d items descubiertos (los de antes, sin cambios)" % len(after))
        print("    (%.1f s)" % elapsed)

        # ---------------- ROLLBACK 2: re-apuntar el master al SNMP walk -----
        print("\n--- ROLLBACK paso 2: re-apuntar el master al item SNMP walk")
        t0 = time.time()
        T.api_call("discoveryRule.update", {"itemid": rule_id, "master_itemid": walk_id}, token)
        T.reload_config_cache()
        elapsed = time.time() - t0
        state = rule_state(token, rule_id)
        check("paso 2: el master de la regla es el SNMP walk", state.get("master_itemid") == walk_id,
              "master_itemid=%s (walk=%s)" % (state.get("master_itemid"), walk_id))
        print("    (%.1f s)" % elapsed)

        # ---------------- ROLLBACK 3: trapper off / walk on ------------------
        print("\n--- ROLLBACK paso 3: deshabilitar el trapper y rehabilitar el SNMP walk")
        t0 = time.time()
        T.api_call("item.update", {"itemid": master_id, "status": 1}, token)
        T.api_call("item.update", {"itemid": walk_id, "status": 0}, token)
        T.reload_config_cache()
        elapsed = time.time() - t0
        check("paso 3: el item trapper quedo deshabilitado", item_state(token, MASTER_KEY).get("status") == "1",
              "status=%s" % item_state(token, MASTER_KEY).get("status"))
        check("paso 3: el item SNMP walk quedo habilitado", item_state(token, WALK_KEY).get("status") == "0",
              "status=%s" % item_state(token, WALK_KEY).get("status"))
        print("    (%.1f s)" % elapsed)

        # ---------------- ROLLBACK 4: dejar de publicar --------------------
        print("\n--- ROLLBACK paso 4: dejar de publicar el JSON (equivale a sacar el cron)")
        t0 = time.time()
        before_value = item_state(token, MASTER_KEY).get("lastvalue")
        # el trapper deshabilitado ya no acepta datos: el sender lo rechaza
        rejected = T.docker("exec", T.SENDER_CONTAINER, "zabbix_sender",
                            "-z", T.SENDER_SERVER, "-p", T.SENDER_PORT,
                            "-s", T.LAB_HOST_NAME, "-k", MASTER_KEY, "-o", payload, check=False)
        time.sleep(15)  # no se publica nada mas: el master no debe cambiar
        after_value = item_state(token, MASTER_KEY).get("lastvalue")
        elapsed = time.time() - t0
        check("paso 4: el trapper deshabilitado RECHAZA el JSON",
              "failed: 1" in rejected.stdout, rejected.stdout.strip().splitlines()[0])
        check("paso 4: el valor del master trapper no cambia (no llega nada nuevo)",
              after_value == before_value, "valor antes=%r despues=%r" % (before_value, after_value))
        print("    (%.1f s)" % elapsed)

        # ---------------- VERIFICACIONES FINALES ---------------------------
        print("\n--- VERIFICACIONES FINALES")
        state = rule_state(token, rule_id)
        # el master SNMP walk no tiene valor en el lab (no hay equipo SNMP):
        # la LLD no puede parsear nada -> no descubre nada nuevo.
        walk = item_state(token, WALK_KEY)
        check("final: el master SNMP walk no tiene valor (la LLD no puede parsear nada)",
              not walk.get("lastvalue"), "lastvalue=%r" % walk.get("lastvalue"))
        discovered_after = {item["key_"] for item in discovered(token, host_id)}
        check("final: tras el rollback no se descubrieron items nuevos",
              discovered_after == discovered_before,
              "%d items descubiertos, mismos keys que en el SETUP: %s"
              % (len(discovered_after), discovered_after == discovered_before))
        print("    nota: el campo error de la regla conserva el ultimo mensaje "
              "(%r); en produccion se limpia al proximo rediscover." % state.get("error", "")[:80])
        check("final: el item trapper quedo deshabilitado",
              item_state(token, MASTER_KEY).get("status") == "1")
        expected_keys = set()
        for direction, template in (("in", "net.vlan.rb.in[ifHCInOctets.%d]"),
                                    ("out", "net.vlan.rb.out[ifHCOutOctets.%d]")):
            for index in [98, 99, 100, 102, 103, 104, 105, 106]:
                expected_keys.add(template % index)
        orphans = [item for item in discovered(token, host_id) if item["key_"] not in expected_keys]
        check("final: no hay items descubiertos huerfanos", not orphans,
              "%d huerfanos" % len(orphans))
    finally:
        print("\n--- LIMPIEZA: se borra todo lo que creo el ensayo")
        cleanup(token, host_id)
        T.stop_mini_snmp()
        left = T.api_call("item.get", {"hostids": [host_id], "search": {"key_": "net.vlan.rb."},
                                       "output": ["itemid"]}, token)
        print("    objetos del ensayo restantes en el lab: %d" % len(left))

    failures = [name for name, ok, _ in CHECKS if not ok]
    print("\n" + "=" * 78)
    print("RESULTADO: %s (%d verificaciones)" % ("OK" if not failures else "FALLA", len(CHECKS)))
    for name, ok, detail in CHECKS:
        print("    %-6s %s%s" % ("OK" if ok else "FALLA", name, (" -> " + detail) if detail else ""))
    print("=" * 78)
    if failures:
        print("Pasos fallidos: %s" % ", ".join(failures))
        return 1
    print("Rollback ensayado en el LAB (no en site-a).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
