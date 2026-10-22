CREATE FUNCTION
--- hostmacro del template 10869 y 10870 + los 7 CHR
-- hostmacro

INSERT INTO hostmacro (hostmacroid, hostid, macro, value, description, type, automatic) VALUES ('0', '{$site-a.VLAN.MATCHES}', '^$', '10869', '0', 'Default fail-safe: sin lista propia el host NO descubre ninguna VLAN. Cada CHR define la suya; la union de VLANs de site-a vive en {$site-a.VLAN.UNIVERSE}.', '8228');
-- hostmacro

INSERT INTO hostmacro (hostmacroid, hostid, macro, value, description, type, automatic) VALUES ('0', '{$site-a.VLAN.NOT_MATCHES}', '^pppoe-.*', '10869', '0', 'LLD exclude: pppoe churn (applied to both {#IFDESCR} and {#IFNAME}).', '8229');
-- hostmacro

INSERT INTO hostmacro (hostmacroid, hostid, macro, value, description, type, automatic) VALUES ('0', '{$site-a.VLAN.MATCHES}', '^(vlan175|vlan190|vlan220|vlan225|vlan235)$', '10845', '0', 'Scoped to assigned VLANs', '8233');
-- hostmacro

INSERT INTO hostmacro (hostmacroid, hostid, macro, value, description, type, automatic) VALUES ('0', '{$site-a.VLAN.MATCHES}', '^(vlan125|vlan130|vlan135|vlan150|vlan165|vlan170)$', '10848', '0', 'Scoped to assigned VLANs', '8234');
-- hostmacro

INSERT INTO hostmacro (hostmacroid, hostid, macro, value, description, type, automatic) VALUES ('0', '{$site-a.VLAN.MATCHES}', '^(vlan111|vlan115|vlan185|vlan205|vlan210|vlan230)$', '10846', '0', 'Scoped to assigned VLANs', '8235');
-- hostmacro

INSERT INTO hostmacro (hostmacroid, hostid, macro, value, description, type, automatic) VALUES ('0', '{$PPP.DEDICATED.MATCHES}', '(?i)^(<pppoe-coopvinia>|<pppoe-multijactosa>|<pppoe-franciscosellart>|<pppoe-arrebeef>|<pppoe-garfin>|<pppoe-buratovichhnos>|<pppoe-southernseeds>|<pppoe-patrullarural>|Enlace-patrullarural)$', '10870', '0', 'LLD whitelist PPP dedicados UP 2026-10-10: match exacto case-insensitive sobre {#PPP_NAME}. Cubre variantes garfin/agrosa/laesperanza y buratovich/* + Enlace-patrullarural y futuro <pppoe-patrullarural>.', '8236');
-- hostmacro

INSERT INTO hostmacro (hostmacroid, hostid, macro, value, description, type, automatic) VALUES ('0', '{$site-a.VLAN.MATCHES}', '^(vlan105|vlan110|vlan140|vlan145|vlan155|vlan195|vlan215|vlan310|vlan315|vlan320)$', '10878', '0', '', '8241');
-- hostmacro

INSERT INTO hostmacro (hostmacroid, hostid, macro, value, description, type, automatic) VALUES ('0', '{$NET.IF.IFDESCR.MATCHES}', '^(PUBLICA|USUARIOS|NAS)$', '10878', '0', '', '8244');
-- hostmacro

INSERT INTO hostmacro (hostmacroid, hostid, macro, value, description, type, automatic) VALUES ('0', '{$site-a.VLAN.MATCHES}', '^(vlan100|vlan120|vlan160|vlan180|vlan240|vlan245)$', '10877', '0', '', '8243');
-- hostmacro

INSERT INTO hostmacro (hostmacroid, hostid, macro, value, description, type, automatic) VALUES ('0', '{$site-a.VLAN.MATCHES}', '^$', '10844', '0', '', '8242');
-- hostmacro

INSERT INTO hostmacro (hostmacroid, hostid, macro, value, description, type, automatic) VALUES ('0', '{$NET.IF.IFDESCR.MATCHES}', '^(PUBLICA|USUARIOS|NAS)$', '10845', '0', '', '8247');
-- hostmacro

INSERT INTO hostmacro (hostmacroid, hostid, macro, value, description, type, automatic) VALUES ('0', '{$NET.IF.IFDESCR.MATCHES}', '^(PUBLICA|USUARIOS|NAS)$', '10879', '0', '', '8249');
-- hostmacro

INSERT INTO hostmacro (hostmacroid, hostid, macro, value, description, type, automatic) VALUES ('0', '{$site-a.VLAN.MATCHES}', '^(vlan250|vlan301|vlan305|vlan175|vlan190|vlan220|vlan225|vlan235)$', '10879', '0', '', '8250');
-- hostmacro

INSERT INTO hostmacro (hostmacroid, hostid, macro, value, description, type, automatic) VALUES ('0', '{$site-a.VLAN.UNIVERSE}', '^(vlan100|vlan105|vlan110|vlan111|vlan115|vlan120|vlan125|vlan130|vlan135|vlan140|vlan145|vlan150|vlan155|vlan160|vlan165|vlan170|vlan175|vlan180|vlan185|vlan190|vlan195|vlan205|vlan210|vlan215|vlan220|vlan225|vlan230|vlan235|vlan240|vlan245|vlan250|vlan301|vlan305|vlan310|vlan315|vlan320)$', '10869', '0', 'DOCUMENTAL: union de las VLANs de site-a (cuales son VLANs de cliente). NO la usa ninguna automatizacion: el filtro real es la macro por host {$site-a.VLAN.MATCHES}.', '8251');

--- items: templates 10869/10870 + items PPP locales de los 7 CHR
-- items

INSERT INTO items (itemid, type, snmp_oid, hostid, name, key_, delay, history, trends, status, value_type, trapper_hosts, units, formula, logtimefmt, templateid, valuemapid, params, ipmi_sensor, authtype, username, password, publickey, privatekey, flags, interfaceid, description, inventory_link, lifetime, evaltype, jmx_endpoint, master_itemid, timeout, url, query_fields, posts, status_codes, follow_redirects, post_type, http_proxy, headers, retrieve_mode, request_method, output_format, ssl_cert_file, ssl_key_file, ssl_key_password, verify_peer, verify_host, allow_traps, discover, uuid, lifetime_type, enabled_lifetime_type, enabled_lifetime) VALUES ('', 'net.vlan.map', 'Mikrotik VLAN site-a: mapa de VLANs (trapper)', '2', '996f171cbb7d4b9296c6179f7c4e2933', '0', '0', '', '', '10869', '134510', '', '0', '0', '', '', '1h', '', '0', '0', '0', '7d', '', '', '', '0', '', '', '', '', NULL, '4', NULL, '0', 'Master TRAPPER de la LLD de VLANs (SOLO site-a).
Los CHR de site-a terminan el PPPoE "Enlace" de ~2.000 usuarios: su ifTable tiene 2.190 filas y un walk de UNA columna son 118.784 bytes, mas que el limite de 65.535 bytes del valor de un item. Por eso el master SNMP anterior (net.vlan.walk) devolvia texto truncado y la LLD descubria 2 de 8 VLANs.
Ahora el master es un trapper alimentado por scripts/vlan_mapper.py (walk de 1 columna + filtro), que publica un JSON [{"ifdescr":"vlan175","ifname":"vlan175","index":102}, ...] con una entrada por VLAN.
NO portar a otros sitios (site-b y demas clientes) sin volver a medir la ifTable.', NULL, '', '0', '0', '', '', '', '200', '0', NULL, '0', '0', '', '127.0.0.1', '0', '0', '0', '1', '', '2');
-- items

INSERT INTO items (itemid, type, snmp_oid, hostid, name, key_, delay, history, trends, status, value_type, trapper_hosts, units, formula, logtimefmt, templateid, valuemapid, params, ipmi_sensor, authtype, username, password, publickey, privatekey, flags, interfaceid, description, inventory_link, lifetime, evaltype, jmx_endpoint, master_itemid, timeout, url, query_fields, posts, status_codes, follow_redirects, post_type, http_proxy, headers, retrieve_mode, request_method, output_format, ssl_cert_file, ssl_key_file, ssl_key_password, verify_peer, verify_host, allow_traps, discover, uuid, lifetime_type, enabled_lifetime_type, enabled_lifetime) VALUES ('', 'mikrotik.ppp.active.raw', 'PPP active raw', '20', '', '3m', '0', '', '', '10844', '130281', '', '0', '0', '', '', '2d', '', '0', '0', '0', '7d', '', 'walk[1.3.6.1.4.1.14988.1.1.14.1.1.2]', '', '0', '', '', '', '', NULL, '4', NULL, '0', '', '141', '', '0', '0', '', '', '', '200', '0', NULL, '0', '0', '', '', '0', '0', '0', '1', '', '2');
-- items

INSERT INTO items (itemid, type, snmp_oid, hostid, name, key_, delay, history, trends, status, value_type, trapper_hosts, units, formula, logtimefmt, templateid, valuemapid, params, ipmi_sensor, authtype, username, password, publickey, privatekey, flags, interfaceid, description, inventory_link, lifetime, evaltype, jmx_endpoint, master_itemid, timeout, url, query_fields, posts, status_codes, follow_redirects, post_type, http_proxy, headers, retrieve_mode, request_method, output_format, ssl_cert_file, ssl_key_file, ssl_key_password, verify_peer, verify_host, allow_traps, discover, uuid, lifetime_type, enabled_lifetime_type, enabled_lifetime) VALUES ('', 'mikrotik.ppp.active.raw', 'PPP active raw', '20', '', '3m', '0', '', '', '10845', '130282', '', '0', '0', '', '', '2d', '', '0', '0', '0', '7d', '', 'walk[1.3.6.1.4.1.14988.1.1.14.1.1.2]', '', '0', '', '', '', '', NULL, '4', NULL, '0', '', '142', '', '0', '0', '', '', '', '200', '0', NULL, '0', '0', '', '', '0', '0', '0', '1', '', '2');
-- items

INSERT INTO items (itemid, type, snmp_oid, hostid, name, key_, delay, history, trends, status, value_type, trapper_hosts, units, formula, logtimefmt, templateid, valuemapid, params, ipmi_sensor, authtype, username, password, publickey, privatekey, flags, interfaceid, description, inventory_link, lifetime, evaltype, jmx_endpoint, master_itemid, timeout, url, query_fields, posts, status_codes, follow_redirects, post_type, http_proxy, headers, retrieve_mode, request_method, output_format, ssl_cert_file, ssl_key_file, ssl_key_password, verify_peer, verify_host, allow_traps, discover, uuid, lifetime_type, enabled_lifetime_type, enabled_lifetime) VALUES ('', 'mikrotik.ppp.active.raw', 'PPP active raw', '20', '', '3m', '0', '', '', '10846', '130283', '', '0', '0', '', '', '2d', '', '0', '0', '0', '7d', '', 'walk[1.3.6.1.4.1.14988.1.1.14.1.1.2]', '', '0', '', '', '', '', NULL, '4', NULL, '0', '', '143', '', '0', '0', '', '', '', '200', '0', NULL, '0', '0', '', '', '0', '0', '0', '1', '', '2');
-- items

INSERT INTO items (itemid, type, snmp_oid, hostid, name, key_, delay, history, trends, status, value_type, trapper_hosts, units, formula, logtimefmt, templateid, valuemapid, params, ipmi_sensor, authtype, username, password, publickey, privatekey, flags, interfaceid, description, inventory_link, lifetime, evaltype, jmx_endpoint, master_itemid, timeout, url, query_fields, posts, status_codes, follow_redirects, post_type, http_proxy, headers, retrieve_mode, request_method, output_format, ssl_cert_file, ssl_key_file, ssl_key_password, verify_peer, verify_host, allow_traps, discover, uuid, lifetime_type, enabled_lifetime_type, enabled_lifetime) VALUES ('', 'mikrotik.ppp.active.raw', 'PPP active raw', '20', '', '3m', '0', '', '', '10848', '130284', '', '0', '0', '', '', '2d', '', '0', '0', '0', '7d', '', 'walk[1.3.6.1.4.1.14988.1.1.14.1.1.2]', '', '0', '', '', '', '', NULL, '4', NULL, '0', '', '145', '', '0', '0', '', '', '', '200', '0', NULL, '0', '0', '', '', '0', '0', '0', '1', '', '2');
-- items

INSERT INTO items (itemid, type, snmp_oid, hostid, name, key_, delay, history, trends, status, value_type, trapper_hosts, units, formula, logtimefmt, templateid, valuemapid, params, ipmi_sensor, authtype, username, password, publickey, privatekey, flags, interfaceid, description, inventory_link, lifetime, evaltype, jmx_endpoint, master_itemid, timeout, url, query_fields, posts, status_codes, follow_redirects, post_type, http_proxy, headers, retrieve_mode, request_method, output_format, ssl_cert_file, ssl_key_file, ssl_key_password, verify_peer, verify_host, allow_traps, discover, uuid, lifetime_type, enabled_lifetime_type, enabled_lifetime) VALUES ('', 'mikrotik.ppp.active.count', 'PPP active users', '18', '', '0', '0', '', '', '10844', '130286', '', '0', '365d', '', '', '31d', '', '0', '0', '0', '7d', '', '', '', '0', '', '', '', '', NULL, '0', NULL, '0', '', NULL, '', '0', '0', '', '', '', '200', '0', '130281', '0', '0', '', '', '0', '0', '0', '1', '', '2');
-- items

INSERT INTO items (itemid, type, snmp_oid, hostid, name, key_, delay, history, trends, status, value_type, trapper_hosts, units, formula, logtimefmt, templateid, valuemapid, params, ipmi_sensor, authtype, username, password, publickey, privatekey, flags, interfaceid, description, inventory_link, lifetime, evaltype, jmx_endpoint, master_itemid, timeout, url, query_fields, posts, status_codes, follow_redirects, post_type, http_proxy, headers, retrieve_mode, request_method, output_format, ssl_cert_file, ssl_key_file, ssl_key_password, verify_peer, verify_host, allow_traps, discover, uuid, lifetime_type, enabled_lifetime_type, enabled_lifetime) VALUES ('', 'mikrotik.ppp.active.count', 'PPP active users', '18', '', '0', '0', '', '', '10845', '130287', '', '0', '365d', '', '', '31d', '', '0', '0', '0', '7d', '', '', '', '0', '', '', '', '', NULL, '0', NULL, '0', '', NULL, '', '0', '0', '', '', '', '200', '0', '130282', '0', '0', '', '', '0', '0', '0', '1', '', '2');
-- items

INSERT INTO items (itemid, type, snmp_oid, hostid, name, key_, delay, history, trends, status, value_type, trapper_hosts, units, formula, logtimefmt, templateid, valuemapid, params, ipmi_sensor, authtype, username, password, publickey, privatekey, flags, interfaceid, description, inventory_link, lifetime, evaltype, jmx_endpoint, master_itemid, timeout, url, query_fields, posts, status_codes, follow_redirects, post_type, http_proxy, headers, retrieve_mode, request_method, output_format, ssl_cert_file, ssl_key_file, ssl_key_password, verify_peer, verify_host, allow_traps, discover, uuid, lifetime_type, enabled_lifetime_type, enabled_lifetime) VALUES ('', 'mikrotik.ppp.active.count', 'PPP active users', '18', '', '0', '0', '', '', '10846', '130288', '', '0', '365d', '', '', '31d', '', '0', '0', '0', '7d', '', '', '', '0', '', '', '', '', NULL, '0', NULL, '0', '', NULL, '', '0', '0', '', '', '', '200', '0', '130283', '0', '0', '', '', '0', '0', '0', '1', '', '2');
-- items

INSERT INTO items (itemid, type, snmp_oid, hostid, name, key_, delay, history, trends, status, value_type, trapper_hosts, units, formula, logtimefmt, templateid, valuemapid, params, ipmi_sensor, authtype, username, password, publickey, privatekey, flags, interfaceid, description, inventory_link, lifetime, evaltype, jmx_endpoint, master_itemid, timeout, url, query_fields, posts, status_codes, follow_redirects, post_type, http_proxy, headers, retrieve_mode, request_method, output_format, ssl_cert_file, ssl_key_file, ssl_key_password, verify_peer, verify_host, allow_traps, discover, uuid, lifetime_type, enabled_lifetime_type, enabled_lifetime) VALUES ('', 'mikrotik.ppp.active.count', 'PPP active users', '18', '', '0', '0', '', '', '10848', '130289', '', '0', '365d', '', '', '31d', '', '0', '0', '0', '7d', '', '', '', '0', '', '', '', '', NULL, '0', NULL, '0', '', NULL, '', '0', '0', '', '', '', '200', '0', '130284', '0', '0', '', '', '0', '0', '0', '1', '', '2');
-- items

INSERT INTO items (itemid, type, snmp_oid, hostid, name, key_, delay, history, trends, status, value_type, trapper_hosts, units, formula, logtimefmt, templateid, valuemapid, params, ipmi_sensor, authtype, username, password, publickey, privatekey, flags, interfaceid, description, inventory_link, lifetime, evaltype, jmx_endpoint, master_itemid, timeout, url, query_fields, posts, status_codes, follow_redirects, post_type, http_proxy, headers, retrieve_mode, request_method, output_format, ssl_cert_file, ssl_key_file, ssl_key_password, verify_peer, verify_host, allow_traps, discover, uuid, lifetime_type, enabled_lifetime_type, enabled_lifetime) VALUES ('', 'net.vlan.in[ifHCInOctets.{#SNMPINDEX}]', 'VLAN {#IFDESCR}: Bits received', '20', '7248d7d75a4046f0881096696d35735e', '1m', '2', '', 'bps', '10869', '131405', '', '0', '365d', '', '', '31d', '', '0', '0', '0', '7d', '', '1.3.6.1.2.1.31.1.1.1.6.{#SNMPINDEX}', '', '0', '', '', '', '', NULL, '3', NULL, '0', 'IF-MIB ifHCInOctets (.1.3.6.1.2.1.31.1.1.1.6), 64-bit.
Rate per second x8 = bits per second.', NULL, '', '0', '0', '', '', '', '200', '0', NULL, '0', '0', '', '', '0', '0', '0', '1', '', '2');
-- items

INSERT INTO items (itemid, type, snmp_oid, hostid, name, key_, delay, history, trends, status, value_type, trapper_hosts, units, formula, logtimefmt, templateid, valuemapid, params, ipmi_sensor, authtype, username, password, publickey, privatekey, flags, interfaceid, description, inventory_link, lifetime, evaltype, jmx_endpoint, master_itemid, timeout, url, query_fields, posts, status_codes, follow_redirects, post_type, http_proxy, headers, retrieve_mode, request_method, output_format, ssl_cert_file, ssl_key_file, ssl_key_password, verify_peer, verify_host, allow_traps, discover, uuid, lifetime_type, enabled_lifetime_type, enabled_lifetime) VALUES ('', 'net.vlan.out[ifHCOutOctets.{#SNMPINDEX}]', 'VLAN {#IFDESCR}: Bits sent', '20', '449014439ed643299bc496c46848c876', '1m', '2', '', 'bps', '10869', '131406', '', '0', '365d', '', '', '31d', '', '0', '0', '0', '7d', '', '1.3.6.1.2.1.31.1.1.1.10.{#SNMPINDEX}', '', '0', '', '', '', '', NULL, '3', NULL, '0', 'IF-MIB ifHCOutOctets (.1.3.6.1.2.1.31.1.1.1.10), 64-bit.
Rate per second x8 = bits per second.', NULL, '', '0', '0', '', '', '', '200', '0', NULL, '0', '0', '', '', '0', '0', '0', '1', '', '2');
-- items

INSERT INTO items (itemid, type, snmp_oid, hostid, name, key_, delay, history, trends, status, value_type, trapper_hosts, units, formula, logtimefmt, templateid, valuemapid, params, ipmi_sensor, authtype, username, password, publickey, privatekey, flags, interfaceid, description, inventory_link, lifetime, evaltype, jmx_endpoint, master_itemid, timeout, url, query_fields, posts, status_codes, follow_redirects, post_type, http_proxy, headers, retrieve_mode, request_method, output_format, ssl_cert_file, ssl_key_file, ssl_key_password, verify_peer, verify_host, allow_traps, discover, uuid, lifetime_type, enabled_lifetime_type, enabled_lifetime) VALUES ('', 'net.vlan.discovery', 'site-a VLAN interfaces discovery', '18', '8f6ee3d5e04e45548dc3e67f3024ac16', '0', '1', '', '', '10869', '131404', '', '0', '365d', '', '', '31d', '', '0', '0', '1', '7d', '', '', '', '0', '', '', '', '', NULL, '4', NULL, '0', 'Discovers the whitelisted site-a VLANs from the JSON published by the trapper master net.vlan.map (SOLO site-a: ver la descripcion del item).
Las macros {#IFDESCR}, {#IFNAME} y {#SNMPINDEX} estan declaradas explicitamente (lld_macro_paths): con un master que no es SNMP, Zabbix deja de autogenerarlas y sin ellas la LLD no descubre nada y no deja error en el log.
El master SNMP viejo (net.vlan.walk) queda en el template DESHABILITADO (para rollback), ya no se usa.', NULL, '', '0', '0', '', '', '', '200', '0', '134510', '0', '0', '', '', '0', '0', '0', '1', '', '2');
-- items

INSERT INTO items (itemid, type, snmp_oid, hostid, name, key_, delay, history, trends, status, value_type, trapper_hosts, units, formula, logtimefmt, templateid, valuemapid, params, ipmi_sensor, authtype, username, password, publickey, privatekey, flags, interfaceid, description, inventory_link, lifetime, evaltype, jmx_endpoint, master_itemid, timeout, url, query_fields, posts, status_codes, follow_redirects, post_type, http_proxy, headers, retrieve_mode, request_method, output_format, ssl_cert_file, ssl_key_file, ssl_key_password, verify_peer, verify_host, allow_traps, discover, uuid, lifetime_type, enabled_lifetime_type, enabled_lifetime) VALUES ('', 'net.ppp.walk', 'PPP dedicated: SNMP walk active entries', '20', 'ef8c84effc3f436689c133ca9376697f', '5m', '0', '', '', '10870', '131645', '', '0', '0', '', '', '3d', '10s', '0', '0', '0', '7d', '', 'walk[1.3.6.1.4.1.14988.1.1.2.1.1.2]', '', '0', '', '', '', '', NULL, '4', NULL, '0', 'Master walk feeding PPP dedicated-users discovery and 64-bit counters (MikroTik private MIB, numeric OIDs).', NULL, '', '0', '0', '', '', '', '200', '0', NULL, '0', '0', '', '', '0', '0', '0', '1', '', '2');
-- items

INSERT INTO items (itemid, type, snmp_oid, hostid, name, key_, delay, history, trends, status, value_type, trapper_hosts, units, formula, logtimefmt, templateid, valuemapid, params, ipmi_sensor, authtype, username, password, publickey, privatekey, flags, interfaceid, description, inventory_link, lifetime, evaltype, jmx_endpoint, master_itemid, timeout, url, query_fields, posts, status_codes, follow_redirects, post_type, http_proxy, headers, retrieve_mode, request_method, output_format, ssl_cert_file, ssl_key_file, ssl_key_password, verify_peer, verify_host, allow_traps, discover, uuid, lifetime_type, enabled_lifetime_type, enabled_lifetime) VALUES ('', 'net.ppp.in[{#PPP_NAME}]', 'PPP {#PPP_NAME}: Bits received', '20', '00f5dfeae9ec4cbfae3e4dd2e8532b03', '1m', '2', '', 'bps', '10870', '131653', '', '0', '365d', '', '', '31d', '', '0', '0', '0', '7d', '', '1.3.6.1.4.1.14988.1.1.2.1.1.8.{#SNMPINDEX}', '', '0', '', '', '', '', NULL, '3', NULL, '0', 'MikroTik active-PPP col .8 (.1.3.6.1.4.1.14988.1.1.2.1.1.8), Counter64.
Rate per second x8 = bits per second.
DIRECTION ASSUMPTION UNCONFIRMED: col .8 treated as IN.', NULL, '', '0', '0', '', '', '', '200', '0', NULL, '0', '0', '', '', '0', '0', '0', '1', '', '2');
-- items

INSERT INTO items (itemid, type, snmp_oid, hostid, name, key_, delay, history, trends, status, value_type, trapper_hosts, units, formula, logtimefmt, templateid, valuemapid, params, ipmi_sensor, authtype, username, password, publickey, privatekey, flags, interfaceid, description, inventory_link, lifetime, evaltype, jmx_endpoint, master_itemid, timeout, url, query_fields, posts, status_codes, follow_redirects, post_type, http_proxy, headers, retrieve_mode, request_method, output_format, ssl_cert_file, ssl_key_file, ssl_key_password, verify_peer, verify_host, allow_traps, discover, uuid, lifetime_type, enabled_lifetime_type, enabled_lifetime) VALUES ('', 'net.ppp.out[{#PPP_NAME}]', 'PPP {#PPP_NAME}: Bits sent', '20', 'c308e6a9dd0a46ad917678d683bd5381', '1m', '2', '', 'bps', '10870', '131654', '', '0', '365d', '', '', '31d', '', '0', '0', '0', '7d', '', '1.3.6.1.4.1.14988.1.1.2.1.1.9.{#SNMPINDEX}', '', '0', '', '', '', '', NULL, '3', NULL, '0', 'MikroTik active-PPP col .9 (.1.3.6.1.4.1.14988.1.1.2.1.1.9), Counter64.
Rate per second x8 = bits per second.
DIRECTION ASSUMPTION UNCONFIRMED: col .9 treated as OUT.', NULL, '', '0', '0', '', '', '', '200', '0', NULL, '0', '0', '', '', '0', '0', '0', '1', '', '2');
-- items

INSERT INTO items (itemid, type, snmp_oid, hostid, name, key_, delay, history, trends, status, value_type, trapper_hosts, units, formula, logtimefmt, templateid, valuemapid, params, ipmi_sensor, authtype, username, password, publickey, privatekey, flags, interfaceid, description, inventory_link, lifetime, evaltype, jmx_endpoint, master_itemid, timeout, url, query_fields, posts, status_codes, follow_redirects, post_type, http_proxy, headers, retrieve_mode, request_method, output_format, ssl_cert_file, ssl_key_file, ssl_key_password, verify_peer, verify_host, allow_traps, discover, uuid, lifetime_type, enabled_lifetime_type, enabled_lifetime) VALUES ('', 'net.vlan.walk', 'Mikrotik VLAN site-a: SNMP walk VLAN interfaces', '20', '043e7ee4267a4c13b06a0b4a385ed35c', '5m', '0', '', '', '10869', '131403', '', '1', '0', '', '', '0', '60s', '0', '0', '0', '7d', '', 'walk[1.3.6.1.2.1.31.1.1.1.1,1.3.6.1.2.1.31.1.1.1.18,1.3.6.1.2.1.2.2.1.2,1.3.6.1.2.1.2.2.1.3]', '', '0', '', '', '', '', NULL, '4', NULL, '0', 'DESHABILITADO 2026-10-21: el walk de 4 columnas excede el limite de 65.535 bytes del valor de un item en los CHR de site-a (ifTable de 2.190 filas). El master de la LLD paso a ser el trapper net.vlan.map. Rollback: habilitar este item y volver a apuntar la regla net.vlan.discovery a el (quitando las lld_macro_paths).', NULL, '', '0', '0', '', '', '', '200', '0', NULL, '0', '0', '', '', '0', '0', '0', '1', '', '2');
-- items

INSERT INTO items (itemid, type, snmp_oid, hostid, name, key_, delay, history, trends, status, value_type, trapper_hosts, units, formula, logtimefmt, templateid, valuemapid, params, ipmi_sensor, authtype, username, password, publickey, privatekey, flags, interfaceid, description, inventory_link, lifetime, evaltype, jmx_endpoint, master_itemid, timeout, url, query_fields, posts, status_codes, follow_redirects, post_type, http_proxy, headers, retrieve_mode, request_method, output_format, ssl_cert_file, ssl_key_file, ssl_key_password, verify_peer, verify_host, allow_traps, discover, uuid, lifetime_type, enabled_lifetime_type, enabled_lifetime) VALUES ('', 'net.ppp.discovery', 'PPP dedicated users discovery', '18', 'c90cdaa214b74e3da58acb23eee6cf8e', '0', '1', '', '', '10870', '131649', '', '0', '365d', '', '', '31d', '', '0', '0', '1', '7d', '', '', '', '0', '', '', '', '', NULL, '4', NULL, '0', 'Discovers whitelisted dedicated PPP users only (case-insensitive exact match on {#PPP_NAME}).', NULL, '', '0', '0', '', '', '', '200', '0', '131645', '0', '0', '', '', '0', '0', '0', '1', '', '2');
-- items

INSERT INTO items (itemid, type, snmp_oid, hostid, name, key_, delay, history, trends, status, value_type, trapper_hosts, units, formula, logtimefmt, templateid, valuemapid, params, ipmi_sensor, authtype, username, password, publickey, privatekey, flags, interfaceid, description, inventory_link, lifetime, evaltype, jmx_endpoint, master_itemid, timeout, url, query_fields, posts, status_codes, follow_redirects, post_type, http_proxy, headers, retrieve_mode, request_method, output_format, ssl_cert_file, ssl_key_file, ssl_key_password, verify_peer, verify_host, allow_traps, discover, uuid, lifetime_type, enabled_lifetime_type, enabled_lifetime) VALUES ('', 'mikrotik.ppp.active.raw', 'PPP active raw', '20', '', '3m', '0', '', '', '10877', '133656', '', '0', '0', '', '', '2d', '', '0', '0', '0', '7d', '', 'walk[1.3.6.1.4.1.14988.1.1.14.1.1.2]', '', '0', '', '', '', '', NULL, '4', NULL, '0', '', '171', '', '0', '0', '', '', '', '200', '0', NULL, '0', '0', '', '', '0', '0', '0', '1', '', '2');
-- items

INSERT INTO items (itemid, type, snmp_oid, hostid, name, key_, delay, history, trends, status, value_type, trapper_hosts, units, formula, logtimefmt, templateid, valuemapid, params, ipmi_sensor, authtype, username, password, publickey, privatekey, flags, interfaceid, description, inventory_link, lifetime, evaltype, jmx_endpoint, master_itemid, timeout, url, query_fields, posts, status_codes, follow_redirects, post_type, http_proxy, headers, retrieve_mode, request_method, output_format, ssl_cert_file, ssl_key_file, ssl_key_password, verify_peer, verify_host, allow_traps, discover, uuid, lifetime_type, enabled_lifetime_type, enabled_lifetime) VALUES ('', 'mikrotik.ppp.active.count', 'PPP active users', '18', '', '0', '0', '', '', '10877', '133657', '', '0', '365d', '', '', '31d', '', '0', '0', '0', '7d', '', '', '', '0', '', '', '', '', NULL, '0', NULL, '0', '', NULL, '', '0', '0', '', '', '', '200', '0', '133656', '0', '0', '', '', '0', '0', '0', '1', '', '2');
-- items

INSERT INTO items (itemid, type, snmp_oid, hostid, name, key_, delay, history, trends, status, value_type, trapper_hosts, units, formula, logtimefmt, templateid, valuemapid, params, ipmi_sensor, authtype, username, password, publickey, privatekey, flags, interfaceid, description, inventory_link, lifetime, evaltype, jmx_endpoint, master_itemid, timeout, url, query_fields, posts, status_codes, follow_redirects, post_type, http_proxy, headers, retrieve_mode, request_method, output_format, ssl_cert_file, ssl_key_file, ssl_key_password, verify_peer, verify_host, allow_traps, discover, uuid, lifetime_type, enabled_lifetime_type, enabled_lifetime) VALUES ('', 'mikrotik.ppp.active.raw', 'PPP active raw', '20', '', '3m', '0', '', '', '10878', '133658', '', '0', '0', '', '', '2d', '', '0', '0', '0', '7d', '', 'walk[1.3.6.1.4.1.14988.1.1.14.1.1.2]', '', '0', '', '', '', '', NULL, '4', NULL, '0', '', '172', '', '0', '0', '', '', '', '200', '0', NULL, '0', '0', '', '', '0', '0', '0', '1', '', '2');
-- items

INSERT INTO items (itemid, type, snmp_oid, hostid, name, key_, delay, history, trends, status, value_type, trapper_hosts, units, formula, logtimefmt, templateid, valuemapid, params, ipmi_sensor, authtype, username, password, publickey, privatekey, flags, interfaceid, description, inventory_link, lifetime, evaltype, jmx_endpoint, master_itemid, timeout, url, query_fields, posts, status_codes, follow_redirects, post_type, http_proxy, headers, retrieve_mode, request_method, output_format, ssl_cert_file, ssl_key_file, ssl_key_password, verify_peer, verify_host, allow_traps, discover, uuid, lifetime_type, enabled_lifetime_type, enabled_lifetime) VALUES ('', 'mikrotik.ppp.active.count', 'PPP active users', '18', '', '0', '0', '', '', '10878', '133659', '', '0', '365d', '', '', '31d', '', '0', '0', '0', '7d', '', '', '', '0', '', '', '', '', NULL, '0', NULL, '0', '', NULL, '', '0', '0', '', '', '', '200', '0', '133658', '0', '0', '', '', '0', '0', '0', '1', '', '2');
-- items

INSERT INTO items (itemid, type, snmp_oid, hostid, name, key_, delay, history, trends, status, value_type, trapper_hosts, units, formula, logtimefmt, templateid, valuemapid, params, ipmi_sensor, authtype, username, password, publickey, privatekey, flags, interfaceid, description, inventory_link, lifetime, evaltype, jmx_endpoint, master_itemid, timeout, url, query_fields, posts, status_codes, follow_redirects, post_type, http_proxy, headers, retrieve_mode, request_method, output_format, ssl_cert_file, ssl_key_file, ssl_key_password, verify_peer, verify_host, allow_traps, discover, uuid, lifetime_type, enabled_lifetime_type, enabled_lifetime) VALUES ('', 'mikrotik.ppp.active.count', 'PPP active users', '18', '', '0', '0', '', '', '10879', '134053', '', '0', '365d', '', '', '31d', '', '0', '0', '0', '7d', '', '', '', '0', '', '', '', '', NULL, '0', NULL, '0', '', NULL, '', '0', '0', '', '', '', '200', '0', '134040', '0', '0', '', '', '0', '0', '0', '1', '', '2');
-- items

INSERT INTO items (itemid, type, snmp_oid, hostid, name, key_, delay, history, trends, status, value_type, trapper_hosts, units, formula, logtimefmt, templateid, valuemapid, params, ipmi_sensor, authtype, username, password, publickey, privatekey, flags, interfaceid, description, inventory_link, lifetime, evaltype, jmx_endpoint, master_itemid, timeout, url, query_fields, posts, status_codes, follow_redirects, post_type, http_proxy, headers, retrieve_mode, request_method, output_format, ssl_cert_file, ssl_key_file, ssl_key_password, verify_peer, verify_host, allow_traps, discover, uuid, lifetime_type, enabled_lifetime_type, enabled_lifetime) VALUES ('', 'mikrotik.ppp.active.raw', 'PPP active raw', '20', '', '5m', '0', '', '', '10879', '134040', '', '0', '0', '', '', '3d', '10s', '0', '0', '0', '7d', '', 'walk[1.3.6.1.4.1.14988.1.1.2.1.1.2]', '', '0', '', '', '', '', NULL, '4', NULL, '0', '', '173', '', '0', '0', '', '', '', '200', '0', NULL, '0', '0', '', '', '0', '0', '0', '1', '', '2');

--- item_preproc de esos items
-- item_preproc

INSERT INTO item_preproc (item_preprocid, itemid, step, type, params, error_handler, error_handler_params) VALUES ('1', '21', '130286', E'var lines = value.trim().split(''\\n'');
var count = 0;

for (var i = 0; i < lines.length; i++) {
    if (lines[i].match(/<pppoe-/)) {
        count++;
    }
}

return count;', '0', '196042', '');
-- item_preproc

INSERT INTO item_preproc (item_preprocid, itemid, step, type, params, error_handler, error_handler_params) VALUES ('1', '21', '130287', E'var lines = value.trim().split(''\\n'');
var count = 0;

for (var i = 0; i < lines.length; i++) {
    if (lines[i].match(/<pppoe-/)) {
        count++;
    }
}

return count;', '0', '196043', '');
-- item_preproc

INSERT INTO item_preproc (item_preprocid, itemid, step, type, params, error_handler, error_handler_params) VALUES ('1', '21', '130288', E'var lines = value.trim().split(''\\n'');
var count = 0;

for (var i = 0; i < lines.length; i++) {
    if (lines[i].match(/<pppoe-/)) {
        count++;
    }
}

return count;', '0', '196044', '');
-- item_preproc

INSERT INTO item_preproc (item_preprocid, itemid, step, type, params, error_handler, error_handler_params) VALUES ('1', '21', '130289', E'var lines = value.trim().split(''\\n'');
var count = 0;

for (var i = 0; i < lines.length; i++) {
    if (lines[i].match(/<pppoe-/)) {
        count++;
    }
}

return count;', '0', '196045', '');
-- item_preproc

INSERT INTO item_preproc (item_preprocid, itemid, step, type, params, error_handler, error_handler_params) VALUES ('1', '10', '131405', '1.3.6.1.2.1.31.1.1.1.6.{#SNMPINDEX}
0', '0', '197600', '');
-- item_preproc

INSERT INTO item_preproc (item_preprocid, itemid, step, type, params, error_handler, error_handler_params) VALUES ('2', '1', '131405', '8', '0', '197601', '');
-- item_preproc

INSERT INTO item_preproc (item_preprocid, itemid, step, type, params, error_handler, error_handler_params) VALUES ('1', '10', '131406', '1.3.6.1.2.1.31.1.1.1.10.{#SNMPINDEX}
0', '0', '197603', '');
-- item_preproc

INSERT INTO item_preproc (item_preprocid, itemid, step, type, params, error_handler, error_handler_params) VALUES ('2', '1', '131406', '8', '0', '197604', '');
-- item_preproc

INSERT INTO item_preproc (item_preprocid, itemid, step, type, params, error_handler, error_handler_params) VALUES ('1', '20', '131404', '1h', '0', '197598', '');
-- item_preproc

INSERT INTO item_preproc (item_preprocid, itemid, step, type, params, error_handler, error_handler_params) VALUES ('1', '10', '131653', '', '1', '198181', '');
-- item_preproc

INSERT INTO item_preproc (item_preprocid, itemid, step, type, params, error_handler, error_handler_params) VALUES ('2', '1', '131653', '8', '1', '198182', '');
-- item_preproc

INSERT INTO item_preproc (item_preprocid, itemid, step, type, params, error_handler, error_handler_params) VALUES ('1', '10', '131654', '', '1', '198184', '');
-- item_preproc

INSERT INTO item_preproc (item_preprocid, itemid, step, type, params, error_handler, error_handler_params) VALUES ('2', '1', '131654', '8', '1', '198185', '');
-- item_preproc

INSERT INTO item_preproc (item_preprocid, itemid, step, type, params, error_handler, error_handler_params) VALUES ('1', '29', '131649', '{#PPP_NAME}
1.3.6.1.4.1.14988.1.1.2.1.1.2
0', '0', '198173', '');
-- item_preproc

INSERT INTO item_preproc (item_preprocid, itemid, step, type, params, error_handler, error_handler_params) VALUES ('2', '20', '131649', '1h', '0', '198174', '');
-- item_preproc

INSERT INTO item_preproc (item_preprocid, itemid, step, type, params, error_handler, error_handler_params) VALUES ('1', '21', '133657', E'var lines = value.trim().split(''\\n'');
var count = 0;

for (var i = 0; i < lines.length; i++) {
    if (lines[i].match(/<pppoe-/)) {
        count++;
    }
}

return count;', '0', '200402', '');
-- item_preproc

INSERT INTO item_preproc (item_preprocid, itemid, step, type, params, error_handler, error_handler_params) VALUES ('1', '21', '133659', E'var lines = value.trim().split(''\\n'');
var count = 0;

for (var i = 0; i < lines.length; i++) {
    if (lines[i].match(/<pppoe-/)) {
        count++;
    }
}

return count;', '0', '200403', '');
-- item_preproc

INSERT INTO item_preproc (item_preprocid, itemid, step, type, params, error_handler, error_handler_params) VALUES ('1', '21', '134053', E'var lines = value.trim().split(''\\n'');
var count = 0;

for (var i = 0; i < lines.length; i++) {
    if (lines[i].match(/<pppoe-/)) {
        count++;
    }
}

return count;', '0', '200970', '');

--- item_condition / lld_macro_path / item_discovery de las reglas
-- item_condition

INSERT INTO item_condition (item_conditionid, itemid, operator, macro, value) VALUES ('{#IFDESCR}', '{$site-a.VLAN.MATCHES}', '131404', '8', '12586');
-- item_condition

INSERT INTO item_condition (item_conditionid, itemid, operator, macro, value) VALUES ('{#IFDESCR}', '{$site-a.VLAN.NOT_MATCHES}', '131404', '9', '12587');
-- item_condition

INSERT INTO item_condition (item_conditionid, itemid, operator, macro, value) VALUES ('{#IFNAME}', '{$site-a.VLAN.NOT_MATCHES}', '131404', '9', '12588');
-- item_condition

INSERT INTO item_condition (item_conditionid, itemid, operator, macro, value) VALUES ('{#IFDESCR}', '{$site-a.VLAN.MATCHES}', '131436', '8', '12595');
-- item_condition

INSERT INTO item_condition (item_conditionid, itemid, operator, macro, value) VALUES ('{#IFDESCR}', '{$site-a.VLAN.NOT_MATCHES}', '131436', '9', '12596');
-- item_condition

INSERT INTO item_condition (item_conditionid, itemid, operator, macro, value) VALUES ('{#IFNAME}', '{$site-a.VLAN.NOT_MATCHES}', '131436', '9', '12597');
-- item_condition

INSERT INTO item_condition (item_conditionid, itemid, operator, macro, value) VALUES ('{#IFDESCR}', '{$site-a.VLAN.MATCHES}', '131440', '8', '12598');
-- item_condition

INSERT INTO item_condition (item_conditionid, itemid, operator, macro, value) VALUES ('{#IFDESCR}', '{$site-a.VLAN.NOT_MATCHES}', '131440', '9', '12599');
-- item_condition

INSERT INTO item_condition (item_conditionid, itemid, operator, macro, value) VALUES ('{#IFNAME}', '{$site-a.VLAN.NOT_MATCHES}', '131440', '9', '12600');
-- item_condition

INSERT INTO item_condition (item_conditionid, itemid, operator, macro, value) VALUES ('{#IFDESCR}', '{$site-a.VLAN.MATCHES}', '131492', '8', '12601');
-- item_condition

INSERT INTO item_condition (item_conditionid, itemid, operator, macro, value) VALUES ('{#IFDESCR}', '{$site-a.VLAN.NOT_MATCHES}', '131492', '9', '12602');
-- item_condition

INSERT INTO item_condition (item_conditionid, itemid, operator, macro, value) VALUES ('{#IFNAME}', '{$site-a.VLAN.NOT_MATCHES}', '131492', '9', '12603');
-- item_condition

INSERT INTO item_condition (item_conditionid, itemid, operator, macro, value) VALUES ('{#IFDESCR}', '{$site-a.VLAN.MATCHES}', '131496', '8', '12604');
-- item_condition

INSERT INTO item_condition (item_conditionid, itemid, operator, macro, value) VALUES ('{#IFDESCR}', '{$site-a.VLAN.NOT_MATCHES}', '131496', '9', '12605');
-- item_condition

INSERT INTO item_condition (item_conditionid, itemid, operator, macro, value) VALUES ('{#IFNAME}', '{$site-a.VLAN.NOT_MATCHES}', '131496', '9', '12606');
-- item_condition

INSERT INTO item_condition (item_conditionid, itemid, operator, macro, value) VALUES ('{#PPP_NAME}', '{$PPP.DEDICATED.MATCHES}', '131649', '8', '12607');
-- item_condition

INSERT INTO item_condition (item_conditionid, itemid, operator, macro, value) VALUES ('{#IFDESCR}', '{$site-a.VLAN.MATCHES}', '133518', '8', '12686');
-- item_condition

INSERT INTO item_condition (item_conditionid, itemid, operator, macro, value) VALUES ('{#IFDESCR}', '{$site-a.VLAN.NOT_MATCHES}', '133518', '9', '12687');
-- item_condition

INSERT INTO item_condition (item_conditionid, itemid, operator, macro, value) VALUES ('{#IFNAME}', '{$site-a.VLAN.NOT_MATCHES}', '133518', '9', '12688');
-- item_condition

INSERT INTO item_condition (item_conditionid, itemid, operator, macro, value) VALUES ('{#IFDESCR}', '{$site-a.VLAN.MATCHES}', '133576', '8', '12705');
-- item_condition

INSERT INTO item_condition (item_conditionid, itemid, operator, macro, value) VALUES ('{#IFDESCR}', '{$site-a.VLAN.NOT_MATCHES}', '133576', '9', '12706');
-- item_condition

INSERT INTO item_condition (item_conditionid, itemid, operator, macro, value) VALUES ('{#IFNAME}', '{$site-a.VLAN.NOT_MATCHES}', '133576', '9', '12707');
-- item_condition

INSERT INTO item_condition (item_conditionid, itemid, operator, macro, value) VALUES ('{#IFDESCR}', '{$site-a.VLAN.MATCHES}', '134008', '8', '12725');
-- item_condition

INSERT INTO item_condition (item_conditionid, itemid, operator, macro, value) VALUES ('{#IFDESCR}', '{$site-a.VLAN.NOT_MATCHES}', '134008', '9', '12726');
-- item_condition

INSERT INTO item_condition (item_conditionid, itemid, operator, macro, value) VALUES ('{#IFNAME}', '{$site-a.VLAN.NOT_MATCHES}', '134008', '9', '12727');

-- lld_macro_path

INSERT INTO lld_macro_path (lld_macro_pathid, itemid, lld_macro, path) VALUES ('$.ifdescr', '131404', '{#IFDESCR}', '3126');
-- lld_macro_path

INSERT INTO lld_macro_path (lld_macro_pathid, itemid, lld_macro, path) VALUES ('$.ifname', '131404', '{#IFNAME}', '3127');
-- lld_macro_path

INSERT INTO lld_macro_path (lld_macro_pathid, itemid, lld_macro, path) VALUES ('$.index', '131404', '{#SNMPINDEX}', '3128');
-- lld_macro_path

INSERT INTO lld_macro_path (lld_macro_pathid, itemid, lld_macro, path) VALUES ('$.ifdescr', '131436', '{#IFDESCR}', '3129');
-- lld_macro_path

INSERT INTO lld_macro_path (lld_macro_pathid, itemid, lld_macro, path) VALUES ('$.ifname', '131436', '{#IFNAME}', '3130');
-- lld_macro_path

INSERT INTO lld_macro_path (lld_macro_pathid, itemid, lld_macro, path) VALUES ('$.index', '131436', '{#SNMPINDEX}', '3131');
-- lld_macro_path

INSERT INTO lld_macro_path (lld_macro_pathid, itemid, lld_macro, path) VALUES ('$.ifdescr', '131440', '{#IFDESCR}', '3132');
-- lld_macro_path

INSERT INTO lld_macro_path (lld_macro_pathid, itemid, lld_macro, path) VALUES ('$.ifname', '131440', '{#IFNAME}', '3133');
-- lld_macro_path

INSERT INTO lld_macro_path (lld_macro_pathid, itemid, lld_macro, path) VALUES ('$.index', '131440', '{#SNMPINDEX}', '3134');
-- lld_macro_path

INSERT INTO lld_macro_path (lld_macro_pathid, itemid, lld_macro, path) VALUES ('$.ifdescr', '131492', '{#IFDESCR}', '3135');
-- lld_macro_path

INSERT INTO lld_macro_path (lld_macro_pathid, itemid, lld_macro, path) VALUES ('$.ifname', '131492', '{#IFNAME}', '3136');
-- lld_macro_path

INSERT INTO lld_macro_path (lld_macro_pathid, itemid, lld_macro, path) VALUES ('$.index', '131492', '{#SNMPINDEX}', '3137');
-- lld_macro_path

INSERT INTO lld_macro_path (lld_macro_pathid, itemid, lld_macro, path) VALUES ('$.ifdescr', '131496', '{#IFDESCR}', '3138');
-- lld_macro_path

INSERT INTO lld_macro_path (lld_macro_pathid, itemid, lld_macro, path) VALUES ('$.ifname', '131496', '{#IFNAME}', '3139');
-- lld_macro_path

INSERT INTO lld_macro_path (lld_macro_pathid, itemid, lld_macro, path) VALUES ('$.index', '131496', '{#SNMPINDEX}', '3140');
-- lld_macro_path

INSERT INTO lld_macro_path (lld_macro_pathid, itemid, lld_macro, path) VALUES ('$.ifdescr', '133518', '{#IFDESCR}', '3141');
-- lld_macro_path

INSERT INTO lld_macro_path (lld_macro_pathid, itemid, lld_macro, path) VALUES ('$.ifname', '133518', '{#IFNAME}', '3142');
-- lld_macro_path

INSERT INTO lld_macro_path (lld_macro_pathid, itemid, lld_macro, path) VALUES ('$.index', '133518', '{#SNMPINDEX}', '3143');
-- lld_macro_path

INSERT INTO lld_macro_path (lld_macro_pathid, itemid, lld_macro, path) VALUES ('$.ifdescr', '133576', '{#IFDESCR}', '3144');
-- lld_macro_path

INSERT INTO lld_macro_path (lld_macro_pathid, itemid, lld_macro, path) VALUES ('$.ifname', '133576', '{#IFNAME}', '3145');
-- lld_macro_path

INSERT INTO lld_macro_path (lld_macro_pathid, itemid, lld_macro, path) VALUES ('$.index', '133576', '{#SNMPINDEX}', '3146');
-- lld_macro_path

INSERT INTO lld_macro_path (lld_macro_pathid, itemid, lld_macro, path) VALUES ('$.ifdescr', '134008', '{#IFDESCR}', '3147');
-- lld_macro_path

INSERT INTO lld_macro_path (lld_macro_pathid, itemid, lld_macro, path) VALUES ('$.ifname', '134008', '{#IFNAME}', '3148');
-- lld_macro_path

INSERT INTO lld_macro_path (lld_macro_pathid, itemid, lld_macro, path) VALUES ('$.index', '134008', '{#SNMPINDEX}', '3149');

-- item_discovery

INSERT INTO item_discovery (itemdiscoveryid, itemid, parent_itemid, key_, lastcheck, ts_delete, status, disable_source, ts_disable, lldruleid) VALUES ('', '131405', '0', '0', '131404', '0', '0', NULL, '0', '84960');
-- item_discovery

INSERT INTO item_discovery (itemdiscoveryid, itemid, parent_itemid, key_, lastcheck, ts_delete, status, disable_source, ts_disable, lldruleid) VALUES ('', '131406', '0', '0', '131404', '0', '0', NULL, '0', '84961');
-- item_discovery

INSERT INTO item_discovery (itemdiscoveryid, itemid, parent_itemid, key_, lastcheck, ts_delete, status, disable_source, ts_disable, lldruleid) VALUES ('', '131437', '0', '0', '131436', '0', '0', NULL, '0', '84986');
-- item_discovery

INSERT INTO item_discovery (itemdiscoveryid, itemid, parent_itemid, key_, lastcheck, ts_delete, status, disable_source, ts_disable, lldruleid) VALUES ('', '131438', '0', '0', '131436', '0', '0', NULL, '0', '84987');
-- item_discovery

INSERT INTO item_discovery (itemdiscoveryid, itemid, parent_itemid, key_, lastcheck, ts_delete, status, disable_source, ts_disable, lldruleid) VALUES ('', '131441', '0', '0', '131440', '0', '0', NULL, '0', '84988');
-- item_discovery

INSERT INTO item_discovery (itemdiscoveryid, itemid, parent_itemid, key_, lastcheck, ts_delete, status, disable_source, ts_disable, lldruleid) VALUES ('', '131442', '0', '0', '131440', '0', '0', NULL, '0', '84989');
-- item_discovery

INSERT INTO item_discovery (itemdiscoveryid, itemid, parent_itemid, key_, lastcheck, ts_delete, status, disable_source, ts_disable, lldruleid) VALUES ('', '133542', '0', '0', '133518', '0', '0', NULL, '0', '86930');
-- item_discovery

INSERT INTO item_discovery (itemdiscoveryid, itemid, parent_itemid, key_, lastcheck, ts_delete, status, disable_source, ts_disable, lldruleid) VALUES ('', '133543', '0', '0', '133518', '0', '0', NULL, '0', '86931');
-- item_discovery

INSERT INTO item_discovery (itemdiscoveryid, itemid, parent_itemid, key_, lastcheck, ts_delete, status, disable_source, ts_disable, lldruleid) VALUES ('', '131493', '0', '0', '131492', '0', '0', NULL, '0', '85038');
-- item_discovery

INSERT INTO item_discovery (itemdiscoveryid, itemid, parent_itemid, key_, lastcheck, ts_delete, status, disable_source, ts_disable, lldruleid) VALUES ('', '131494', '0', '0', '131492', '0', '0', NULL, '0', '85039');
-- item_discovery

INSERT INTO item_discovery (itemdiscoveryid, itemid, parent_itemid, key_, lastcheck, ts_delete, status, disable_source, ts_disable, lldruleid) VALUES ('', '131497', '0', '0', '131496', '0', '0', NULL, '0', '85040');
-- item_discovery

INSERT INTO item_discovery (itemdiscoveryid, itemid, parent_itemid, key_, lastcheck, ts_delete, status, disable_source, ts_disable, lldruleid) VALUES ('', '131498', '0', '0', '131496', '0', '0', NULL, '0', '85041');
-- item_discovery

INSERT INTO item_discovery (itemdiscoveryid, itemid, parent_itemid, key_, lastcheck, ts_delete, status, disable_source, ts_disable, lldruleid) VALUES ('', '133600', '0', '0', '133576', '0', '0', NULL, '0', '86955');
-- item_discovery

INSERT INTO item_discovery (itemdiscoveryid, itemid, parent_itemid, key_, lastcheck, ts_delete, status, disable_source, ts_disable, lldruleid) VALUES ('', '133601', '0', '0', '133576', '0', '0', NULL, '0', '86956');
-- item_discovery

INSERT INTO item_discovery (itemdiscoveryid, itemid, parent_itemid, key_, lastcheck, ts_delete, status, disable_source, ts_disable, lldruleid) VALUES ('', '131653', '0', '0', '131649', '0', '0', NULL, '0', '85170');
-- item_discovery

INSERT INTO item_discovery (itemdiscoveryid, itemid, parent_itemid, key_, lastcheck, ts_delete, status, disable_source, ts_disable, lldruleid) VALUES ('', '131654', '0', '0', '131649', '0', '0', NULL, '0', '85171');
-- item_discovery

INSERT INTO item_discovery (itemdiscoveryid, itemid, parent_itemid, key_, lastcheck, ts_delete, status, disable_source, ts_disable, lldruleid) VALUES ('', '134032', '0', '0', '134008', '0', '0', NULL, '0', '87340');
-- item_discovery

INSERT INTO item_discovery (itemdiscoveryid, itemid, parent_itemid, key_, lastcheck, ts_delete, status, disable_source, ts_disable, lldruleid) VALUES ('', '134033', '0', '0', '134008', '0', '0', NULL, '0', '87341');

--- widget_field de los 2 widgets
-- widget_field

INSERT INTO widget_field (widget_fieldid, widgetid, type, name, value_int, value_str, value_groupid, value_hostid, value_itemid, value_graphid, value_sysmapid, value_serviceid, value_slaid, value_userid, value_actionid, value_mediatypeid) VALUES ('columns.0.base_color', '1', '67523', '0', 'FF8A65', NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, '295064', NULL, NULL);
-- widget_field

INSERT INTO widget_field (widget_fieldid, widgetid, type, name, value_int, value_str, value_groupid, value_hostid, value_itemid, value_graphid, value_sysmapid, value_serviceid, value_slaid, value_userid, value_actionid, value_mediatypeid) VALUES ('columns.0.display', '0', '67523', '2', '', NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, '295065', NULL, NULL);
-- widget_field

INSERT INTO widget_field (widget_fieldid, widgetid, type, name, value_int, value_str, value_groupid, value_hostid, value_itemid, value_graphid, value_sysmapid, value_serviceid, value_slaid, value_userid, value_actionid, value_mediatypeid) VALUES ('columns.0.items.0', '1', '67523', '0', 'PPP active users', NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, '295066', NULL, NULL);
-- widget_field

INSERT INTO widget_field (widget_fieldid, widgetid, type, name, value_int, value_str, value_groupid, value_hostid, value_itemid, value_graphid, value_sysmapid, value_serviceid, value_slaid, value_userid, value_actionid, value_mediatypeid) VALUES ('columns.0.max', '1', '67523', '0', '2400', NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, '295067', NULL, NULL);
-- widget_field

INSERT INTO widget_field (widget_fieldid, widgetid, type, name, value_int, value_str, value_groupid, value_hostid, value_itemid, value_graphid, value_sysmapid, value_serviceid, value_slaid, value_userid, value_actionid, value_mediatypeid) VALUES ('columns.0.min', '1', '67523', '0', '0', NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, '295068', NULL, NULL);
-- widget_field

INSERT INTO widget_field (widget_fieldid, widgetid, type, name, value_int, value_str, value_groupid, value_hostid, value_itemid, value_graphid, value_sysmapid, value_serviceid, value_slaid, value_userid, value_actionid, value_mediatypeid) VALUES ('show_column_header', '0', '67523', '1', '', NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, '295069', NULL, NULL);
-- widget_field

INSERT INTO widget_field (widget_fieldid, widgetid, type, name, value_int, value_str, value_groupid, value_hostid, value_itemid, value_graphid, value_sysmapid, value_serviceid, value_slaid, value_userid, value_actionid, value_mediatypeid) VALUES ('hostids.0', '3', '67523', '0', '', NULL, '10848', NULL, NULL, NULL, NULL, NULL, NULL, '295070', NULL, NULL);
-- widget_field

INSERT INTO widget_field (widget_fieldid, widgetid, type, name, value_int, value_str, value_groupid, value_hostid, value_itemid, value_graphid, value_sysmapid, value_serviceid, value_slaid, value_userid, value_actionid, value_mediatypeid) VALUES ('hostids.1', '3', '67523', '0', '', NULL, '10846', NULL, NULL, NULL, NULL, NULL, NULL, '295071', NULL, NULL);
-- widget_field

INSERT INTO widget_field (widget_fieldid, widgetid, type, name, value_int, value_str, value_groupid, value_hostid, value_itemid, value_graphid, value_sysmapid, value_serviceid, value_slaid, value_userid, value_actionid, value_mediatypeid) VALUES ('hostids.2', '3', '67523', '0', '', NULL, '10877', NULL, NULL, NULL, NULL, NULL, NULL, '295072', NULL, NULL);
-- widget_field

INSERT INTO widget_field (widget_fieldid, widgetid, type, name, value_int, value_str, value_groupid, value_hostid, value_itemid, value_graphid, value_sysmapid, value_serviceid, value_slaid, value_userid, value_actionid, value_mediatypeid) VALUES ('hostids.3', '3', '67523', '0', '', NULL, '10878', NULL, NULL, NULL, NULL, NULL, NULL, '295073', NULL, NULL);
-- widget_field

INSERT INTO widget_field (widget_fieldid, widgetid, type, name, value_int, value_str, value_groupid, value_hostid, value_itemid, value_graphid, value_sysmapid, value_serviceid, value_slaid, value_userid, value_actionid, value_mediatypeid) VALUES ('hostids.4', '3', '67523', '0', '', NULL, '10879', NULL, NULL, NULL, NULL, NULL, NULL, '295062', NULL, NULL);
-- widget_field

INSERT INTO widget_field (widget_fieldid, widgetid, type, name, value_int, value_str, value_groupid, value_hostid, value_itemid, value_graphid, value_sysmapid, value_serviceid, value_slaid, value_userid, value_actionid, value_mediatypeid) VALUES ('columns.0.aggregate_function', '0', '67524', '2', '', NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, '295080', NULL, NULL);
-- widget_field

INSERT INTO widget_field (widget_fieldid, widgetid, type, name, value_int, value_str, value_groupid, value_hostid, value_itemid, value_graphid, value_sysmapid, value_serviceid, value_slaid, value_userid, value_actionid, value_mediatypeid) VALUES ('columns.0.base_color', '1', '67524', '0', '1565C0', NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, '295081', NULL, NULL);
-- widget_field

INSERT INTO widget_field (widget_fieldid, widgetid, type, name, value_int, value_str, value_groupid, value_hostid, value_itemid, value_graphid, value_sysmapid, value_serviceid, value_slaid, value_userid, value_actionid, value_mediatypeid) VALUES ('columns.0.display', '0', '67524', '3', '', NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, '295082', NULL, NULL);
-- widget_field

INSERT INTO widget_field (widget_fieldid, widgetid, type, name, value_int, value_str, value_groupid, value_hostid, value_itemid, value_graphid, value_sysmapid, value_serviceid, value_slaid, value_userid, value_actionid, value_mediatypeid) VALUES ('columns.0.history', '0', '67524', '1', '', NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, '295083', NULL, NULL);
-- widget_field

INSERT INTO widget_field (widget_fieldid, widgetid, type, name, value_int, value_str, value_groupid, value_hostid, value_itemid, value_graphid, value_sysmapid, value_serviceid, value_slaid, value_userid, value_actionid, value_mediatypeid) VALUES ('columns.0.items.0', '1', '67524', '0', 'PPP active users', NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, '295084', NULL, NULL);
-- widget_field

INSERT INTO widget_field (widget_fieldid, widgetid, type, name, value_int, value_str, value_groupid, value_hostid, value_itemid, value_graphid, value_sysmapid, value_serviceid, value_slaid, value_userid, value_actionid, value_mediatypeid) VALUES ('columns.0.max', '1', '67524', '0', '2400', NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, '295085', NULL, NULL);
-- widget_field

INSERT INTO widget_field (widget_fieldid, widgetid, type, name, value_int, value_str, value_groupid, value_hostid, value_itemid, value_graphid, value_sysmapid, value_serviceid, value_slaid, value_userid, value_actionid, value_mediatypeid) VALUES ('columns.0.min', '1', '67524', '0', '0', NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, '295086', NULL, NULL);
-- widget_field

INSERT INTO widget_field (widget_fieldid, widgetid, type, name, value_int, value_str, value_groupid, value_hostid, value_itemid, value_graphid, value_sysmapid, value_serviceid, value_slaid, value_userid, value_actionid, value_mediatypeid) VALUES ('columns.0.time_period.from', '1', '67524', '0', 'now-1d', NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, '295087', NULL, NULL);
-- widget_field

INSERT INTO widget_field (widget_fieldid, widgetid, type, name, value_int, value_str, value_groupid, value_hostid, value_itemid, value_graphid, value_sysmapid, value_serviceid, value_slaid, value_userid, value_actionid, value_mediatypeid) VALUES ('columns.0.time_period.to', '1', '67524', '0', 'now', NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, '295088', NULL, NULL);
-- widget_field

INSERT INTO widget_field (widget_fieldid, widgetid, type, name, value_int, value_str, value_groupid, value_hostid, value_itemid, value_graphid, value_sysmapid, value_serviceid, value_slaid, value_userid, value_actionid, value_mediatypeid) VALUES ('show_column_header', '0', '67524', '1', '', NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, '295089', NULL, NULL);
-- widget_field

INSERT INTO widget_field (widget_fieldid, widgetid, type, name, value_int, value_str, value_groupid, value_hostid, value_itemid, value_graphid, value_sysmapid, value_serviceid, value_slaid, value_userid, value_actionid, value_mediatypeid) VALUES ('hostids.0', '3', '67524', '0', '', NULL, '10848', NULL, NULL, NULL, NULL, NULL, NULL, '295074', NULL, NULL);
-- widget_field

INSERT INTO widget_field (widget_fieldid, widgetid, type, name, value_int, value_str, value_groupid, value_hostid, value_itemid, value_graphid, value_sysmapid, value_serviceid, value_slaid, value_userid, value_actionid, value_mediatypeid) VALUES ('hostids.1', '3', '67524', '0', '', NULL, '10846', NULL, NULL, NULL, NULL, NULL, NULL, '295075', NULL, NULL);
-- widget_field

INSERT INTO widget_field (widget_fieldid, widgetid, type, name, value_int, value_str, value_groupid, value_hostid, value_itemid, value_graphid, value_sysmapid, value_serviceid, value_slaid, value_userid, value_actionid, value_mediatypeid) VALUES ('hostids.2', '3', '67524', '0', '', NULL, '10877', NULL, NULL, NULL, NULL, NULL, NULL, '295076', NULL, NULL);
-- widget_field

INSERT INTO widget_field (widget_fieldid, widgetid, type, name, value_int, value_str, value_groupid, value_hostid, value_itemid, value_graphid, value_sysmapid, value_serviceid, value_slaid, value_userid, value_actionid, value_mediatypeid) VALUES ('hostids.3', '3', '67524', '0', '', NULL, '10878', NULL, NULL, NULL, NULL, NULL, NULL, '295077', NULL, NULL);
-- widget_field

INSERT INTO widget_field (widget_fieldid, widgetid, type, name, value_int, value_str, value_groupid, value_hostid, value_itemid, value_graphid, value_sysmapid, value_serviceid, value_slaid, value_userid, value_actionid, value_mediatypeid) VALUES ('hostids.4', '3', '67524', '0', '', NULL, '10879', NULL, NULL, NULL, NULL, NULL, NULL, '295078', NULL, NULL);

--- widgets
-- widget

INSERT INTO widget (widgetid, type, name, x, y, width, height, view_mode, dashboard_pageid) VALUES ('0', '0', 'USUARIOS ACTIVOS POR NODO', 'topitems', '39', '4', '67523', '0', '17866');
-- widget

INSERT INTO widget (widgetid, type, name, x, y, width, height, view_mode, dashboard_pageid) VALUES ('39', '0', 'MAXIMO DE USUARIOS POR DIA', 'topitems', '33', '4', '67524', '0', '17866');

