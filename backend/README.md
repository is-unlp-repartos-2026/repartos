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

## Tests

```bash
docker compose up -d              # los tests necesitan la base levantada
uv run pytest                     # corre todos los tests
uv run pytest -v                  # muestra cada test con su resultado
uv run pytest tests/test_health.py   # corre solo un archivo
```

- Los tests usan una base aparte (`siger_test`), que se crea sola la primera vez y recibe las mismas
  migraciones que la de desarrollo. Tu base de desarrollo no se toca.
- Cada test arranca con la base vacía: lo que crea un test se deshace al terminar.
- Fixtures disponibles (en `tests/conftest.py`):
  - `cliente`: hace requests a la API, por ejemplo `cliente.post("/operario/repartidores", json={...})`.
  - `db`: una sesión de la base de prueba, para preparar datos o verificar resultados con SQL.
- Cada criterio de aceptación de una HU se escribe como un test.

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
├── models/        estructura de las tablas (solo para que Alembic genere las migraciones)
├── repositories/  consultas a la base, escritas en SQL (un archivo por tabla)
├── schemas/       datos que entran y salen de la API
├── services/      reglas de negocio de las historias de usuario
└── routers/       endpoints, uno por interfaz (operario, repartidor, seguimiento)
```

Recorrido de una request: el router recibe el pedido y llama a un service; el service aplica las reglas
de la HU y llama a los repositories; los repositories ejecutan el SQL.

Reglas:

- Las reglas de negocio van solo en `services/`.
- El SQL va solo en `repositories/`. Los models no se usan para consultar.
- Los valores del SQL siempre van como parámetros (`WHERE dni = :dni`), nunca armados con texto
  (`f"WHERE dni = '{dni}'"`): armarlos con texto permite la inyección SQL.
