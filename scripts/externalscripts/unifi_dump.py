#!/usr/bin/python3

import requests
import urllib3
import json

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

URL = "https://192.0.2.40"
USER = "admin"
PASS = "change_me"

s = requests.Session()
s.verify = False

r = s.post(
    f"{URL}/api/auth/login",
    json={
        "username": USER,
        "password": PASS
    }
)

r.raise_for_status()

devices = s.get(
    f"{URL}/proxy/network/api/s/default/stat/device"
)

devices.raise_for_status()

print(devices.text)
