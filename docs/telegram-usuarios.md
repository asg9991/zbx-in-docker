# Alta de usuarios y grupos en Telegram

Objetivo: habilitar notificaciones de Zabbix por Telegram para personas y
grupos. Complementa la castellanización de alarmas descripta en
[`telegram-es-i18n.md`](telegram-es-i18n.md).

Referencia oficial: <https://www.zabbix.com/la/integrations/telegram>

## 1. Crear el bot

1. Hablar con `@BotFather` y enviar `/newbot`.
2. Seguir las instrucciones y guardar el **token** que devuelve BotFather.
3. Cargar el token en el media type de Zabbix o en la macro correspondiente.
   Nunca versionarlo: ver [`seguridad-secretos.md`](seguridad-secretos.md).

## 2. Notificaciones personales

1. La persona interesada envía `/getid` a `@myidbot` (es un bot distinto del
   creado en el paso 1) y obtiene su chat ID.
2. La persona envía `/start` al bot creado en el paso 1. Si se salta este paso,
   el bot no puede iniciar la conversación y los mensajes fallan.
3. Cargar el chat ID como destino en el usuario de Zabbix.

## 3. Notificaciones grupales

1. Agregar al grupo tanto el bot creado en el paso 1 como `@myidbot`.
2. En el grupo, enviar `/getgroupid@myidbot` para obtener el ID del grupo.
3. Cargar ese ID como destino en el usuario o grupo de Zabbix.

## 4. Verificación

- Enviar una notificación de prueba desde Zabbix.
- Si no llega, revisar que el usuario haya hecho `/start` al bot y que el chat
  ID sea el correcto.
- Los errores del webhook quedan en `Reports → Action log` y en el log del
  media type.
