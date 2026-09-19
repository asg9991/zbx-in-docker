# TLS con Cloudflare Origin (detrás del proxy naranja)

Usar cuando el sitio va detrás del proxy de Cloudflare (nube naranja) y se
quiere cifrado punta a punta sin exponer el origen ni correr ACME en él.

## Cuándo usarlo (vs. Let's Encrypt directo)

| Aspecto              | Origin (este doc)              | Directo (`tls-letsencrypt-direct.md`) |
| -------------------- | ------------------------------ | ------------------------------------- |
| Emisor del cert      | Cloudflare Origin CA           | Let's Encrypt (ACME)                  |
| Desafío en origen    | Ninguno (no usa puerto 80)     | HTTP-01 por puerto 80                 |
| Confianza directa    | Solo Cloudflare (no browsers)  | Pública                               |
| Modo SSL en CF       | **Full (strict)** obligatorio  | N/A                                   |

## Procedimiento

1. En el dashboard de Cloudflare (SSL/TLS → Origin Server): crear un
   Origin Certificate para el `SERVER_NAME` del sitio, guardar `fullchain`
   y `privkey` (solo se muestran una vez).
2. Colocarlos en `${DATA_DIR}/certs/` con los mismos nombres que espera el
   template (`fullchain.pem`, `privkey.pem`; key con modo `600`).
3. Fijar SSL/TLS → Overview en **Full (strict)**.
4. `docker compose restart nginx`.

No hay timer ni deploy-hook: el Origin cert dura ~15 años; rotarlo a mano
generando uno nuevo en el dashboard.

## Diferencias con el modo directo

- Nada escucha desafíos ACME en el origen: el bloque
  `/.well-known/acme-challenge/` del template queda inerte (inofensivo).
- El `SERVER_NAME` debe coincidir con el hostname proxied en Cloudflare.
- La validación es la misma (https 200 / http 301 / headers / API), pero
  el issuer visto por el cliente es Cloudflare, no Let's Encrypt.
