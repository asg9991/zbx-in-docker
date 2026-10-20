#!/usr/bin/env python3
"""Export live Zabbix templates to the repo's `zabbix_export` YAML format.

Why: the repo keeps one YAML per template under templates/. When a template is
edited live (via API or UI) the repo copy drifts. This script pulls the live
definition and writes a faithful, re-importable YAML so the repo always has a
backup of what is actually running.

Usage:
    export API_URL TOKEN TEMPLATE_ID OUTFILE [--label LABEL]

Example:
    scripts/zabbix_template_export.py \
        https://127.0.0.1/api_jsonrpc.php "$ZABBIX_TOKEN" 10870 \
        templates/template_ppp_dedicated_users.yaml

Notes:
  * Zabbix 7.4 renamed the API parameters: `template.get` ignores `ids`
    (use `templateids`) and returns discovery rules under `discoveryRules`.
  * The API has no template-export method, so the YAML is built from
    template.get + item.get. Keep the output key names aligned with the
    Zabbix 7.4 frontend export format used by the existing repo files.
"""

import json
import sys
import urllib.request

API_TYPES = {
    0: "ZABBIX", 1: "SNMPV1", 2: "TRAPPER", 3: "SIMPLE", 4: "SNMPV2",
    5: "INTERNAL", 6: "SNMPV3", 7: "ZABBIX_ACTIVE", 8: "TRAP", 9: "HTTP_TEST",
    10: "EXTERNAL", 11: "DB_MONITOR", 12: "IPMI", 13: "SSH", 14: "TELNET",
    15: "CALCULATED", 16: "JMX", 17: "SNMP_TRAP", 18: "DEPENDENT",
    19: "HTTP_AGENT", 20: "SNMP_AGENT", 21: "SCRIPT", 22: "BROWSER",
}
VALUE_TYPES = {
    0: "FLOAT", 1: "CHARACTER", 2: "LOG", 3: "UNSIGNED", 4: "TEXT", 5: "BINARY",
}
STATUS = {0: "enabled", 1: "DISABLED"}
# Zabbix 7.4 preprocessing type codes. Verified empirically against the live
# site-a DB (item_preproc.type) for the steps used by the MikroTik templates:
#   1 = MULTIPLIER (params: factor)
#   10 = CHANGE_PER_SECOND (no params)
#   20 = DISCARD_UNCHANGED_HEARTBEAT (params: interval)
#   28 = SNMP_WALK_VALUE (params: oid, '0')
#   29 = SNMP_WALK_TO_JSON (params: macro, oid, '0', ...)
# The 7.4 codes are NOT the 6.x ones. Codes not listed here are rendered as
# PREPROC_<n> so an unmapped step is visible instead of silently wrong.
PREPROCESS_TYPE = {
    1: "MULTIPLIER",
    10: "CHANGE_PER_SECOND",
    20: "DISCARD_UNCHANGED_HEARTBEAT",
    28: "SNMP_WALK_VALUE",
    29: "SNMP_WALK_TO_JSON",
}


def api_call(api_url, token, method, params, insecure=False, _id=[0]):
    _id[0] += 1
    body = json.dumps(
        {"jsonrpc": "2.0", "method": method, "params": params, "id": _id[0]}
    ).encode()
    req = urllib.request.Request(
        api_url,
        data=body,
        headers={
            "Content-Type": "application/json-rpc",
            "Authorization": f"Bearer {token}",
        },
    )
    ctx = None
    if insecure:
        import ssl
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
    with urllib.request.urlopen(req, timeout=120, context=ctx) as resp:
        payload = json.load(resp)
    if "error" in payload:
        raise SystemExit(f"API error in {method}: {payload['error']}")
    return payload["result"]


def yaml_scalar(value):
    """Render a scalar the way the repo YAML files do."""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int):
        return str(value)
    if value is None:
        return "''"
    text = str(value)
    if text == "":
        return "''"
    if "\n" in text:
        return "'" + text.replace("'", "''") + "'"
    needs_quote = (
        text[0] in "!&*?|>%@`{}[],#\"' "
        or text[-1] == " "
        or ": " in text
        or " #" in text
        or text in ("yes", "no", "true", "false", "null", "on", "off", "~")
        or _is_numeric(text)
    )
    if needs_quote:
        return "'" + text.replace("'", "''") + "'"
    return text


def _is_numeric(text):
    try:
        float(text)
        return True
    except ValueError:
        return False


def yaml_block(value, indent):
    """Render a dict or list as a YAML fragment (already indented)."""
    pad = " " * indent
    out = []
    if isinstance(value, dict):
        for key, val in value.items():
            if val is None:
                continue
            if isinstance(val, str) and "\n" in val:
                out.append(f"{pad}{key}: |-")
                for line in val.rstrip("\n").split("\n"):
                    out.append(f"{pad}  {line}" if line else "")
            elif isinstance(val, (dict, list)) and val:
                out.append(f"{pad}{key}:")
                out.append(yaml_block(val, indent + 2))
            else:
                out.append(f"{pad}{key}: {yaml_scalar(val)}")
    elif isinstance(value, list):
        for entry in value:
            if isinstance(entry, dict):
                first = True
                for key, val in entry.items():
                    if val is None:
                        continue
                    prefix = f"{pad}- " if first else f"{pad}  "
                    if isinstance(val, str) and "\n" in val:
                        out.append(f"{prefix}{key}: |-")
                        for line in val.rstrip("\n").split("\n"):
                            out.append(f"{pad}    {line}" if line else "")
                    elif isinstance(val, (dict, list)) and val:
                        out.append(f"{prefix}{key}:")
                        out.append(yaml_block(val, indent + 4))
                    else:
                        out.append(f"{prefix}{key}: {yaml_scalar(val)}")
                    first = False
            else:
                out.append(f"{pad}- {yaml_scalar(entry)}")
    return "\n".join(out)


def preprocessing(steps):
    if not steps:
        return None
    out = []
    for step in steps:
        code = int(step.get("type", 0))
        entry = {"type": PREPROCESS_TYPE.get(code, f"PREPROC_{code}")}
        # The API calls it "parameters", the DB dump calls it "params".
        params = step.get("parameters")
        if params is None:
            params = step.get("params")
        if params:
            entry["parameters"] = params
        if step.get("error_handler"):
            entry["error_handler"] = step["error_handler"]
        out.append(entry)
    return out


def convert_item(item, masters_by_id, protos_by_master):
    out = {
        "uuid": item.get("uuid"),
        "name": item.get("name"),
        "type": API_TYPES.get(int(item.get("type", 0)), item.get("type")),
        "key": item.get("key_"),
    }
    if item.get("snmp_oid"):
        out["snmp_oid"] = item["snmp_oid"]
    if item.get("delay") not in (None, "0", ""):
        out["delay"] = item["delay"]
    if item.get("timeout") not in (None, "", "0"):
        out["timeout"] = item["timeout"]
    if item.get("status") == "1":
        out["status"] = "DISABLED"
    if item.get("value_type") is not None:
        out["value_type"] = VALUE_TYPES.get(int(item["value_type"]), item["value_type"])
    if item.get("units"):
        out["units"] = item["units"]
    if item.get("history") not in (None, "", "0"):
        out["history"] = item["history"]
    if item.get("trends") not in (None, "", "0"):
        out["trends"] = item["trends"]
    if item.get("description"):
        out["description"] = item["description"].rstrip()
    steps = preprocessing(item.get("preprocessing"))
    if steps:
        out["preprocessing"] = steps
    master = masters_by_id.get(item.get("master_itemid"))
    if master:
        out["master_item"] = {"key": master.get("key_")}
    if item.get("prototypes"):
        out["item_prototypes"] = [
            convert_item(p, masters_by_id, {}) for p in item["prototypes"]
        ]
    if item.get("graph_prototypes"):
        out["graph_prototypes"] = [
            convert_graph_proto(g) for g in item["graph_prototypes"]
        ]
    if item.get("trigger_prototypes"):
        out["trigger_prototypes"] = [
            convert_trigger_proto(t) for t in item["trigger_prototypes"]
        ]
    return {k: v for k, v in out.items() if v not in (None, [], {})}


def convert_graph_proto(g):
    out = {"uuid": g.get("uuid"), "name": g.get("name")}
    items = []
    for gi in g.get("graph_items", []):
        entry = {}
        if gi.get("sortorder") is not None:
            entry["sortorder"] = gi.get("sortorder")
        if gi.get("color"):
            entry["color"] = gi.get("color")
        if gi.get("drawtype"):
            entry["drawtype"] = gi.get("drawtype")
        item = gi.get("item") or {}
        if item.get("key"):
            entry["item"] = {"host": item.get("host"), "key": item.get("key")}
        items.append(entry)
    if items:
        out["graph_items"] = items
    return {k: v for k, v in out.items() if v is not None}


def convert_trigger_proto(t):
    out = {"uuid": t.get("uuid"), "name": t.get("name"), "expression": t.get("expression")}
    if t.get("priority"):
        out["priority"] = t["priority"]
    if t.get("description"):
        out["description"] = t["description"].rstrip()
    return {k: v for k, v in out.items() if v is not None}


def convert_discovery_rule(rule, masters_by_id):
    out = {
        "uuid": rule.get("uuid"),
        "name": rule.get("name"),
        "type": API_TYPES.get(int(rule.get("type", 0)), rule.get("type")),
        "key": rule.get("key_"),
    }
    if rule.get("snmp_oid"):
        out["snmp_oid"] = rule["snmp_oid"]
    if rule.get("delay") not in (None, "", "0"):
        out["delay"] = rule["delay"]
    if rule.get("lifetime") not in (None, "", "0"):
        out["lifetime"] = rule["lifetime"]
    if rule.get("status") == "1":
        out["status"] = "DISABLED"
    if rule.get("description"):
        out["description"] = rule["description"].rstrip()
    steps = preprocessing(rule.get("preprocessing"))
    if steps:
        out["preprocessing"] = steps
    master = masters_by_id.get(rule.get("master_itemid"))
    if master:
        out["master_item"] = {"key": master.get("key_")}
    if rule.get("item_prototypes"):
        out["item_prototypes"] = [
            convert_item(p, masters_by_id, {}) for p in rule["item_prototypes"]
        ]
    if rule.get("graph_prototypes"):
        out["graph_prototypes"] = [
            convert_graph_proto(g) for g in rule["graph_prototypes"]
        ]
    if rule.get("trigger_prototypes"):
        out["trigger_prototypes"] = [
            convert_trigger_proto(t) for t in rule["trigger_prototypes"]
        ]
    macros = rule.get("discoverymacros") or rule.get("discovery_macros")
    if macros:
        out["discovery_macros"] = [
            {"macro": m.get("macro"), "path": m.get("path")} for m in macros
        ]
    filt = rule.get("filter")
    if filt:
        out["filters"] = [
            {"macro": f.get("macro"), "value": f.get("value"), "op": f.get("op")}
            for f in (filt if isinstance(filt, list) else [filt])
        ]
    return {k: v for k, v in out.items() if v not in (None, [], {})}


def render_db_json(doc, outfile, label=None):
    """Render the DB-derived template definition (item_preproc/item_condition).

    The Zabbix 7.4 API does not expose LLD preprocessing, filters or item
    prototypes for discovery rules, so a complete backup has to come from the
    database. `scripts/zabbix_template_dump.sql` produces the JSON consumed
    here.
    """
    tpl = doc["template"]
    masters = {}
    for item in doc.get("items", []):
        masters[item["itemid"]] = item

    def master_key(mid):
        m = masters.get(mid)
        return {"key": m["key_"]} if m else None

    def item_block(item, is_proto=False):
        out = {
            "uuid": item.get("uuid"),
            "name": item.get("name"),
            "type": API_TYPES.get(int(item.get("type", 0)), item.get("type")),
            "key": item.get("key_"),
        }
        if item.get("snmp_oid"):
            out["snmp_oid"] = item["snmp_oid"]
        if item.get("delay") not in (None, "", "0"):
            out["delay"] = item["delay"]
        if item.get("timeout") not in (None, "", "0"):
            out["timeout"] = item["timeout"]
        if int(item.get("status", 0)) == 1:
            out["status"] = "DISABLED"
        if item.get("value_type") is not None:
            out["value_type"] = VALUE_TYPES.get(int(item["value_type"]), item["value_type"])
        if item.get("units"):
            out["units"] = item["units"]
        if item.get("history") not in (None, "", "0"):
            out["history"] = item["history"]
        if item.get("trends") not in (None, "", "0"):
            out["trends"] = item["trends"]
        if item.get("description"):
            out["description"] = item["description"].rstrip()
        steps = preprocessing(item.get("preprocessing"))
        if steps:
            out["preprocessing"] = steps
        mk = master_key(item.get("master_itemid"))
        if mk:
            out["master_item"] = mk
        return {k: v for k, v in out.items() if v not in (None, [], {})}

    items_out = [item_block(i) for i in doc.get("items", [])]

    rules_out = []
    for rule in doc.get("discovery_rules", []):
        out = {
            "uuid": rule.get("uuid"),
            "name": rule.get("name"),
            "type": API_TYPES.get(int(rule.get("type", 0)), rule.get("type")),
            "key": rule.get("key_"),
        }
        if rule.get("snmp_oid"):
            out["snmp_oid"] = rule["snmp_oid"]
        if rule.get("delay") not in (None, "", "0"):
            out["delay"] = rule["delay"]
        if rule.get("lifetime") not in (None, "", "0"):
            out["lifetime"] = rule["lifetime"]
        if int(rule.get("status", 0)) == 1:
            out["status"] = "DISABLED"
        if rule.get("description"):
            out["description"] = rule["description"].rstrip()
        steps = preprocessing(rule.get("preprocessing"))
        if steps:
            out["preprocessing"] = steps
        mk = master_key(rule.get("master_itemid"))
        if mk:
            out["master_item"] = mk
        protos = [item_block(p) for p in (rule.get("item_prototypes") or [])]
        if protos:
            out["item_prototypes"] = protos
        filters = rule.get("filters") or []
        if filters:
            out["filters"] = [
                {
                    "macro": f.get("macro"),
                    "value": f.get("value"),
                    "op": {2: "CONTAINS", 3: "EQUALS", 4: "REGEX", 5: "NOT_CONTAINS",
                           6: "NOT_EQUALS", 7: "NOT_REGEX", 8: "MATCHES_REGEX",
                           9: "NOT_MATCHES_REGEX"}.get(int(f.get("op", 0)), f.get("op")),
                }
                for f in filters
            ]
        rules_out.append({k: v for k, v in out.items() if v not in (None, [], {})})

    template = {
        "uuid": tpl.get("uuid"),
        "template": tpl.get("name"),
        "name": tpl.get("name"),
        "description": (tpl.get("description") or "").rstrip(),
        "items": items_out,
        "discovery_rules": rules_out,
        "macros": [
            {
                "macro": m.get("macro"),
                "value": m.get("value"),
                "description": (m.get("description") or "").rstrip(),
            }
            for m in doc.get("macros", [])
        ],
    }
    if label:
        template["description"] = (
            (template["description"] + "\n\n" if template["description"] else "") + label
        )
    payload = {"zabbix_export": {"version": "7.4", "templates": [template]}}
    hosts = ", ".join(h.get("host", "") for h in doc.get("hosts", []))
    header = (
        f"# Live export of Zabbix template {tpl.get('templateid')} ('{tpl.get('name')}').\n"
        f"# Source: Zabbix 7.4 database (item_preproc / item_condition / item_discovery).\n"
        f"# The 7.4 API does not expose LLD preprocessing, filters or prototypes.\n"
        f"# Template hosts: {hosts}\n"
    )
    with open(outfile, "w") as fh:
        fh.write(header)
        fh.write(yaml_block(payload, 0))
        fh.write("\n")
    print(f"written: {outfile}")


def main():
    if "--db-json" in sys.argv:
        idx = sys.argv.index("--db-json")
        doc = json.load(open(sys.argv[idx + 1]))
        outfile = sys.argv[idx + 2]
        label = None
        if "--label" in sys.argv:
            label = sys.argv[sys.argv.index("--label") + 1]
        render_db_json(doc, outfile, label)
        return

    if len(sys.argv) < 5:
        raise SystemExit(__doc__)
    api_url, token, template_id, outfile = sys.argv[1:5]
    label = None
    if "--label" in sys.argv:
        label = sys.argv[sys.argv.index("--label") + 1]
    insecure = "--insecure" in sys.argv

    templates = api_call(
        api_url, token, "template.get",
        {
            "templateids": [template_id],
            "selectItems": ["itemid", "key_", "name", "type", "snmp_oid", "delay", "timeout",
                            "status", "master_itemid", "value_type", "units",
                            "history", "trends", "description", "uuid"],
            "selectDiscoveryRules": ["itemid", "key_", "name", "type", "snmp_oid", "delay",
                                     "lifetime", "status", "master_itemid",
                                     "description", "uuid"],
            "selectMacros": ["macro", "value", "description", "type"],
            "selectHosts": ["hostid", "host", "name"],
            "selectValueMaps": ["name", "mappings"],
        },
        insecure=insecure,
    )
    if not templates:
        raise SystemExit(f"template {template_id} not found")
    tpl = templates[0]

    # Deep detail: preprocessing, filters, macros, prototypes live on item.get.
    item_ids = [i["itemid"] for i in tpl.get("items", [])]
    rule_ids = [r["itemid"] for r in tpl.get("discoveryRules", [])]
    deep = {}
    for batch_start in range(0, len(item_ids + rule_ids), 50):
        batch = (item_ids + rule_ids)[batch_start:batch_start + 50]
        got = api_call(
            api_url, token, "item.get",
            {
                "itemids": batch,
                "selectPreprocessing": True,
                "selectFilter": True,
                "selectDiscoveryMacros": True,
                "selectPrototypes": True,
                "selectGraphPrototypes": True,
                "selectTriggerPrototypes": True,
            },
            insecure=insecure,
        )
        for obj in got:
            deep[obj["itemid"]] = obj

    masters = {}
    for obj in deep.values():
        if obj.get("key_"):
            masters[obj["itemid"]] = obj

    items_out = []
    for item in tpl.get("items", []):
        merged = dict(item)
        merged.update({k: v for k, v in deep.get(item["itemid"], {}).items()
                       if k in ("preprocessing", "filter", "discoverymacros",
                                "prototypes", "graph_prototypes", "trigger_prototypes")})
        items_out.append(convert_item(merged, masters, {}))

    rules_out = []
    for rule in tpl.get("discoveryRules", []):
        merged = dict(rule)
        merged.update({k: v for k, v in deep.get(rule["itemid"], {}).items()
                       if k in ("preprocessing", "filter", "discoverymacros",
                                "prototypes", "graph_prototypes", "trigger_prototypes")})
        rules_out.append(convert_discovery_rule(merged, masters))

    groups = sorted({g for h in tpl.get("hosts", []) for g in []})
    doc = {
        "zabbix_export": {
            "version": "7.4",
            "templates": [
                {
                    "uuid": tpl.get("uuid"),
                    "template": tpl.get("name"),
                    "name": tpl.get("name"),
                    "description": (tpl.get("description") or "").rstrip(),
                    "items": items_out,
                    "discovery_rules": rules_out,
                    "macros": [
                        {
                            "macro": m.get("macro"),
                            "value": m.get("value"),
                            "description": (m.get("description") or "").rstrip(),
                        }
                        for m in tpl.get("macros", [])
                    ],
                }
            ],
        }
    }
    if label:
        doc["zabbix_export"]["templates"][0]["description"] = (
            (doc["zabbix_export"]["templates"][0]["description"] + "\n\n" if
             doc["zabbix_export"]["templates"][0]["description"] else "") + label
        )

    header = (
        f"# Live export of Zabbix template {template_id} ('{tpl.get('name')}').\n"
        f"# Generated by scripts/zabbix_template_export.py — do not hand-edit.\n"
        f"# Template hosts: {', '.join(h.get('host', '') for h in tpl.get('hosts', []))}\n"
    )
    with open(outfile, "w") as fh:
        fh.write(header)
        fh.write(yaml_block(doc, 0))
        fh.write("\n")
    print(f"written: {outfile}")


if __name__ == "__main__":
    main()
