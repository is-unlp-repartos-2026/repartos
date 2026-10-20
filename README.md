# Repartos

Sistema de gestión de repartos para comercios de barrio. Proyecto de Ingeniería de Software (UNLP).

## Estructura del repositorio

```
repartos/
├── backend/    API en Python (FastAPI) y base de datos (PostgreSQL). Ver backend/README.md
└── frontend/   Web del operario, web del cliente final y app del repartidor. Ver frontend/README.md
```

## Requisitos generales

- [Git](https://git-scm.com/downloads)
- [VS Code](https://code.visualstudio.com/)

Cada parte tiene sus propios requisitos e instrucciones en su README.

```bash
git clone https://github.com/is-unlp-repartos-2026/repartos.git
cd repartos
```

## Flujo de trabajo

No se puede pushear a `main`: todo cambio entra por Pull Request y necesita la aprobación de otro integrante.

```bash
git switch main
git pull
git switch -c tipo/descripcion     # ej: feat/hu-04-registrar-pedido, fix/login, docs/readme
# ... cambios ...
git status                         # revisar qué se va a subir
git add archivo1 archivo2
git commit -m "tipo: descripción"
git push -u origin tipo/descripcion
gh pr create --fill                # o desde la web de GitHub
```

Tipos: `feat` (funcionalidad), `fix` (bug), `docs` (documentación), `chore` (configuración).

Si después de aprobado el PR se suben más cambios, la aprobación se descarta y hay que volver a revisarlo.
