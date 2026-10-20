-- Dump the complete live definition of one Zabbix 7.4 template as JSON.
--
-- Why: the Zabbix 7.4 API does not expose LLD preprocessing (item_preproc),
-- LLD filters (item_condition) nor item prototypes (item_discovery) for
-- discovery rules, so a faithful template backup must come from the database.
--
-- Usage (on the Zabbix server):
--   sed 's/:tpl/10841/g' scripts/zabbix_template_dump.sql \
--     | docker exec -i zabbix-postgres psql -U zabbix -d zabbix -At > /tmp/tpldb_10841.json
--
-- Then render it with:
--   scripts/zabbix_template_export.py --db-json /tmp/tpldb_10841.json out.yaml
--
-- :tpl is replaced by the templateid.

WITH t AS (SELECT hostid, uuid, name, description FROM hosts WHERE hostid = :tpl),
pp AS (
  SELECT itemid,
         json_agg(json_build_object('type', type, 'params',
           CASE WHEN params IS NULL OR params='' THEN NULL
                ELSE string_to_array(params, E'\n') END,
           'error_handler', error_handler) ORDER BY step) AS pre
  FROM item_preproc GROUP BY itemid
),
protos AS (
  SELECT d.lldruleid AS ruleid, i.itemid, i.uuid, i.key_, i.name, i.type, i.snmp_oid,
         i.delay, i.timeout, i.status, i.value_type, i.units, i.history, i.trends,
         i.description, i.master_itemid
  FROM item_discovery d JOIN items i ON i.itemid = d.itemid
  WHERE i.hostid = :tpl
)
SELECT json_build_object(
  'template', json_build_object('templateid', t.hostid, 'uuid', t.uuid, 'name', t.name, 'description', t.description),
  'items', (SELECT json_agg(json_build_object(
              'itemid', i.itemid, 'uuid', i.uuid, 'key_', i.key_, 'name', i.name,
              'type', i.type, 'snmp_oid', i.snmp_oid, 'delay', i.delay, 'timeout', i.timeout,
              'status', i.status, 'value_type', i.value_type, 'units', i.units,
              'history', i.history, 'trends', i.trends, 'description', i.description,
              'master_itemid', i.master_itemid, 'preprocessing', pp.pre)
            ORDER BY i.itemid)
            FROM items i LEFT JOIN pp ON pp.itemid = i.itemid
            WHERE i.hostid = :tpl AND i.type <> 18 AND i.key_ NOT LIKE '%{%'),
  'discovery_rules', (SELECT json_agg(json_build_object(
              'itemid', i.itemid, 'uuid', i.uuid, 'key_', i.key_, 'name', i.name,
              'type', i.type, 'snmp_oid', i.snmp_oid, 'delay', i.delay, 'lifetime', i.lifetime,
              'status', i.status, 'description', i.description,
              'master_itemid', i.master_itemid, 'preprocessing', pp.pre,
              'filters', (SELECT json_agg(json_build_object('macro', c.macro, 'op', c.operator, 'value', c.value) ORDER BY c.macro, c.operator)
                            FROM item_condition c WHERE c.itemid = i.itemid),
              'item_prototypes', (SELECT json_agg(json_build_object(
                              'itemid', p.itemid, 'uuid', p.uuid, 'key_', p.key_, 'name', p.name,
                              'type', p.type, 'snmp_oid', p.snmp_oid, 'delay', p.delay, 'timeout', p.timeout,
                              'status', p.status, 'value_type', p.value_type, 'units', p.units,
                              'history', p.history, 'trends', p.trends, 'description', p.description,
                              'master_itemid', p.master_itemid, 'preprocessing', pp2.pre)
                            ORDER BY p.itemid)
                            FROM protos p LEFT JOIN pp pp2 ON pp2.itemid = p.itemid
                            WHERE p.ruleid = i.itemid))
            ORDER BY i.itemid)
            FROM items i LEFT JOIN pp ON pp.itemid = i.itemid
            WHERE i.hostid = :tpl AND i.type = 18
              AND i.itemid NOT IN (SELECT itemid FROM item_discovery)),
  'macros', (SELECT json_agg(json_build_object('macro', m.macro, 'value', m.value, 'description', m.description) ORDER BY m.macro)
               FROM hostmacro m WHERE m.hostid = :tpl),
  'hosts', (SELECT json_agg(json_build_object('hostid', h.hostid, 'host', h.host) ORDER BY h.hostid)
              FROM hosts_templates ht JOIN hosts h ON h.hostid = ht.hostid WHERE ht.templateid = :tpl)
) FROM t;
