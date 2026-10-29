"""Consultas SQL de la tabla repartidores."""

from sqlalchemy import RowMapping, text
from sqlalchemy.orm import Session

# Columnas que se devuelven al leer un repartidor (nunca el hash del código de acceso).
_COLUMNAS = (
    "id, nombre, dni, correo, peso_max_kg, alto_max_cm, ancho_max_cm, largo_max_cm, habilitado, activo"
)


def existe_dni(db: Session, dni: str) -> bool:
    resultado = db.execute(
        # EXISTS corta en cuanto encuentra una fila: no hace falta traer los datos.
        text("SELECT EXISTS (SELECT 1 FROM repartidores WHERE dni = :dni)"),
        {"dni": dni},
    )
    return resultado.scalar_one()


def existe_correo(db: Session, correo: str) -> bool:
    resultado = db.execute(
        # lower(): "Juan@Mail.com" y "juan@mail.com" son el mismo correo.
        text("SELECT EXISTS (SELECT 1 FROM repartidores WHERE lower(correo) = lower(:correo))"),
        {"correo": correo},
    )
    return resultado.scalar_one()


def insertar(
    db: Session,
    nombre: str,
    dni: str,
    correo: str,
    peso_max_kg: float,
    alto_max_cm: float,
    ancho_max_cm: float,
    largo_max_cm: float,
    codigo_acceso_hash: str,
) -> RowMapping:
    """Inserta un repartidor y devuelve la fila creada.

    habilitado y activo no se mandan: los pone la base con su valor por defecto (habilitado e inactivo).
    RETURNING devuelve la fila tal como quedó guardada, con esos valores incluidos.
    """
    resultado = db.execute(
        text(
            "INSERT INTO repartidores "
            "(nombre, dni, correo, peso_max_kg, alto_max_cm, ancho_max_cm, largo_max_cm, codigo_acceso_hash) "
            "VALUES (:nombre, :dni, :correo, :peso_max_kg, :alto_max_cm, :ancho_max_cm, :largo_max_cm, "
            ":codigo_acceso_hash) "
            f"RETURNING {_COLUMNAS}"  # _COLUMNAS es texto fijo del código, nunca un dato del usuario
        ),
        {
            "nombre": nombre,
            "dni": dni,
            "correo": correo,
            "peso_max_kg": peso_max_kg,
            "alto_max_cm": alto_max_cm,
            "ancho_max_cm": ancho_max_cm,
            "largo_max_cm": largo_max_cm,
            "codigo_acceso_hash": codigo_acceso_hash,
        },
    )
    return resultado.mappings().one()
