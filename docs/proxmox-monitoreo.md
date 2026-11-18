# Monitoreo de Proxmox VE en Zabbix

Objetivo: monitorear un nodo Proxmox VE, sus VMs, contenedores LXC y storage
con los templates oficiales:

- `Proxmox VE by HTTP` — consulta la API REST de Proxmox.
- `Linux by Zabbix agent active` — monitorea el sistema operativo del nodo.

La API de Proxmox ya expone nodos, QEMU, LXC, almacenamiento, CPU, memoria y
estado del cluster; no hace falta el agente para descubrir esos recursos.

> Para el problema de confianza TLS con la CA privada del cluster, ver
> [`proxmox-monitoreo-tls.md`](proxmox-monitoreo-tls.md).

## 1. Crear el usuario de monitoreo en Proxmox

Crear un usuario dedicado, por ejemplo `zabbix@pve`, y asignarle permisos de
auditoría sobre todo el árbol de recursos:

- Path: `/`
- Propagate: `Yes`
- Privilegios: `Sys.Audit`, `VM.Audit`, `Datastore.Audit`
- Alternativa: rol `PVEAuditor`

## 2. Crear el API Token

En Proxmox:

```text
Datacenter → Permissions → API Tokens
```

Seleccionar el usuario `zabbix@pve`, crear el token y registrar:

- Token ID (ej. `zabbix@pve!monitoring`)
- Token Secret

Si el token no hereda los permisos del usuario, desactivar
`Privilege Separation` en el token.

## 3. Configurar el host en Zabbix

Vincular los templates:

- `Proxmox VE by HTTP`
- `Linux by Zabbix agent active`

Configurar las macros del host:

| Macro | Valor |
|---|---|
| `{$PVE.URL.HOST}` | `https://<IP_PROXMOX>` |
| `{$PVE.URL.PORT}` | `8006` |
| `{$PVE.TOKEN.ID}` | `zabbix@pve!monitoring` |
| `{$PVE.TOKEN.SECRET}` | `<TOKEN_SECRET>` |

El token secret se carga en Zabbix y no se versiona.

## 4. Instalar Zabbix Agent 2 en el nodo

```bash
apt update
apt install zabbix-agent2
```

Editar `/etc/zabbix/zabbix_agent2.conf`:

```ini
Server=<IP_ZABBIX>
ServerActive=<IP_ZABBIX>
Hostname=<HOSTNAME>
```

Reiniciar y habilitar:

```bash
systemctl restart zabbix-agent2
systemctl enable zabbix-agent2
```

## 5. Problemas comunes

| Síntoma | Causa | Solución |
|---|---|---|
| `403 Permission check failed (/nodes/<host>, Sys.Audit)` | El token no tiene permisos de auditoría o no los hereda | Asignar `Sys.Audit`, `VM.Audit`, `Datastore.Audit` sobre `/` con `Propagate=Yes`; revisar `Privilege Separation` |
| `Temporary failure resolving ...` durante `apt` | DNS del nodo | Corregir la resolución DNS y reintentar |
| Descubrimiento incompleto | Permisos insuficientes en algunos endpoints | Forzar una nueva ejecución del discovery después de corregir permisos |

## 6. Verificación

- El host queda `Enabled` y los items del template `Proxmox VE by HTTP` en
  estado soportado.
- El discovery muestra el nodo, las VMs QEMU y los contenedores LXC.
- Los items de `Linux by Zabbix agent active` reportan carga, procesos,
  interfaces y espacio en disco.
