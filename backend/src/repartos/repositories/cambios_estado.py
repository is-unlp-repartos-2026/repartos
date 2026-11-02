"""Consultas SQL de la tabla cambios_estado (el historial de cada pedido)."""

from sqlalchemy import RowMapping, text
from sqlalchemy.orm import Session

from repartos.models import EstadoPedido


def insertar(
    db: Session,
    pedido_id: int,
    estado: EstadoPedido,
    repartidor_id: int | None = None,
    detalle: str | None = None,
    modificacion: bool = False,
) -> None:
    """Registra que el pedido pasó a `estado`. La fecha y hora la pone la base (now()).

    Con modificacion=True no es un cambio de estado sino una corrección de datos (HU-05): `estado` es el
    que tenía el pedido en ese momento.
    """
    db.execute(
        text(
            "INSERT INTO cambios_estado (pedido_id, estado, repartidor_id, detalle, modificacion) "
            "VALUES (:pedido_id, :estado, :repartidor_id, :detalle, :modificacion)"
        ),
        {
            "pedido_id": pedido_id,
            "estado": estado,
            "repartidor_id": repartidor_id,
            "detalle": detalle,
            "modificacion": modificacion,
        },
    )


def listar_de_pedido(db: Session, pedido_id: int) -> list[RowMapping]:
    """El historial del pedido, del primer cambio al último, con el nombre del repartidor de cada cambio.

    LEFT JOIN (y no JOIN): los cambios sin repartidor (por ejemplo, "registrado") también tienen que salir;
    en esos, repartidor_nombre viene NULL.
    """
    resultado = db.execute(
        text(
            "SELECT c.estado, c.fecha_hora, c.repartidor_id, r.nombre AS repartidor_nombre, c.detalle, c.modificacion "
            "FROM cambios_estado c "
            "LEFT JOIN repartidores r ON r.id = c.repartidor_id "
            "WHERE c.pedido_id = :pedido_id ORDER BY c.fecha_hora, c.id"
        ),
        {"pedido_id": pedido_id},
    )
    return list(resultado.mappings())
