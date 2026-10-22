"""Consultas SQL de la tabla operarios.

Los repositories solo ejecutan SQL: no deciden reglas de negocio ni hacen commit.
Quien los llama (un service o un comando) decide cuándo confirmar la transacción.
"""

from sqlalchemy import RowMapping, text
from sqlalchemy.orm import Session


def buscar_por_usuario(db: Session, usuario: str) -> RowMapping | None:
    """Devuelve el operario con ese usuario (id, usuario, password_hash) o None si no existe."""
    resultado = db.execute(
        text("SELECT id, usuario, password_hash FROM operarios WHERE usuario = :usuario"),
        {"usuario": usuario},
    )
    # mappings(): cada fila como diccionario (fila["usuario"]); first(): la primera fila o None.
    return resultado.mappings().first()


def buscar_por_id(db: Session, operario_id: int) -> RowMapping | None:
    """Devuelve el operario con ese id (id, usuario) o None si no existe."""
    resultado = db.execute(
        text("SELECT id, usuario FROM operarios WHERE id = :id"),
        {"id": operario_id},
    )
    return resultado.mappings().first()


def insertar(db: Session, usuario: str, password_hash: str) -> int:
    """Inserta un operario y devuelve su id (RETURNING le pide a PostgreSQL el id que generó)."""
    resultado = db.execute(
        text(
            "INSERT INTO operarios (usuario, password_hash) "
            "VALUES (:usuario, :password_hash) "
            "RETURNING id"
        ),
        {"usuario": usuario, "password_hash": password_hash},
    )
    return resultado.scalar_one()
