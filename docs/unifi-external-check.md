# UniFi Network API Integration

## Objetivo

Incorporar métricas avanzadas de equipos UniFi mediante la API oficial de UniFi Network, complementando el monitoreo tradicional por SNMP.

La integración permite obtener información que no está disponible mediante SNMP, como clientes conectados, versión de firmware y estadísticas específicas de cada Access Point.

---

# Arquitectura

```
                   UniFi Controller
                          │
                    HTTPS / REST API
                          │
                          ▼
                  scripts/unifi_api.py
                          │
                          ▼
                    scripts/unifi.py
                          │
                          ▼
      scripts/externalscripts/unifi.py
                          │
                    External Check
                          │
                          ▼
               Zabbix Master Item (JSON)
                          │
               ┌──────────┴──────────┐
               │                     │
               ▼                     ▼
        Discovery Rule        Dependent Items
```

---

# Estructura del proyecto

```
scripts/

├── externalscripts/
│   └── unifi.py
│
└── unifi/
    ├── __init__.py
    ├── unifi.py
    └── unifi_api.py
```

## Componentes

### unifi_api.py

Implementa el cliente de la API de UniFi.

Responsabilidades:

- autenticación
- gestión de sesión
- consultas HTTPS
- obtención de dispositivos
- filtrado de Access Points

Toda la lógica de comunicación con UniFi se concentra en este módulo.

---

### unifi.py

Implementa la interfaz de línea de comandos utilizada por Zabbix.

Actualmente soporta dos operaciones.

#### devices

Obtiene todos los Access Points del controlador.

```
unifi.py devices URL USER PASSWORD SITE
```

Salida:

```json
{
    "data": [
        ...
    ]
}
```

---

#### discovery

Genera el JSON utilizado por Low Level Discovery.

```
unifi.py discovery URL USER PASSWORD SITE
```

Salida:

```json
[
    {
        "{#MAC}":"",
        "{#NAME}":"",
        "{#IP}":"",
        "{#MODEL}":"",
        "{#SITE}":""
    }
]
```

---

### Wrapper

```
scripts/externalscripts/unifi.py
```

Este archivo actúa únicamente como punto de entrada para Zabbix External Checks.

No contiene lógica de negocio.

Toda la implementación reside dentro del directorio `scripts/unifi`.

---

# Requisitos

## Controlador

- UniFi OS
- Aplicación UniFi Network instalada
- Usuario con permisos sobre UniFi Network

## Zabbix

- Python 3
- requests
- External Scripts habilitados

---

# Configuración del Template

## Macros requeridas

| Macro | Descripción |
|--------|-------------|
| `{$UNIFI.URL}` | URL del controlador UniFi |
| `{$UNIFI.USER}` | Usuario |
| `{$UNIFI.PASSWORD}` | Contraseña |
| `{$UNIFI.SITE}` | Identificador interno del Site |

Ejemplo:

```
{$UNIFI.URL}=https://192.0.2.40
{$UNIFI.USER}=admin
{$UNIFI.SITE}=default
```

> La contraseña debe configurarse únicamente desde el host o template de Zabbix.

---

# Master Item

Tipo:

```
External Check
```

Key:

```
unifi.py[
devices,
{$UNIFI.URL},
{$UNIFI.USER},
{$UNIFI.PASSWORD},
{$UNIFI.SITE}
]
```

Información:

```
Text
```

Intervalo recomendado:

```
60 segundos
```

El Master Item obtiene toda la información del controlador en una única consulta HTTP.

---

# Discovery Rule

Tipo:

```
External Check
```

Key:

```
unifi.py[
discovery,
{$UNIFI.URL},
{$UNIFI.USER},
{$UNIFI.PASSWORD},
{$UNIFI.SITE}
]
```

Intervalo recomendado:

```
1 hora
```

El descubrimiento genera automáticamente un conjunto de Item Prototypes para cada Access Point encontrado.

---

# Item Prototypes

Todos los elementos descubiertos son **Dependent Items** cuyo origen es el Master Item.

Actualmente se generan automáticamente:

- Estado del AP
- Firmware
- Clientes conectados
- RX
- TX

RX y TX utilizan el preprocesamiento:

```
Change per second
```

para obtener el caudal en lugar del contador acumulado.

---

# Triggers

Actualmente implementados:

- Access Point Offline

Próximamente:

- Firmware desactualizado
- Alto número de clientes
- Radio saturada
- Reinicios frecuentes

---

# Métricas disponibles

Actualmente:

- Estado
- Firmware
- Clientes conectados
- RX
- TX

---

# Próximas métricas

Se prevé incorporar:

- CPU
- Memoria
- Uptime
- Radio Utilization
- TX Power
- Canal
- Channel Width
- Clientes por radio
- Información PoE
- Estadísticas inalámbricas avanzadas

---

# Troubleshooting

## Error 401 Unauthorized

Verificar:

- usuario
- contraseña
- Site configurado

---

## No se descubren Access Points

Verificar:

- que el AP esté adoptado
- que pertenezca al Site consultado
- que tenga nombre configurado

---

## Script unsupported

Verificar:

- permisos de ejecución
- montaje del volumen `externalscripts`
- Python instalado en el contenedor

---

## RX/TX incorrectos

Configurar los ítems utilizando:

```
Change per second
```

---

# Estado actual

## Alcance actual (2026-10-31)

La integración está **operativa solo en un sitio**: 4 items de external check
(`unifi.py[devices,...]` y `unifi.py[discovery,...]`).

En el resto de los sitios y en el lab hay **0 items de external check**: el script se
despliega con el stack (el server monta `../scripts`) pero no se usa.

Recordatorio operativo: el wrapper `scripts/unifi.py` hace `os.execv` de
`scripts/unifi/unifi.py`, así que ese archivo **debe conservar el bit de
ejecución en git** (`100755`). Si se pierde, el external check devuelve
`PermissionError` en lugar de JSON.

## Implementado

- Autenticación mediante UniFi Network API
- Cliente Python reutilizable
- Wrapper para Zabbix External Checks
- Master Item basado en JSON
- Descubrimiento automático (LLD)
- Dependent Items
- Estado del AP
- Firmware
- Clientes conectados
- RX/TX

## Pendiente

- Métricas avanzadas de radio
- Dashboard específico de UniFi
- Monitoreo de Switches UniFi
- Monitoreo de Gateways UniFi
- Exportación del template oficial
