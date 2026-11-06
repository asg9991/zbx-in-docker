# Instalación del agente Zabbix en Linux

Objetivo: instalar y configurar el agente clásico (`zabbix-agent`) en hosts
Debian/Ubuntu y RHEL/CentOS.

## 1. Instalación

Debian/Ubuntu:

```bash
sudo apt update
sudo apt install zabbix-agent -y
```

RHEL/CentOS:

```bash
sudo dnf install zabbix-agent -y
```

CentOS 7:

```bash
sudo yum install zabbix-agent -y
```

## 2. Configuración

Editar `/etc/zabbix/zabbix_agentd.conf`:

```ini
# IP pública o FQDN del servidor Zabbix que el agente puede alcanzar.
Server=<IP_ZABBIX>

# Dirección usada por los checks activos.
ServerActive=<IP_ZABBIX>

# Nombre exacto del host en la interfaz de Zabbix.
Hostname=<HOSTNAME>

# Opcional: frecuencia de refresco de checks activos (default 120 s).
RefreshActiveChecks=60
```

Reiniciar y habilitar:

```bash
sudo systemctl restart zabbix-agent
sudo systemctl enable zabbix-agent
```

## 3. Verificación

```bash
sudo tail -f /var/log/zabbix/zabbix_agentd.log
```

Buscar líneas como:

```text
Active check configuration update from [<IP_ZABBIX>:10051] started
Got N active checks
```

Si no aparecen, revisar conectividad al puerto `10051`, el `Hostname` y que el
host esté creado en Zabbix con ese mismo nombre.
