"""Reglas de las acciones del repartidor sobre sus pedidos (HU-18 Retirar pedido)."""

from sqlalchemy import RowMapping
from sqlalchemy.orm import Session

from repartos.models import EstadoPedido
from repartos.repositories import cambios_estado, pedidos
from repartos.schemas.pedidos import EstadoActualizado
from repartos.services.pedidos import EstadoNoPermitido, PedidoNoEncontrado


def _pedido_del_repartidor(db: Session, pedido_id: int, repartidor_id: int) -> RowMapping:
    """Trae (y bloquea) el pedido si es de este repartidor.

    Si existe pero es de otro, responde lo mismo que si no existiera: así un repartidor no puede
    averiguar qué pedidos existen probando números.
    """
    pedido = pedidos.buscar_por_id_y_bloquear(db, pedido_id)
    if pedido is None or pedido["repartidor_id"] != repartidor_id:
        raise PedidoNoEncontrado
    return pedido


def retirar_pedido(db: Session, pedido_id: int, repartidor_id: int) -> EstadoActualizado:
    """HU-18: el repartidor retira el pedido en el comercio y pasa a "en camino"."""
    pedido = _pedido_del_repartidor(db, pedido_id, repartidor_id)
    if pedido["estado"] != EstadoPedido.REPARTIDOR_ASIGNADO:
        raise EstadoNoPermitido

    pedidos.cambiar_estado(db, pedido_id, EstadoPedido.EN_CAMINO)
    cambios_estado.insertar(db, pedido_id, EstadoPedido.EN_CAMINO, repartidor_id=repartidor_id)
    db.commit()
    return EstadoActualizado(id=pedido_id, estado=EstadoPedido.EN_CAMINO)
