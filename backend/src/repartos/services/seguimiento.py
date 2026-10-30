"""Reglas del seguimiento del cliente final (HU-21 Consultar estado de pedido)."""

from sqlalchemy.orm import Session

from repartos.repositories import cambios_estado, pedidos
from repartos.schemas.seguimiento import CambioDeEstado, EstadoDelPedido
from repartos.services.pedidos import PedidoNoEncontrado


def consultar_estado(db: Session, codigo: str) -> EstadoDelPedido:
    """HU-21: estado actual e historial (con fecha y hora) del pedido con ese código de seguimiento."""
    # Los códigos se generan en mayúsculas: así "ab3k..." también se encuentra.
    pedido = pedidos.buscar_por_codigo_seguimiento(db, codigo.strip().upper())
    if pedido is None:
        raise PedidoNoEncontrado

    historial = cambios_estado.listar_de_pedido(db, pedido["id"])
    return EstadoDelPedido(
        codigo_seguimiento=pedido["codigo_seguimiento"],
        estado=pedido["estado"],
        historial=[CambioDeEstado(estado=c["estado"], fecha_hora=c["fecha_hora"]) for c in historial],
    )
