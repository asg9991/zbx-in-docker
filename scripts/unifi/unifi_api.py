#!/usr/bin/env python3

import requests
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class UniFiAPI:

    def __init__(self, url, username, password, site="default"):

        self.url = url.rstrip("/")
        self.site = site

        self.session = requests.Session()
        self.session.verify = False

        r = self.session.post(
            f"{self.url}/api/auth/login",
            json={
                "username": username,
                "password": password
            },
            timeout=30
        )

        r.raise_for_status()

    def get(self, endpoint):

        r = self.session.get(
            self.url + endpoint,
            timeout=30
        )

        r.raise_for_status()

        return r.json()

    def devices(self):

        return self.get(
            f"/proxy/network/api/s/{self.site}/stat/device"
        )["data"]

    def access_points(self):

        aps = []

        for device in self.devices():

            if device.get("type") != "uap":
                continue
            if not device.get("name"):
                continue
            device["id"] = device.get("mac", "")
            aps.append(device)

        return aps
