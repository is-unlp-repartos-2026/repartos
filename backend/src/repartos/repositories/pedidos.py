"""Consultas SQL de la tabla pedidos."""

from sqlalchemy import RowMapping, text
from sqlalchemy.orm import Session

from repartos.models import EstadoPedido

# Columnas que se devuelven al leer un pedido.
_COLUMNAS = (
    "id, codigo_seguimiento, origen, destino, receptor_nombre, receptor_dni, "
    "peso_kg, alto_cm, ancho_cm, largo_cm, estado, repartidor_id"
)


def existe_codigo_seguimiento(db: Session, codigo: str) -> bool:
    resultado = db.execute(
        text("SELECT EXISTS (SELECT 1 FROM pedidos WHERE codigo_seguimiento = :codigo)"),
        {"codigo": codigo},
    )
    return resultado.scalar_one()


def insertar(
    db: Session,
    codigo_seguimiento: str,
    origen: str,
    destino: str,
    receptor_nombre: str,
    receptor_dni: str,
    peso_kg: float,
    alto_cm: float,
    ancho_cm: float,
    largo_cm: float,
) -> RowMapping:
    """Inserta un pedido y devuelve la fila creada. El estado no se manda: la base pone "registrado"."""
    resultado = db.execute(
        text(
            "INSERT INTO pedidos "
            "(codigo_seguimiento, origen, destino, receptor_nombre, receptor_dni, "
            "peso_kg, alto_cm, ancho_cm, largo_cm) "
            "VALUES (:codigo_seguimiento, :origen, :destino, :receptor_nombre, :receptor_dni, "
            ":peso_kg, :alto_cm, :ancho_cm, :largo_cm) "
            f"RETURNING {_COLUMNAS}"  # _COLUMNAS es texto fijo del código, nunca un dato del usuario
        ),
        {
            "codigo_seguimiento": codigo_seguimiento,
            "origen": origen,
            "destino": destino,
            "receptor_nombre": receptor_nombre,
            "receptor_dni": receptor_dni,
            "peso_kg": peso_kg,
            "alto_cm": alto_cm,
            "ancho_cm": ancho_cm,
            "largo_cm": largo_cm,
        },
    )
    return resultado.mappings().one()


def asignar_repartidor(db: Session, pedido_id: int, repartidor_id: int) -> None:
    """Pasa el pedido a "repartidor asignado" con ese repartidor."""
    db.execute(
        text("UPDATE pedidos SET estado = :estado, repartidor_id = :repartidor_id WHERE id = :id"),
        {"estado": EstadoPedido.REPARTIDOR_ASIGNADO, "repartidor_id": repartidor_id, "id": pedido_id},
    )
