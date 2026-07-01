#!/usr/bin/env python3

import os
import sys

BASE = "/usr/lib/zabbix/externalscripts/unifi"

sys.path.insert(0, BASE)

os.execv(
    f"{BASE}/unifi.py",
    ["unifi.py"] + sys.argv[1:]
)
