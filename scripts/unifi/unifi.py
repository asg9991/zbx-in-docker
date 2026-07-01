#!/usr/bin/env python3

import json
import sys

from unifi_api import UniFiAPI


def usage():

    print(
        "Usage:\n"
        "unifi.py devices <url> <user> <pass> <site>\n"
        "unifi.py discovery <url> <user> <pass> <site>"
    )

    sys.exit(1)


if len(sys.argv) != 6:
    usage()

command = sys.argv[1]

url = sys.argv[2]
user = sys.argv[3]
password = sys.argv[4]
site = sys.argv[5]

api = UniFiAPI(
    url,
    user,
    password,
    site
)

if command == "devices":

    print(
        json.dumps(
            {
                "data": api.access_points()
            }
        )
    )

elif command == "discovery":
    aps = []

    for ap in api.access_points():
        aps.append({
            "{#MAC}": ap.get("mac", ""),
            "{#NAME}": ap.get("name", ""),
            "{#IP}": ap.get("ip", ""),
            "{#MODEL}": ap.get("model", ""),
            "{#SITE}": site
        })

    print(json.dumps(aps))

else:

    usage()
