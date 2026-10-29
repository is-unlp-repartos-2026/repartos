"""Consultas SQL de la tabla cambios_estado (el historial de cada pedido)."""

from sqlalchemy import text
from sqlalchemy.orm import Session

from repartos.models import EstadoPedido


def insertar(
    db: Session,
    pedido_id: int,
    estado: EstadoPedido,
    repartidor_id: int | None = None,
    detalle: str | None = None,
) -> None:
    """Registra que el pedido pasó a `estado`. La fecha y hora la pone la base (now())."""
    db.execute(
        text(
            "INSERT INTO cambios_estado (pedido_id, estado, repartidor_id, detalle) "
            "VALUES (:pedido_id, :estado, :repartidor_id, :detalle)"
        ),
        {"pedido_id": pedido_id, "estado": estado, "repartidor_id": repartidor_id, "detalle": detalle},
    )
