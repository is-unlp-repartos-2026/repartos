"""Clase base de todos los modelos (tablas) de SQLAlchemy."""

from sqlalchemy import MetaData
from sqlalchemy.orm import DeclarativeBase

# Nombres de las restricciones: los mismos que PostgreSQL usa por defecto.
# Así Alembic puede borrarlas por nombre en los downgrade.
CONVENCION_DE_NOMBRES = {
    "pk": "%(table_name)s_pkey",
    "uq": "%(table_name)s_%(column_0_name)s_key",
    "fk": "%(table_name)s_%(column_0_name)s_fkey",
    "ix": "ix_%(table_name)s_%(column_0_name)s",
    "ck": "%(table_name)s_%(constraint_name)s_check",
}


class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=CONVENCION_DE_NOMBRES)