# Repositorios por cliente

Regla del proyecto: **un repo genérico público y un repo privado por cliente**.
El genérico nunca contiene particularidades de un cliente; cada cliente vive en
su propio repositorio privado, y es ese repo el que se despliega en **su**
servidor.

## Modelo

| Repo | Visibilidad | Qué contiene | Dónde se clona |
|---|---|---|---|
| `zbx-in-docker` (genérico) | público | stack, scripts, docs y templates genéricos | solo en la máquina de trabajo del administrador |
| `zbx-in-docker-<cliente>` | privado | el genérico + `client/` con sus particularidades | en el servidor del cliente: `/opt/monitoring/zbx-in-docker` |

El repo privado es un fork del genérico: su `main` es el `main` del genérico
más un commit `chore(client): particularidades de <cliente>` que agrega
`client/`.

## Estructura del repo privado

```
client/
  docs/       documentación del sitio (runbooks, diagnóstico, inventario)
  scripts/    scripts propios del cliente
  templates/  templates Zabbix con particularidades del cliente
docker/ scripts/ systemd/ docs/   idénticos al genérico
```

## Clave SSH y alias por cliente

Cada servidor de cliente tiene su propia deploy key y un alias en
`~/.ssh/config`:

```
Host github.com-zbx-<cliente>
    HostName github.com
    User git
    IdentityFile ~/.ssh/zbx_<cliente>
```

El remoto del checkout del servidor queda así:

```
git@github.com-zbx-<cliente>:<org>/zbx-in-docker-<cliente>.git
```

Nunca se reutiliza la clave de otro cliente ni la del administrador.

## Reglas

1. **Nada con nombre de cliente en el genérico.** Ni docs, ni runbooks, ni
   scripts con valores por defecto de un cliente.
2. **Si una particularidad obliga a tocar el genérico, el genérico no es
   genérico:** se parametriza (config, macro o variable de entorno) y el valor
   concreto queda en el repo privado.
3. **El genérico no se despliega en servidores de clientes.** Lo que corre en
   un servidor es el repo privado de ese cliente.
4. Secretos (`.env`, claves, certificados con clave privada) nunca van a git.
5. El repo del cliente se actualiza con merge desde el `main` del genérico.
   No se copian archivos a mano.

## Alta de un cliente nuevo

1. Crear el repo privado `zbx-in-docker-<cliente>`.
2. En el servidor del cliente, generar la deploy key:
   ```bash
   ssh-keygen -t ed25519 -C "zbx-<cliente>" -f ~/.ssh/zbx_<cliente>
   ```
   y cargar la clave pública como deploy key con permiso de escritura.
3. Agregar el alias `github.com-zbx-<cliente>` a `~/.ssh/config`.
4. Clonar:
   ```bash
   git clone git@github.com-zbx-<cliente>:<org>/zbx-in-docker-<cliente>.git \
     /opt/monitoring/zbx-in-docker
   ```
5. Sembrar desde el genérico:
   ```bash
   cd /opt/monitoring/zbx-in-docker
   git remote add upstream git@github.com:<org>/zbx-in-docker.git
   git fetch upstream
   git merge upstream/main
   ```
6. Crear `client/{docs,scripts,templates}` con las particularidades del sitio.
7. Recrear `docker/.env` desde la bóveda (ver `docs/recupero.md`).
8. Commit `chore(client): particularidades de <cliente>` y push.

## Actualizar un cliente con cambios del genérico

En el checkout del servidor o en un clon local del repo privado:

```bash
git fetch upstream
git merge upstream/main
git push
```

Los conflictos se resuelven solo en archivos de `client/`. Si el conflicto
aparece en un archivo genérico, es señal de que esa particularidad debía
estar parametrizada: corregir el genérico primero y volver a mergear.
