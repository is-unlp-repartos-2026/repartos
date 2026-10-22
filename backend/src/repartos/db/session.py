"""Conexión a la base de datos.

- engine: la conexión física con PostgreSQL. Se crea una sola vez.
- SessionLocal: fábrica de sesiones. Una sesión es una "conversación" con la base.
- get_db: entrega una sesión por cada pedido HTTP y la cierra al terminar.
"""

from collections.abc import Generator
from typing import Annotated

from fastapi import Depends
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from repartos.core.config import settings

engine = create_engine(settings.database_url)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def get_db() -> Generator[Session]:
    """Dependencia de FastAPI: los routers la piden con Depends(get_db)."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# Atajo para usar en los routers: `db: SesionDB` en lugar de `db: Session = Depends(get_db)`.
SesionDB = Annotated[Session, Depends(get_db)]
