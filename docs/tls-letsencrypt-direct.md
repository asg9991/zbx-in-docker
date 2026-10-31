# TLS con Let's Encrypt directo (HTTP-01 webroot)

Certificado público emitido por Let's Encrypt y terminado en el nginx del
compose. Es el procedimiento default para un sitio con DNS público que
apunta al host (ej. site-a: `SERVER_NAME=zabbix.example.com`).

## Requisitos

- `SERVER_NAME` con DNS público resolviendo a la IP del host.
- Puertos 80 y 443 accesibles desde internet (el desafío HTTP-01 entra
  por el puerto 80).
- `docker/.env` con `SERVER_NAME=<dominio>` (ver `.env.example`).

## Emisión (una vez)

Con el stack levantado (nginx sirve `/.well-known/acme-challenge/` desde
el webroot montado):

```bash
DATA_DIR=/opt/monitoring/data   # o el valor de docker/.env
DOMAIN=zabbix.example.com       # = SERVER_NAME
sudo certbot certonly --webroot \
  -w "${DATA_DIR}/certbot-webroot" \
  -d "${DOMAIN}" \
  --email <tu-email> --agree-tos --no-eff-email
```

Copiar al directorio que nginx monta `:ro` (permisos estrictos en la key):

```bash
sudo install -m 600 /etc/letsencrypt/live/"${DOMAIN}"/privkey.pem \
  "${DATA_DIR}/certs/privkey.pem"
sudo install -m 644 /etc/letsencrypt/live/"${DOMAIN}"/fullchain.pem \
  "${DATA_DIR}/certs/fullchain.pem"
docker compose -f docker/docker-compose.yml restart nginx
```

## Renovación

`certbot renew` corre por timer (`snap` o `systemd`, según instalación).
Agregar el deploy-hook para copiar y recargar solo si hubo cambios:

```bash
sudo cp docker/certbot-deploy-hook.sh.example /root/certbot-deploy-hook.sh
sudo chmod 700 /root/certbot-deploy-hook.sh
# En la renovación (o en /etc/letsencrypt/renewal/<dominio>.conf):
#   deploy_hook = /root/certbot-deploy-hook.sh
sudo certbot renew --dry-run
```

El hook es idempotente (`cmp -s` antes de copiar) y reinicia solo el
servicio `nginx` del compose.

## Validación

```bash
curl -s -o /dev/null -w '%{http_code}\n' http://<dominio>/
# → 301
curl -s -o /dev/null -w '%{http_code}\n' https://<dominio>/
# → 200
curl -sI https://<dominio>/ | grep -iE 'strict-transport|server:'
# → solo strict-transport-security (Server va oculto por proxy_hide_header)
curl -s https://<dominio>/api_jsonrpc.php \
  -H 'Content-Type: application/json-rpc' \
  -d '{"jsonrpc":"2.0","method":"apiinfo.version","params":{},"id":1}'
# → {"jsonrpc":"2.0","result":"7.4.16","id":1}
```
