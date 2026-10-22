"""Configuración de Alembic.

Alembic compara los modelos (src/repartos/models/) con la base de datos y genera las migraciones.
La dirección de la base se toma de la misma configuración que usa la app (el .env), salvo que quien
ejecuta Alembic pase otra (los tests la usan para aplicar las migraciones a la base de prueba).
"""

from logging.config import fileConfig

from alembic import context
from sqlalchemy import create_engine, pool

import repartos.models  # noqa: F401  (registra todas las tablas en Base.metadata)
from repartos.core.config import settings
from repartos.db.base import Base

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Las tablas que Alembic tiene que mantener: las de nuestros modelos.
target_metadata = Base.metadata

# Por defecto, la base del .env. Los tests pasan la URL de la base de prueba en config.attributes["url"].
url_base = config.attributes.get("url", settings.database_url)


def run_migrations_offline() -> None:
    """Genera el SQL sin conectarse a la base (uv run alembic upgrade head --sql)."""
    context.configure(
        url=url_base,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Se conecta a la base y aplica las migraciones."""
    engine = create_engine(url_base, poolclass=pool.NullPool)
    with engine.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            # Que el autogenerate también detecte cambios en los valores por defecto de las columnas.
            compare_server_default=True,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
