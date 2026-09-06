# Seguridad de secretos — token de Telegram

## Secreto involucrado

- Tipo: `api_token` del bot de Telegram usado por el media type webhook "Telegram".
- Alcance: credencial del bot frente a la API de Telegram. No se incluye su valor
  en este documento ni debe incorporarse en ningún archivo del repositorio.

## Ubicación

- Archivo: `templates/template_telegram_webhook.xml` (parámetro `api_token`
  del media type).
- Historial: el valor estuvo presente en el commit `da12351`.
- Estado actual: removido del working tree en el commit `5be7da0`, donde el
  parámetro quedó con el placeholder `{$TELEGRAM.BOT.TOKEN}`.

## Impacto

- Quien disponga de un clon que incluya el historial previo a la remoción puede
  enviar mensajes como ese bot de Telegram.
- No otorga acceso a Zabbix ni a otros sistemas: el alcance se limita al uso del
  bot frente a la API de Telegram.

## Mitigación aplicada

- El working tree ya no contiene el valor: el parámetro usa el placeholder
  `{$TELEGRAM.BOT.TOKEN}`.
- El valor real debe gestionarse como macro global por ambiente (lab / prod),
  fuera del repositorio.
- El ambiente de lab conserva el placeholder y no define un token real en el repo.

## Pendiente

1. Rotar el token en BotFather para invalidar el valor expuesto en el historial.
2. Configurar la macro correspondiente en producción con el nuevo valor.
3. Evaluar de forma coordinada la limpieza del historial (por ejemplo con
   `git filter-repo`), avisando a quienes tengan clones existentes.
