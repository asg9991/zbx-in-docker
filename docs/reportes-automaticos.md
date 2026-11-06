# Reportes automáticos en Zabbix 7.4

Objetivo: generar PDFs de dashboards desde Zabbix y enviarlos por correo, con
un esquema apto para producción.

## 1. Componentes necesarios

- Zabbix Server
- Zabbix Frontend
- Zabbix Web Service
- Navegador (`chromium` o Google Chrome)
- Media type de correo configurado

## 2. Instalar el Web Service

En Debian/Ubuntu:

```bash
apt update
apt install zabbix-web-service
systemctl enable zabbix-web-service --now
```

## 3. Configurar el servidor

Editar `/etc/zabbix/zabbix_server.conf`:

```ini
StartReportWriters=1
WebServiceURL=http://localhost:10053/report
```

Reiniciar:

```bash
systemctl restart zabbix-server
```

## 4. Configurar el frontend

En la interfaz web:

```text
Administration → General → Other
```

Definir `Frontend URL` con la URL real de Zabbix, por ejemplo
`http://<IP_O_DNS>/zabbix`.

## 5. Navegador (punto crítico)

Chromium instalado como SNAP genera errores (`not a snap cgroup`, fallos
intermitentes). La solución recomendada es usar Google Chrome:

```bash
snap remove chromium
wget https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb
apt install ./google-chrome-stable_current_amd64.deb -y
ln -sf /usr/bin/google-chrome /usr/bin/chromium
```

Zabbix 7.4 no permite configurar el binario desde un archivo: usa el
`chromium`/`chrome` disponible en el sistema.

## 6. Configurar el media type de correo

En Zabbix:

```text
Administration → Media types → Email
```

Ejemplo con Gmail:

| Campo | Valor |
|---|---|
| SMTP server | `smtp.gmail.com` |
| Port | `587` |
| Security | `STARTTLS` |
| Authentication | usuario / contraseña |
| Usuario | cuenta dedicada |
| Password | app password |

Usar una cuenta dedicada y una **app password** generada para Zabbix. La
contraseña se carga solo en Zabbix; no se versiona ni se comparte por chat. Ver
[`seguridad-secretos.md`](seguridad-secretos.md).

## 7. Crear reportes programados

En Zabbix:

```text
Reports → Scheduled reports
```

Configurar dashboard, intervalo (diario, semanal, mensual), destinatarios y
formato PDF.

## 8. Problemas comunes

| Problema | Causa | Solución |
|---|---|---|
| `Report manager is disabled` | `StartReportWriters=0` | Poner `StartReportWriters=1` y reiniciar el server |
| `Frontend URL not configured` | URL no definida | Configurar `Frontend URL` en la GUI |
| `Cannot connect to web service` | Servicio no instalado o puerto cerrado | Instalar `zabbix-web-service`; verificar el puerto `10053` |
| `chrome failed to start` | Chromium SNAP | Usar Google Chrome y el symlink |
| `invalid parameter ChromeOptions` | Versión no soportada | Quitar ese parámetro de la configuración |

## 9. Verificación

```bash
systemctl status zabbix-web-service
ss -lntp | grep 10053
curl http://localhost:10053/report
```

La respuesta esperada del endpoint es `Method Not Allowed`.

Después, generar un reporte de prueba y confirmar la recepción del correo con el
PDF adjunto.

## 10. Recomendaciones

- Evitar Chromium SNAP en producción.
- Usar una cuenta de correo dedicada.
- Validar los dashboards antes de automatizar.
- Mantener la configuración simple, sin parámetros no soportados.
