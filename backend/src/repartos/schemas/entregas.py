"""Schemas de las acciones del repartidor sobre sus pedidos."""

from pydantic import BaseModel

from repartos.models import EstadoPedido


class EstadoActualizado(BaseModel):
    """Respuesta de un cambio de estado: el pedido y el estado en que quedó."""

    id: int
    estado: EstadoPedido
