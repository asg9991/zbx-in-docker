--- hostmacro del template 10869
-- hostmacro

INSERT INTO hostmacro (hostmacroid, hostid, macro, value, description, type, automatic) VALUES ('0', '{$site-a.VLAN.MATCHES}', '^(vlan100|vlan105|vlan110|vlan111|vlan115|vlan120|vlan125|vlan130|vlan135|vlan140|vlan145|vlan150|vlan155|vlan160|vlan165|vlan170|vlan175|vlan180|vlan185|vlan190|vlan195|vlan205|vlan210|vlan215|vlan220|vlan225|vlan230|vlan235|vlan240|vlan245|vlan250|vlan301|vlan305|vlan310|vlan315|vlan320)$', '10869', '0', 'LLD whitelist: union of site-a VLAN IDs (see file header comments for per-host idx).', '8228');
-- hostmacro

INSERT INTO hostmacro (hostmacroid, hostid, macro, value, description, type, automatic) VALUES ('0', '{$site-a.VLAN.NOT_MATCHES}', '^pppoe-.*', '10869', '0', 'LLD exclude: pppoe churn (applied to both {#IFDESCR} and {#IFNAME}).', '8229');

--- hostmacro de los 7 CHR
-- hostmacro

INSERT INTO hostmacro (hostmacroid, hostid, macro, value, description, type, automatic) VALUES ('0', '{$site-a.VLAN.MATCHES}', '^(vlan175|vlan190|vlan220|vlan225|vlan235)$', '10845', '0', 'Scoped to assigned VLANs', '8233');
-- hostmacro

INSERT INTO hostmacro (hostmacroid, hostid, macro, value, description, type, automatic) VALUES ('0', '{$site-a.VLAN.MATCHES}', '^(vlan125|vlan130|vlan135|vlan150|vlan165|vlan170)$', '10848', '0', 'Scoped to assigned VLANs', '8234');
-- hostmacro

INSERT INTO hostmacro (hostmacroid, hostid, macro, value, description, type, automatic) VALUES ('0', '{$site-a.VLAN.MATCHES}', '^(vlan111|vlan115|vlan185|vlan205|vlan210|vlan230)$', '10846', '0', 'Scoped to assigned VLANs', '8235');
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

