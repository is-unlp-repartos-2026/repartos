# Repartos

Sistema de gestión de repartos para comercios de barrio. Proyecto de Ingeniería de Software (UNLP).

## Requisitos

- [Git](https://git-scm.com/downloads)
- [VS Code](https://code.visualstudio.com/)
- [uv](https://docs.astral.sh/uv/getting-started/installation/)

Instalar uv:

```bash
# Linux / macOS
curl -LsSf https://astral.sh/uv/install.sh | sh

# Windows (PowerShell)
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

No hace falta instalar Python: uv descarga la versión correcta (la de `.python-version`).

## Instalación

```bash
git clone https://github.com/is-unlp-repartos-2026/repartos.git
cd repartos
uv sync
```

## Levantar la app

```bash
uv run fastapi dev
```

- API: http://127.0.0.1:8000
- Documentación interactiva: http://127.0.0.1:8000/docs

## Dependencias

```bash
uv add paquete          # agregar una dependencia
uv add --dev paquete    # agregar una dependencia solo de desarrollo
uv sync                 # sincronizar el entorno (después de cada git pull)
```

`pyproject.toml` y `uv.lock` siempre se commitean juntos.

## Flujo de trabajo

No se puede pushear a `main`: todo cambio entra por Pull Request.

```bash
git switch main
git pull
git switch -c tipo/descripcion     # ej: feat/alta-pedidos, fix/login, docs/readme
# ... cambios ...
git add .
git commit -m "tipo: descripción"
git push -u origin tipo/descripcion
gh pr create --fill                # o desde la web de GitHub
```

Tipos: `feat` (funcionalidad), `fix` (bug), `docs` (documentación), `chore` (configuración).
