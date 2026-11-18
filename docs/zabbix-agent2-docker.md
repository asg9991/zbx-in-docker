# Zabbix Agent 2 en un host Docker

Objetivo: monitorear el host donde corren los contenedores y, opcionalmente,
los contenedores mismos, usando Zabbix Agent 2.

## 1. Instalar el agente (Debian/Ubuntu)

```bash
sudo -s

# Ajustar la versión y el codename de la distro según el host.
wget https://repo.zabbix.com/zabbix/7.4/release/ubuntu/pool/main/z/zabbix-release/zabbix-release_latest_7.4+ubuntu24.04_all.deb
dpkg -i zabbix-release_latest_7.4+ubuntu24.04_all.deb
apt update
apt install zabbix-agent2
```

Plugins opcionales para bases de datos:

```bash
apt install zabbix-agent2-plugin-mongodb \
            zabbix-agent2-plugin-mssql \
            zabbix-agent2-plugin-postgresql
```

## 2. Configurar el servidor

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

## 3. Permisos para inspeccionar Docker

Para que el agente pueda leer el estado de los contenedores, agregar el usuario
`zabbix` al grupo `docker`:

```bash
usermod -aG docker zabbix
systemctl restart zabbix-agent2
```

> **Precaución:** pertenecer al grupo `docker` equivale a acceso root sobre el
> host. Aplicarlo solo en hosts dedicados al monitoreo o evaluar una alternativa
> con permisos acotados.

## 4. Verificación

```bash
systemctl status zabbix-agent2
tail -f /var/log/zabbix/zabbix_agent2.log
```

Buscar líneas de configuración activa desde el servidor:

```text
Active check configuration update from [<IP_ZABBIX>:10051] started
```
