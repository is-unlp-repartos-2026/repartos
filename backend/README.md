# Backend

API de SIGER en Python (FastAPI) con base de datos PostgreSQL.
Todos los comandos de este archivo se corren **dentro de la carpeta `backend/`**.

## Requisitos

- [uv](https://docs.astral.sh/uv/getting-started/installation/): maneja Python, el entorno y las dependencias.
  No hace falta instalar Python: uv descarga la versión de `.python-version`.
- [Docker](https://docs.docker.com/get-docker/) (en Windows y macOS, Docker Desktop): levanta la base de datos.

```bash
# Instalar uv en Linux / macOS
curl -LsSf https://astral.sh/uv/install.sh | sh
# Instalar uv en Windows (PowerShell)
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

## Primera vez

```bash
cd backend
cp .env.example .env              # configuración local (no se sube al repo)
uv sync                           # crea el entorno e instala las dependencias
docker compose up -d              # levanta PostgreSQL en segundo plano
uv run alembic upgrade head       # crea las tablas en la base
```

## Día a día

```bash
git pull
uv sync                           # por si alguien agregó dependencias
docker compose up -d              # si la base no está corriendo
uv run alembic upgrade head       # por si alguien agregó migraciones
uv run fastapi dev                # levanta la API
```

- API: http://127.0.0.1:8000
- Documentación interactiva: http://127.0.0.1:8000/docs

## Base de datos

```bash
docker compose up -d              # levantar la base
docker compose stop               # apagarla (los datos se conservan)
docker compose down -v            # borrarla por completo, con todos sus datos
```

Si el puerto 5432 ya está ocupado en tu máquina, cambiá `POSTGRES_PORT` en tu `.env` (por ejemplo, 5433)
y el mismo número en `DATABASE_URL`.

## Migraciones (cambios en las tablas)

Cada cambio en `src/repartos/models/` necesita una migración:

```bash
uv run alembic revision --autogenerate -m "descripción del cambio"   # genera la migración
# revisar el archivo generado en migrations/versions/ antes de seguir
uv run alembic upgrade head                                          # aplica las migraciones pendientes
uv run alembic downgrade -1                                          # deshace la última
```

## Dependencias

```bash
uv add paquete          # agregar una dependencia
uv add --dev paquete    # agregar una dependencia solo de desarrollo
uv sync                 # sincronizar el entorno (después de cada git pull)
```

`pyproject.toml` y `uv.lock` siempre se commitean juntos.

## Organización del código

```
src/repartos/
├── main.py      arma la app y registra los routers
├── core/        configuración general (lee el .env)
├── db/          conexión a la base de datos
├── models/      tablas de la base de datos
├── schemas/     datos que entran y salen de la API
├── services/    reglas de negocio de las historias de usuario
└── routers/     endpoints, uno por interfaz (operario, repartidor, seguimiento)
```

Regla: el router recibe el pedido y llama a un service; el service aplica las reglas y usa los models.
Las reglas de negocio van solo en `services/`.
