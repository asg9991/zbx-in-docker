"""Definiciones canonicas de las consultas a la API de Zabbix.

Un solo lugar para el body, root_selector y columnas. Los dashboards solo
referencian el nombre (`query: <clave>`) y `scripts/gen_queries.py` inyecta
el resto. Si cambia el API, se ajusta aca y se regeneran todos.
"""

import json


def _trigger(params, root, columns):
    return {
        "method": "trigger.get",
        "params": params,
        "root_selector": root,
        "columns": columns,
    }


COLS_BASICAS = [
    {"selector": "hosts.0.host", "text": "Equipo", "type": "string"},
]
COLS_TABLA = [
    {"selector": "Equipo", "text": "Equipo", "type": "string"},
    {"selector": "Problema", "text": "Problema", "type": "string"},
    {"selector": "Gravedad", "text": "Gravedad", "type": "string"},
    {"selector": "Antiguedad", "text": "Antiguedad", "type": "string"},
]

_ROOT_TABLA = (
    '$map(result, function($v){ '
    '{"Equipo": $v.hosts[0].host, "Problema": $v.description, "Gravedad": $v.priority, '
    '"Antiguedad": ($millis() - $number($v.lastchange)*1000) > 86400000 '
    '? $string($round(($millis() - $number($v.lastchange)*1000)/86400000)) & " d" '
    ': $string($round(($millis() - $number($v.lastchange)*1000)/3600000)) & " h"} })'
)

_TRIGGER_COMUN = {
    "output": ["triggerid", "description", "priority", "lastchange"],
    "selectHosts": ["host"],
    "only_true": True,
    "monitored": True,
    "sortfield": "priority",
    "sortorder": "DESC",
    "limit": 100,
}

QUERIES = {
    # --- conteos para KPIs (una fila por problema, el panel cuenta) ---
    "problemas_graves": _trigger(
        dict(_TRIGGER_COMUN, filter={"priority": [4, 5]}),
        "result", COLS_BASICAS),
    "avisos": _trigger(
        dict(_TRIGGER_COMUN, filter={"priority": [2, 3]}),
        "result", COLS_BASICAS),
    "problemas_altos_tabla": _trigger(
        dict(_TRIGGER_COMUN, filter={"priority": [4, 5]}),
        _ROOT_TABLA, COLS_TABLA),
    "avisos_tabla": _trigger(
        dict(_TRIGGER_COMUN, filter={"priority": [2, 3]}),
        _ROOT_TABLA, COLS_TABLA),
    "problemas_todos_tabla": _trigger(
        dict(_TRIGGER_COMUN, filter={"priority": [2, 3, 4, 5]}),
        _ROOT_TABLA, COLS_TABLA),
    # --- salud del monitoreo ---
    "items_sin_datos": {
        "method": "item.get",
        "params": {"output": ["itemid", "name", "error"], "selectHosts": ["host"],
                   "filter": {"state": 1}, "sortfield": "name", "sortorder": "ASC",
                   "limit": 500},
        "root_selector": "result",
        "columns": [
            {"selector": "hosts.0.host", "text": "Equipo", "type": "string"},
            {"selector": "name", "text": "Item sin datos", "type": "string"},
            {"selector": "error", "text": "Motivo", "type": "string"},
        ],
    },
    "hosts_sin_respuesta": {
        "method": "hostinterface.get",
        "params": {"output": ["hostid", "error"], "selectHosts": ["host"],
                   "filter": {"available": 2}, "limit": 50},
        "root_selector": "result",
        "columns": [
            {"selector": "hosts.0.host", "text": "Equipo", "type": "string"},
            {"selector": "error", "text": "Motivo", "type": "string"},
        ],
    },
    "equipos_caidos_kpi": {
        "method": "hostinterface.get",
        "params": {"output": ["hostid"], "selectHosts": ["host"],
                   "filter": {"available": 2}, "limit": 200},
        "root_selector": "result",
        "columns": COLS_BASICAS,
    },
    "cola": {
        "method": "item.get",
        "params": {"output": ["lastvalue"], "filter": {"key_": "zabbix[queue]"}},
        "root_selector": "result",
        "columns": [{"selector": "lastvalue", "text": "cola", "type": "number"}],
    },
    # --- drill-down por equipo (usa la variable ${hostid} del dashboard) ---
    "problemas_host": {
        "method": "problem.get",
        "params": {"output": ["eventid", "name", "severity", "clock"],
                   "hostids": ["${hostid}"], "recent": False, "limit": 100},
        "root_selector": (
            '$map(result, function($v){ {"Problema": $v.name, "Gravedad": $string($v.severity), '
            '"Antiguedad": ($millis() - $number($v.clock)*1000) > 86400000 '
            '? $string($round(($millis() - $number($v.clock)*1000)/86400000)) & " d" '
            ': $string($round(($millis() - $number($v.clock)*1000)/3600000)) & " h"} })'
        ),
        "columns": [
            {"selector": "Problema", "text": "Problema", "type": "string"},
            {"selector": "Gravedad", "text": "Gravedad", "type": "string"},
            {"selector": "Antiguedad", "text": "Antiguedad", "type": "string"},
        ],
    },
    # --- mapa: detalle de problemas de los equipos del mapa ---
    "problemas_mapa": {
        "method": "problem.get",
        "params": {"output": ["eventid", "name", "severity", "clock"],
                   "recent": False, "limit": 200},
        "root_selector": (
            '$map(result, function($v){ {"Problema": $v.name, "Gravedad": $string($v.severity), '
            '"Antiguedad": ($millis() - $number($v.clock)*1000) > 86400000 '
            '? $string($round(($millis() - $number($v.clock)*1000)/86400000)) & " d" '
            ': $string($round(($millis() - $number($v.clock)*1000)/3600000)) & " h"} })'
        ),
        "columns": [
            {"selector": "Problema", "text": "Problema", "type": "string"},
            {"selector": "Gravedad", "text": "Gravedad", "type": "string"},
            {"selector": "Antiguedad", "text": "Antiguedad", "type": "string"},
        ],
    },
}


def target(name: str, refid: str = "A") -> dict:
    """Devuelve el target de Infinity completo para un nombre logico."""
    q = QUERIES[name]
    body = {"jsonrpc": "2.0", "method": q["method"], "params": q["params"], "id": 1}
    return {
        "refId": refid,
        "datasource": {"type": "yesoreyeram-infinity-datasource", "uid": "zabbix-api"},
        "type": "json",
        "source": "url",
        "format": "table",
        "parser": "backend",
        "root_selector": q["root_selector"],
        "filters": [],
        "url": "http://zabbix-web:8080/api_jsonrpc.php",
        "url_options": {
            "method": "POST",
            "data": json.dumps(body),
            "headers": [{"key": "Content-Type", "value": "application/json-rpc"}],
        },
        "columns": q["columns"],
    }


def estado_host(hostid: str, idx: int) -> dict:
    """Estado de un equipo para el mapa: una fila con color/estado unicos.

    Usa `problem.get`, que es la fuente autoritativa. `trigger.get` devuelve
    `value` inconsistente (0 en triggers que estan en problema) y hacia que el
    mapa mostrara verde con problemas activos.
    """
    body = {"jsonrpc": "2.0", "method": "problem.get", "params": {
        "output": ["eventid", "name", "severity"],
        "hostids": [hostid],
        "recent": False,
        "limit": 100,
    }, "id": 1}
    root = (
        f'$map([1], function($x){{ {{"c_{idx}": $count(result) > 0 ? 1 : 0, '
        f'"s_{idx}": $count(result) > 0 '
        f'? $string($count(result)) & " problemas" : "OK"}} }})'
    )
    return {
        "refId": f"q{idx}",
        "datasource": {"type": "yesoreyeram-infinity-datasource", "uid": "zabbix-api"},
        "type": "json",
        "source": "url",
        "format": "table",
        "parser": "backend",
        "root_selector": root,
        "filters": [],
        "url": "http://zabbix-web:8080/api_jsonrpc.php",
        "url_options": {
            "method": "POST",
            "data": json.dumps(body),
            "headers": [{"key": "Content-Type", "value": "application/json-rpc"}],
        },
        "columns": [
            {"selector": f"c_{idx}", "text": f"c_{idx}", "type": "number"},
            {"selector": f"s_{idx}", "text": f"s_{idx}", "type": "string"},
        ],
    }


def problemas_de(hostids) -> dict:
    """Detalle de problemas acotado a los equipos del mapa."""
    t = target("problemas_mapa")
    body = {"jsonrpc": "2.0", "method": "problem.get", "params": {
        "output": ["eventid", "name", "severity", "clock"],
        "hostids": list(hostids),
        "recent": False,
        "limit": 200,
    }, "id": 1}
    t["url_options"]["data"] = json.dumps(body)
    return t
