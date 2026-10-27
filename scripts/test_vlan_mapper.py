#!/usr/bin/env python3
"""Test del mapper de VLANs (T2) — corre SIN red.

Usa la fixture sintetica que replica la ifTable de un CHR de site-a
(2.190 filas: 8 VLANs + 2.159 interfaces dinamicas PPPoE + fijas) y un
`snmpwalk` inyectado, asi que no toca la red ni site-a.

Verifica:
  1. El parser del walk crudo (`snmpwalk -Oq`) saca bien (ifIndex, nombre).
  2. El filtro deja las 8 VLANs con su ifIndex correcto.
  3. Las 2.159 interfaces dinamicas PPPoE NO aparecen.
  4. El JSON tiene la forma verificada en T1 (array de objetos con
     ifdescr / ifname / index).
  5. El mapper es idempotente: dos corridas producen el mismo JSON.

Ejecucion: python3 scripts/test_vlan_mapper.py   (exit 0 = verde)
"""

import json
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import vlan_mapper  # noqa: E402

FIXTURE = os.path.join(vlan_mapper.FIXTURE_DIR, "chr_703_ifdescr_walk.txt")
FIXTURE_PPP = os.path.join(vlan_mapper.FIXTURE_DIR, "chr_703_ppp_sessions_walk.txt")

# La whitelist real del template 10869 (leida de la base de site-a el 2026-10-22)
PPP_WHITELIST = (r"(?i)^(<pppoe-coopvinia>|<pppoe-multijactosa>|<pppoe-franciscosellart>|"
                  r"<pppoe-arrebeef>|<pppoe-garfin>|<pppoe-buratovichhnos>|"
                  r"<pppoe-southernseeds>|<pppoe-patrullarural>|Enlace-patrullarural)$")

# El mapper publica TODAS las interfaces vlan* del router (la macro de host
# decide cuales se monitorean: el filtro de la LLD las rechaza).
EXPECTED_VLANS = [
    {"ifdescr": "vlan250", "ifname": "vlan250", "index": 98},
    {"ifdescr": "vlan301", "ifname": "vlan301", "index": 99},
    {"ifdescr": "vlan305", "ifname": "vlan305", "index": 100},
    {"ifdescr": "vlan999", "ifname": "vlan999", "index": 101},
    {"ifdescr": "vlan175", "ifname": "vlan175", "index": 102},
    {"ifdescr": "vlan190", "ifname": "vlan190", "index": 103},
    {"ifdescr": "vlan220", "ifname": "vlan220", "index": 104},
    {"ifdescr": "vlan225", "ifname": "vlan225", "index": 105},
    {"ifdescr": "vlan235", "ifname": "vlan235", "index": 106},
]


def fixture_text():
    with open(FIXTURE, encoding="utf-8") as handle:
        return handle.read()


def fixture_text():
    with open(FIXTURE, encoding="utf-8") as handle:
        return handle.read()


def ppp_fixture_text():
    with open(FIXTURE_PPP, encoding="utf-8") as handle:
        return handle.read()


def fake_walker(text):
    """Walker inyectado: devuelve la fixture sin tocar la red."""
    def walker(ip, community, oid, **kwargs):
        assert ip == "192.0.2.65", ip
        assert community == "public", community
        assert oid == "1.3.6.1.2.1.2.2.1.2", oid
        return text
    return walker


def fake_ppp_walker(text):
    """Walker de la tabla de sesiones PPP."""
    def walker(ip, community, oid, **kwargs):
        assert oid == "1.3.6.1.4.1.14988.1.1.2.1.1.2", oid
        return text
    return walker


class TestVlanMapper(unittest.TestCase):

    def setUp(self):
        self.text = fixture_text()
        self.config = json.loads(json.dumps(vlan_mapper.DEFAULT_CONFIG))
        self.config["hosts"] = [{"zabbix_host": "SW-EDGE-703", "ip": "192.0.2.65"}]
        self.config["ppp"]["whitelist"] = PPP_WHITELIST
        self.ppp_text = ppp_fixture_text()

    # --- parser -----------------------------------------------------------
    def test_fixture_shape(self):
        rows = vlan_mapper.parse_walk_output(self.text)
        self.assertEqual(len(rows), 2190, "la fixture debe tener 2.190 filas de ifTable")
        pppoe = [row for row in rows if row[1].startswith("pppoe-")]
        self.assertEqual(len(pppoe), 2159, "2.159 interfaces dinamicas PPPoE")

    def test_parser_indexes(self):
        rows = vlan_mapper.parse_walk_output(self.text)
        by_index = dict(rows)
        self.assertEqual(by_index[1], "lo")
        self.assertEqual(by_index[98], "vlan250")
        self.assertEqual(by_index[102], "vlan175")
        self.assertEqual(by_index[106], "vlan235")

    def test_parser_ignores_noise(self):
        noise = (
            "# comentario\n"
            "\n"
            '.1.3.6.1.2.1.2.2.1.2.42 "vlan42"\n'
            ".1.3.6.1.2.1.31.1.1.1.1.42 \"otra-columna\"\n"
            "basura sin oid\n"
        )
        rows = vlan_mapper.parse_walk_output(noise)
        self.assertEqual(rows, [(42, "vlan42")])

    def test_parser_accepts_oid_sin_punto(self):
        rows = vlan_mapper.parse_walk_output('1.3.6.1.2.1.2.2.1.2.7 "vlan7"')
        self.assertEqual(rows, [(7, "vlan7")])

    def test_parser_accepts_raiz_iso(self):
        """net-snmp 5.9 en site-a imprime la raiz 'iso.' (no '.1.3.6...')."""
        rows = vlan_mapper.parse_walk_output('iso.3.6.1.2.1.2.2.1.2.7 "vlan7"')
        self.assertEqual(rows, [(7, "vlan7")])

    def test_normalize_oid(self):
        self.assertEqual(vlan_mapper.normalize_oid("iso.3.6.1.2.1.2.2.1.2.98"), "1.3.6.1.2.1.2.2.1.2.98")
        self.assertEqual(vlan_mapper.normalize_oid(".1.3.6.1.2.1.2.2.1.2.98"), "1.3.6.1.2.1.2.2.1.2.98")
        self.assertEqual(vlan_mapper.normalize_oid("1.3.6.1.2.1.2.2.1.2.98"), "1.3.6.1.2.1.2.2.1.2.98")

    # --- comando snmpwalk ---------------------------------------------------
    def test_snmpwalk_command_uses_valid_version_flag(self):
        """net-snmp NO acepta '-v2': para v2c la sintaxis es '-v 2c'."""
        command = vlan_mapper.build_snmpwalk_command("192.0.2.65", "public", "1.3.6.1.2.1.2.2.1.2")
        self.assertIn("-v", command)
        self.assertEqual(command[command.index("-v") + 1], "2c")
        self.assertNotIn("-v2", command)

    def test_snmpwalk_command_shape(self):
        command = vlan_mapper.build_snmpwalk_command(
            "192.0.2.65", "public", "1.3.6.1.2.1.2.2.1.2", version=2, timeout=30, retries=1)
        self.assertEqual(command[0], "snmpwalk")
        self.assertEqual(command[command.index("-c") + 1], "public")
        self.assertEqual(command[command.index("-t") + 1], "30")
        self.assertEqual(command[command.index("-r") + 1], "1")
        self.assertIn("-Oq", command)
        self.assertEqual(command[-2], "192.0.2.65")
        self.assertEqual(command[-1], "1.3.6.1.2.1.2.2.1.2")

    # --- filtro -----------------------------------------------------------
    def test_filter_keeps_the_8_vlans(self):
        rows = vlan_mapper.parse_walk_output(self.text)
        vlans = vlan_mapper.filter_vlans(
            rows,
            pattern=self.config["vlan"]["pattern"],
            exclude_pattern=self.config["vlan"]["exclude_pattern"],
        )
        self.assertEqual(vlans, EXPECTED_VLANS)

    def test_filter_drops_pppoe(self):
        rows = vlan_mapper.parse_walk_output(self.text)
        vlans = vlan_mapper.filter_vlans(
            rows,
            pattern=self.config["vlan"]["pattern"],
            exclude_pattern=self.config["vlan"]["exclude_pattern"],
        )
        names = [vlan["ifdescr"] for vlan in vlans]
        self.assertEqual(len([name for name in names if name.startswith("pppoe-")]), 0)
        self.assertEqual(len(vlans), 9)

    def test_mapper_does_not_filter_by_vlan_list(self):
        """El mapper no lleva listas de VLANs: publica todas las vlan* del router.

        La autoridad de que se monitoree una VLAN es la macro de host
        {$site-a.VLAN.MATCHES} (filtro de la LLD), no el mapper: agregar una
        VLAN a un CHR tiene que ser tocar UNA sola lista.
        """
        rows = vlan_mapper.parse_walk_output(self.text)
        vlans = vlan_mapper.filter_vlans(
            rows,
            pattern=self.config["vlan"]["pattern"],
            exclude_pattern=self.config["vlan"]["exclude_pattern"],
        )
        self.assertIn("vlan999", [vlan["ifdescr"] for vlan in vlans])
        self.assertNotIn("ids", self.config["vlan"])
        for host in self.config["hosts"]:
            self.assertNotIn("vlans", host)

    # --- la macro del host es la autoridad (el mapper no filtra) -----------
    def test_mapper_publishes_every_vlan_the_router_has(self):
        """El mapper publica todas las vlan* del router, sin lista propia.

        El filtro de la LLD (macro de host {$site-a.VLAN.MATCHES}) es el que
        decide que se monitorea; publicar de mas es inofensivo.
        """
        rows = vlan_mapper.parse_walk_output(self.text)
        vlans = vlan_mapper.filter_vlans(
            rows,
            pattern=self.config["vlan"]["pattern"],
            exclude_pattern=self.config["vlan"]["exclude_pattern"],
        )
        self.assertEqual(vlans, EXPECTED_VLANS)
        self.assertIn("vlan999", [v["ifdescr"] for v in vlans])


    # --- lado PPP: conteo de sesiones y mapa de dedicados -------------------
    def test_count_ppp_sessions(self):
        """El conteo es el numero de FILAS de la tabla de sesiones PPP."""
        rows = vlan_mapper.parse_walk_output(self.ppp_text, "1.3.6.1.4.1.14988.1.1.2.1.1.2")
        self.assertEqual(len(rows), 2079)
        self.assertEqual(vlan_mapper.count_ppp_sessions(rows), 2079)

    def test_filter_dedicated_uses_the_whitelist(self):
        """Solo pasan las sesiones que matchean la whitelist del template."""
        rows = vlan_mapper.parse_walk_output(self.ppp_text, "1.3.6.1.4.1.14988.1.1.2.1.1.2")
        dedicated = vlan_mapper.filter_dedicated(rows, PPP_WHITELIST)
        names = [entry["ppp_name"] for entry in dedicated]
        self.assertEqual(len(dedicated), 9)
        self.assertIn("<pppoe-coopvinia>", names)
        self.assertIn("Enlace-patrullarural", names)
        self.assertNotIn("<pppoe-aliciacanovas0>", names)
        for entry in dedicated:
            self.assertIn("index", entry)
            self.assertIsInstance(entry["index"], int)

    def test_dedicated_json_is_small(self):
        """El JSON del master debe entrar de sobra en los 64 KB del item.

        Con 2.079 sesiones PPP, publicar el mapa completo seria ~100 KB: por eso
        el mapper publica SOLO las dedicadas.
        """
        rows = vlan_mapper.parse_walk_output(self.ppp_text, "1.3.6.1.4.1.14988.1.1.2.1.1.2")
        dedicated = vlan_mapper.filter_dedicated(rows, PPP_WHITELIST)
        payload = vlan_mapper.build_payload(dedicated)
        self.assertLess(len(payload), 1024)
        self.assertLess(len(payload), 65535)
        # el mapa completo, en cambio, no entraria
        full = vlan_mapper.build_payload([{"ppp_name": name, "index": index}
                                          for index, name in rows])
        self.assertGreater(len(full), 65535)

    def test_no_whitelist_means_no_dedicated_map(self):
        rows = vlan_mapper.parse_walk_output(self.ppp_text, "1.3.6.1.4.1.14988.1.1.2.1.1.2")
        self.assertEqual(vlan_mapper.filter_dedicated(rows, None), [])
        self.assertEqual(vlan_mapper.filter_dedicated(rows, ""), [])

    def test_invalid_whitelist_raises(self):
        with self.assertRaises(ValueError):
            vlan_mapper.filter_dedicated([(1, "<pppoe-x>")], "(unclosed")

    def test_ppp_walk_failure_does_not_break_the_vlan_side(self):
        """Un fallo del walk de PPP no puede tumbar el mapa de VLANs."""
        published = []

        def spy(zabbix_config, host, key, payload):
            published.append((key, payload))
            return True, "sent: 1"

        def broken_ppp_walker(ip, community, oid, **kwargs):
            raise RuntimeError("timeout")

        original = vlan_mapper.publish
        vlan_mapper.publish = spy
        try:
            code = vlan_mapper.run(self.config, walker=fake_walker(self.text),
                                   ppp_walker=broken_ppp_walker)
        finally:
            vlan_mapper.publish = original
        self.assertEqual(code, 0)
        self.assertEqual([key for key, _payload in published], ["net.vlan.map"])

    def test_ppp_walk_with_zero_rows_does_not_publish_ppp_but_keeps_the_vlans(self):
        """Un walk PPP con 0 filas no publica PPP, pero si publica las VLANs.

        El guard del mapper trata un walk PPP vacio como walk corto/fallido:
        no publica el conteo (evita pisar el ultimo valor bueno con 0) y deja
        intacto el lado VLAN.
        """
        published = []

        def spy(zabbix_config, host, key, payload):
            published.append((key, payload))
            return True, "sent: 1"

        def empty_ppp_walker(ip, community, oid, **kwargs):
            assert oid == "1.3.6.1.4.1.14988.1.1.2.1.1.2", oid
            return ""

        original = vlan_mapper.publish
        vlan_mapper.publish = spy
        try:
            code = vlan_mapper.run(self.config, walker=fake_walker(self.text),
                                   ppp_walker=empty_ppp_walker)
        finally:
            vlan_mapper.publish = original
        self.assertEqual(code, 0)
        self.assertEqual([key for key, _payload in published], ["net.vlan.map"],
                         "con 0 filas PPP solo se publica el mapa de VLANs")

        vlans, _rows, ppp, error = vlan_mapper.collect_host(
            self.config["hosts"][0], self.config, walker=fake_walker(self.text),
            ppp_walker=empty_ppp_walker
        )
        self.assertIsNone(error)
        self.assertIsNone(ppp, "con 0 filas PPP el resultado no debe traer conteo")
        self.assertEqual(len(vlans), 9, "el lado VLAN no se toca")

    def test_key_for_each_purpose(self):
        zabbix = self.config["zabbix"]
        self.assertEqual(vlan_mapper.key_for(zabbix, "vlan_map"), "net.vlan.map")
        self.assertEqual(vlan_mapper.key_for(zabbix, "ppp_count"), "mikrotik.ppp.active.count")
        self.assertEqual(vlan_mapper.key_for(zabbix, "ppp_map"), "net.ppp.map")

    def test_read_whitelist_from_db(self):
        """La whitelist se lee del TEMPLATE por psql read-only (fuente unica)."""
        calls = []

        class FakeResult:
            returncode = 0
            stdout = "(?i)^(<pppoe-coopvinia>|<pppoe-garfin>)$\n"
            stderr = ""

        def fake_run(command, **kwargs):
            calls.append(command)
            return FakeResult()

        original = vlan_mapper.subprocess.run
        vlan_mapper.subprocess.run = fake_run
        try:
            value = vlan_mapper.read_whitelist_from_db(
                {"type": "db", "container": "zabbix-postgres", "template_hostid": 10870,
                 "macro": "{$PPP.DEDICATED.MATCHES}"})
        finally:
            vlan_mapper.subprocess.run = original
        self.assertIn("<pppoe-coopvinia>", value)
        self.assertTrue(calls[0][0].endswith("docker"))
        self.assertIn("zabbix-postgres", calls[0])
        self.assertIn("hostmacro", calls[0][-1])

    def test_read_whitelist_from_db_returns_none_on_failure(self):
        class FakeResult:
            returncode = 1
            stdout = ""
            stderr = "psql: no se pudo conectar"

        original = vlan_mapper.subprocess.run
        vlan_mapper.subprocess.run = lambda command, **kwargs: FakeResult()
        try:
            value = vlan_mapper.read_whitelist_from_db(
                {"type": "db", "container": "zabbix-postgres", "template_hostid": 10870,
                 "macro": "{$PPP.DEDICATED.MATCHES}"})
        finally:
            vlan_mapper.subprocess.run = original
        self.assertIsNone(value)

    def test_resolve_whitelist_precedence(self):
        config = json.loads(json.dumps(self.config))
        config["ppp"]["whitelist"] = None
        config["ppp"]["whitelist_fallback"] = "(?i)^<pppoe-fallback>$"
        self.assertEqual(vlan_mapper.resolve_whitelist(config, "(?i)^<pppoe-directo>$"),
                         "(?i)^<pppoe-directo>$")

    # --- payload ----------------------------------------------------------
    def test_payload_shape_is_the_t1_contract(self):
        vlans, _rows, _ppp, error = vlan_mapper.collect_host(
            self.config["hosts"][0], self.config, walker=fake_walker(self.text),
            ppp_walker=fake_ppp_walker(self.ppp_text)
        )
        self.assertIsNone(error)
        payload = vlan_mapper.build_payload(vlans)
        parsed = json.loads(payload)
        self.assertIsInstance(parsed, list, "el JSON debe ser un array")
        self.assertEqual(len(parsed), 9)
        for entry in parsed:
            self.assertEqual(sorted(entry.keys()), ["ifdescr", "ifname", "index"])
            self.assertIsInstance(entry["index"], int)
        self.assertEqual(parsed[0], {"ifdescr": "vlan250", "ifname": "vlan250", "index": 98})

    def test_payload_is_small(self):
        """El motivo de todo el diseno: el JSON tiene que entrar de sobra en 64 KB."""
        vlans, _rows, _ppp, _error = vlan_mapper.collect_host(
            self.config["hosts"][0], self.config, walker=fake_walker(self.text),
            ppp_walker=fake_ppp_walker(self.ppp_text)
        )
        payload = vlan_mapper.build_payload(vlans)
        self.assertLess(len(payload), 1024)
        self.assertLess(len(payload), 65535)

    # --- flujo completo ---------------------------------------------------
    def test_run_dry_run_does_not_publish(self):
        published = []

        def spy(zabbix_config, host, key, payload):
            published.append((host, key, payload))
            return True, "ok"

        original = vlan_mapper.publish
        vlan_mapper.publish = spy
        try:
            code = vlan_mapper.run(self.config, dry_run=True, walker=fake_walker(self.text),
                                   ppp_walker=fake_ppp_walker(self.ppp_text))
        finally:
            vlan_mapper.publish = original
        self.assertEqual(code, 0)
        self.assertEqual(published, [], "en dry-run no se debe publicar nada")

    def test_run_publishes_and_is_idempotent(self):
        published = []

        def spy(zabbix_config, host, key, payload):
            published.append((host, key, payload))
            return True, "sent: 1"

        original = vlan_mapper.publish
        vlan_mapper.publish = spy
        try:
            self.assertEqual(vlan_mapper.run(self.config, walker=fake_walker(self.text),
                                              ppp_walker=fake_ppp_walker(self.ppp_text)), 0)
            self.assertEqual(vlan_mapper.run(self.config, walker=fake_walker(self.text),
                                              ppp_walker=fake_ppp_walker(self.ppp_text)), 0)
        finally:
            vlan_mapper.publish = original
        self.assertEqual(len(published), 6, "3 valores por corrida (vlan_map, ppp_count, ppp_map)")
        self.assertEqual(published[0], published[3], "dos corridas deben publicar lo mismo")
        self.assertEqual(published[1], published[4])
        self.assertEqual(published[2], published[5])
        host, key, payload = published[0]
        self.assertEqual(host, "SW-EDGE-703")
        self.assertEqual(key, "net.vlan.map")
        self.assertEqual(json.loads(payload), EXPECTED_VLANS)

    def test_one_dead_chr_does_not_break_the_others(self):
        def walker(ip, community, oid, **kwargs):
            if ip == "192.0.2.57":
                raise RuntimeError("snmpwalk fallo: timeout")
            return self.text

        config = json.loads(json.dumps(self.config))
        config["hosts"] = [
            {"zabbix_host": "SW-EDGE-501", "ip": "192.0.2.57"},
            {"zabbix_host": "SW-EDGE-703", "ip": "192.0.2.65"},
        ]
        published = []

        def spy(zabbix_config, host, key, payload):
            published.append((host, key))
            return True, "sent: 1"

        original = vlan_mapper.publish
        vlan_mapper.publish = spy
        try:
            code = vlan_mapper.run(config, walker=walker, ppp_walker=fake_ppp_walker(self.ppp_text))
        finally:
            vlan_mapper.publish = original
        self.assertEqual(code, 1, "un CHR caido tiene que quedar registrado como fallo")
        self.assertEqual([host for host, _key in published], ["SW-EDGE-703"] * 3,
                         "el CHR vivo se publica igual (3 valores)")

    def test_host_without_ip_is_skipped(self):
        config = json.loads(json.dumps(self.config))
        config["hosts"] = [{"zabbix_host": "SW-EDGE-701", "ip": None}]
        self.assertEqual(vlan_mapper.run(config, dry_run=True), 1)


# ==========================================================================
# hw: CPU / disco / RAM por trapper (piloto 704)
#
# El mapper camina hrProcessorLoad (1 columna) y 3 columnas de hrStorage
# (tablas chicas, nada comparable a la ifTable) y publica TRES escalares
# float con el mismo guard del PPP: walk fallido o 0 filas -> no publica.
# Deshabilitado por defecto; se activa por host con "hw": true.
# ==========================================================================

CPU_OID = "1.3.6.1.2.1.25.3.3.1.2"
STORAGE_DESCR_OID = "1.3.6.1.2.1.25.2.3.1.3"
STORAGE_SIZE_OID = "1.3.6.1.2.1.25.2.3.1.5"
STORAGE_USED_OID = "1.3.6.1.2.1.25.2.3.1.6"

# net-snmp -Oq imprime el '1.' inicial como 'iso.': iso.3.6.1.2.1...
def iso_oid(oid):
    return "iso." + oid[2:]

# 18 nucleos con media conocida: 9 nucleos a 10 % y 9 a 20 % -> 15.0
# (formato `snmpwalk -Oq`: `oid valor` con un espacio)
CPU_TEXT = "".join(
    "%s.%d %d\n" % (iso_oid(CPU_OID), i, 10 if i <= 9 else 20) for i in range(1, 19)
)
# hrStorage: fila 1 = "Memory" (RAM), fila 131072 = "System flash" (disco).
STORAGE_DESCR_TEXT = (
    "%s.1 \"Memory\"\n"
    "%s.131072 \"System flash\"\n" % (iso_oid(STORAGE_DESCR_OID), iso_oid(STORAGE_DESCR_OID))
)
STORAGE_SIZE_TEXT = (
    "%s.1 8192000\n"
    "%s.131072 60416\n" % (iso_oid(STORAGE_SIZE_OID), iso_oid(STORAGE_SIZE_OID))
)
STORAGE_USED_TEXT = (
    "%s.1 1048576\n"
    "%s.131072 32000\n" % (iso_oid(STORAGE_USED_OID), iso_oid(STORAGE_USED_OID))
)

HW_KEYS = ["system.hw.cpu.avg", "system.hw.disk.pused", "system.hw.ram.util"]


def generic_vlan_walker():
    """Walker de ifDescr sin asercion de IP (los tests de hw usan el host 704)."""
    def walker(ip, community, oid, **kwargs):
        assert oid == "1.3.6.1.2.1.2.2.1.2", oid
        return fixture_text()
    return walker


def fake_hw_walker(cpu_text=CPU_TEXT, descr_text=STORAGE_DESCR_TEXT,
                   size_text=STORAGE_SIZE_TEXT, used_text=STORAGE_USED_TEXT):
    """Walker de hw: una funcion para los 4 OIDs de hrProcessorLoad/hrStorage."""
    mapping = {
        CPU_OID: cpu_text,
        STORAGE_DESCR_OID: descr_text,
        STORAGE_SIZE_OID: size_text,
        STORAGE_USED_OID: used_text,
    }

    def walker(ip, community, oid, **kwargs):
        return mapping[oid]

    return walker


def broken_hw_walker(ip, community, oid, **kwargs):
    raise RuntimeError("snmpwalk fallo: timeout")


class HwTrapperTest(unittest.TestCase):
    def setUp(self):
        self.config = json.loads(json.dumps(vlan_mapper.DEFAULT_CONFIG))

    def collect(self, **kwargs):
        return vlan_mapper.collect_hw(
            self.config["hosts"][0], self.config, hw_walker=kwargs.get("hw_walker", fake_hw_walker())
        )

    def test_collect_hw_computes_the_three_metrics(self):
        hw = self.collect()
        # RAM: 1048576/8192000*100 = 12.8 ; disco: 32000/60416*100 = 53.0
        self.assertEqual(hw, {"cpu_avg": 15.0, "ram_util": 12.8, "disk_pused": 53.0})

    def test_cpu_walk_failure_keeps_storage(self):
        hw = vlan_mapper.collect_hw(
            self.config["hosts"][0], self.config,
            hw_walker=fake_hw_walker(cpu_text=None))
        self.assertNotIn("cpu_avg", hw)
        self.assertIn("ram_util", hw)
        self.assertIn("disk_pused", hw)

    def test_missing_memory_row_skips_ram_only(self):
        hw = vlan_mapper.collect_hw(
            self.config["hosts"][0], self.config,
            hw_walker=fake_hw_walker(descr_text="%s.131072 \"System flash\"\n" % iso_oid(STORAGE_DESCR_OID)))
        self.assertNotIn("ram_util", hw)
        self.assertIn("disk_pused", hw)
        self.assertIn("cpu_avg", hw)

    def test_missing_disk_row_skips_disk_only(self):
        hw = vlan_mapper.collect_hw(
            self.config["hosts"][0], self.config,
            hw_walker=fake_hw_walker(descr_text="%s.1 \"Memory\"\n" % iso_oid(STORAGE_DESCR_OID)))
        self.assertNotIn("disk_pused", hw)
        self.assertIn("ram_util", hw)

    def test_hw_disabled_by_default(self):
        """Sin el flag, el mapper no camina ningun OID de hw ni publica nada."""
        walked = []

        def spy_walker(ip, community, oid, **kwargs):
            walked.append(oid)
            if oid == "1.3.6.1.2.1.2.2.1.2":
                return fixture_text()
            if oid == "1.3.6.1.4.1.14988.1.1.2.1.1.2":
                return ppp_fixture_text()
            raise AssertionError("oid de hw pedido con hw deshabilitado: %s" % oid)

        published = []

        def spy(zabbix_config, host, key, payload):
            published.append(key)
            return True, "sent: 1"

        original = vlan_mapper.publish
        vlan_mapper.publish = spy
        try:
            code = vlan_mapper.run(self.config, walker=spy_walker, ppp_walker=spy_walker)
        finally:
            vlan_mapper.publish = original
        self.assertEqual(code, 0)
        self.assertEqual([key for key in published if key.startswith("system.hw")], [],
                         "hw deshabilitado: ninguna key de hw publicada")

    def test_per_host_enable_publishes_three_scalars(self):
        config = json.loads(json.dumps(vlan_mapper.DEFAULT_CONFIG))
        config["hosts"] = [{"zabbix_host": "SW-EDGE-704", "ip": "192.0.2.66", "hw": True}]
        published = []

        def spy(zabbix_config, host, key, payload):
            published.append((key, payload))
            return True, "sent: 1"

        original = vlan_mapper.publish
        vlan_mapper.publish = spy
        try:
            code = vlan_mapper.run(config, walker=generic_vlan_walker(),
                                   ppp_walker=fake_ppp_walker(ppp_fixture_text()),
                                   hw_walker=fake_hw_walker())
        finally:
            vlan_mapper.publish = original
        self.assertEqual(code, 0)
        hw_keys = [key for key, _payload in published if key.startswith("system.hw")]
        self.assertEqual(sorted(hw_keys), sorted(HW_KEYS))
        payloads = {key: payload for key, payload in published if key.startswith("system.hw")}
        self.assertEqual(float(payloads["system.hw.cpu.avg"]), 15.0)
        self.assertEqual(float(payloads["system.hw.disk.pused"]), 53.0)
        self.assertEqual(float(payloads["system.hw.ram.util"]), 12.8)

    def test_hw_failure_does_not_break_vlan_and_ppp(self):
        config = json.loads(json.dumps(vlan_mapper.DEFAULT_CONFIG))
        config["hosts"] = [{"zabbix_host": "SW-EDGE-704", "ip": "192.0.2.66", "hw": True}]
        published = []

        def spy(zabbix_config, host, key, payload):
            published.append(key)
            return True, "sent: 1"

        original = vlan_mapper.publish
        vlan_mapper.publish = spy
        try:
            code = vlan_mapper.run(config, walker=generic_vlan_walker(),
                                   ppp_walker=fake_ppp_walker(ppp_fixture_text()),
                                   hw_walker=broken_hw_walker)
        finally:
            vlan_mapper.publish = original
        self.assertEqual(code, 0, "un fallo de hw no debe tumbar el lado VLAN/PPP")
        self.assertNotIn("system.hw.cpu.avg", published)

    def test_key_for_hw_purposes(self):
        zabbix = self.config["zabbix"]
        self.assertEqual(vlan_mapper.key_for(zabbix, "hw_cpu"), "system.hw.cpu.avg")
        self.assertEqual(vlan_mapper.key_for(zabbix, "hw_disk"), "system.hw.disk.pused")
        self.assertEqual(vlan_mapper.key_for(zabbix, "hw_ram"), "system.hw.ram.util")


if __name__ == "__main__":
    unittest.main(verbosity=2)
