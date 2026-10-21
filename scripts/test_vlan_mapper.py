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

EXPECTED_VLANS = [
    {"ifdescr": "vlan250", "ifname": "vlan250", "index": 98},
    {"ifdescr": "vlan301", "ifname": "vlan301", "index": 99},
    {"ifdescr": "vlan305", "ifname": "vlan305", "index": 100},
    {"ifdescr": "vlan175", "ifname": "vlan175", "index": 102},
    {"ifdescr": "vlan190", "ifname": "vlan190", "index": 103},
    {"ifdescr": "vlan220", "ifname": "vlan220", "index": 104},
    {"ifdescr": "vlan225", "ifname": "vlan225", "index": 105},
    {"ifdescr": "vlan235", "ifname": "vlan235", "index": 106},
]


def fixture_text():
    with open(FIXTURE, encoding="utf-8") as handle:
        return handle.read()


def fake_walker(text):
    """Walker inyectado: devuelve la fixture sin tocar la red."""
    def walker(ip, community, oid, **kwargs):
        assert ip == "192.0.2.65", ip
        assert community == "public", community
        assert oid == "1.3.6.1.2.1.2.2.1.2", oid
        return text
    return walker


class TestVlanMapper(unittest.TestCase):

    def setUp(self):
        self.text = fixture_text()
        self.config = json.loads(json.dumps(vlan_mapper.DEFAULT_CONFIG))
        self.config["hosts"] = [{"zabbix_host": "SW-EDGE-703", "ip": "192.0.2.65"}]

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

    # --- filtro -----------------------------------------------------------
    def test_filter_keeps_the_8_vlans(self):
        rows = vlan_mapper.parse_walk_output(self.text)
        vlans = vlan_mapper.filter_vlans(
            rows,
            pattern=self.config["vlan"]["pattern"],
            exclude_pattern=self.config["vlan"]["exclude_pattern"],
            ids=self.config["vlan"]["ids"],
        )
        self.assertEqual(vlans, EXPECTED_VLANS)

    def test_filter_drops_pppoe(self):
        rows = vlan_mapper.parse_walk_output(self.text)
        vlans = vlan_mapper.filter_vlans(
            rows,
            pattern=self.config["vlan"]["pattern"],
            exclude_pattern=self.config["vlan"]["exclude_pattern"],
            ids=self.config["vlan"]["ids"],
        )
        names = [vlan["ifdescr"] for vlan in vlans]
        self.assertEqual(len([name for name in names if name.startswith("pppoe-")]), 0)
        self.assertEqual(len(vlans), 8)

    def test_filter_drops_vlan_outside_whitelist(self):
        """vlan999 (ifIndex 101) matchea el pattern pero no esta en la whitelist."""
        rows = vlan_mapper.parse_walk_output(self.text)
        vlans = vlan_mapper.filter_vlans(
            rows,
            pattern=self.config["vlan"]["pattern"],
            exclude_pattern=self.config["vlan"]["exclude_pattern"],
            ids=self.config["vlan"]["ids"],
        )
        self.assertNotIn("vlan999", [vlan["ifdescr"] for vlan in vlans])

    # --- payload ----------------------------------------------------------
    def test_payload_shape_is_the_t1_contract(self):
        vlans, _rows, error = vlan_mapper.collect_host(
            self.config["hosts"][0], self.config, walker=fake_walker(self.text)
        )
        self.assertIsNone(error)
        payload = vlan_mapper.build_payload(vlans)
        parsed = json.loads(payload)
        self.assertIsInstance(parsed, list, "el JSON debe ser un array")
        self.assertEqual(len(parsed), 8)
        for entry in parsed:
            self.assertEqual(sorted(entry.keys()), ["ifdescr", "ifname", "index"])
            self.assertIsInstance(entry["index"], int)
        self.assertEqual(parsed[0], {"ifdescr": "vlan250", "ifname": "vlan250", "index": 98})

    def test_payload_is_small(self):
        """El motivo de todo el diseno: el JSON tiene que entrar de sobra en 64 KB."""
        vlans, _rows, _error = vlan_mapper.collect_host(
            self.config["hosts"][0], self.config, walker=fake_walker(self.text)
        )
        payload = vlan_mapper.build_payload(vlans)
        self.assertLess(len(payload), 1024)
        self.assertLess(len(payload), 65535)

    # --- flujo completo ---------------------------------------------------
    def test_run_dry_run_does_not_publish(self):
        published = []

        def spy(zabbix_config, host, payload):
            published.append((host, payload))
            return True, "ok"

        original = vlan_mapper.publish
        vlan_mapper.publish = spy
        try:
            code = vlan_mapper.run(self.config, dry_run=True, walker=fake_walker(self.text))
        finally:
            vlan_mapper.publish = original
        self.assertEqual(code, 0)
        self.assertEqual(published, [], "en dry-run no se debe publicar nada")

    def test_run_publishes_and_is_idempotent(self):
        published = []

        def spy(zabbix_config, host, payload):
            published.append((host, payload))
            return True, "sent: 1"

        original = vlan_mapper.publish
        vlan_mapper.publish = spy
        try:
            self.assertEqual(vlan_mapper.run(self.config, walker=fake_walker(self.text)), 0)
            self.assertEqual(vlan_mapper.run(self.config, walker=fake_walker(self.text)), 0)
        finally:
            vlan_mapper.publish = original
        self.assertEqual(len(published), 2)
        self.assertEqual(published[0], published[1], "dos corridas deben publicar lo mismo")
        host, payload = published[0]
        self.assertEqual(host, "SW-EDGE-703")
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

        def spy(zabbix_config, host, payload):
            published.append(host)
            return True, "sent: 1"

        original = vlan_mapper.publish
        vlan_mapper.publish = spy
        try:
            code = vlan_mapper.run(config, walker=walker)
        finally:
            vlan_mapper.publish = original
        self.assertEqual(code, 1, "un CHR caido tiene que quedar registrado como fallo")
        self.assertEqual(published, ["SW-EDGE-703"], "el CHR vivo se publica igual")

    def test_host_without_ip_is_skipped(self):
        config = json.loads(json.dumps(self.config))
        config["hosts"] = [{"zabbix_host": "SW-EDGE-701", "ip": None}]
        self.assertEqual(vlan_mapper.run(config, dry_run=True), 1)


if __name__ == "__main__":
    unittest.main(verbosity=2)
