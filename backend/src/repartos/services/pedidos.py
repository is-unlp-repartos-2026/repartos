"""Reglas de los pedidos del lado del operario (HU-04 Registrar, HU-06 Cancelar, HU-23 Consultar detalle)."""

from pathlib import Path

from sqlalchemy.orm import Session

from repartos.core.config import settings
from repartos.core.security import generar_codigo_seguimiento
from repartos.models import EstadoPedido
from repartos.repositories import cambios_estado, pedidos
from repartos.schemas.pedidos import (
    CambioDeEstadoOperario,
    DatosNuevoPedido,
    DetallePedidoOperario,
    EstadoActualizado,
    PedidoRegistrado,
    RepartidorDelPedido,
)
from repartos.services import asignacion

class PedidoNoEncontrado(Exception):
    """El pedido no existe (o, para un repartidor, no es suyo)."""


class EstadoNoPermitido(Exception):
    """El pedido no está en un estado que permita esa acción."""


AVISO_SIN_REPARTIDOR = (
    "No hay ningún repartidor disponible que pueda llevar este pedido. "
    "Quedó registrado y se asignará cuando haya uno."
)


def _nuevo_codigo_seguimiento(db: Session) -> str:
    """Genera códigos hasta encontrar uno que no esté usado.

    Con 850 mil millones de combinaciones, repetir es casi imposible, pero si pasa no se rompe nada.
    """
    while True:
        codigo = generar_codigo_seguimiento()
        if not pedidos.existe_codigo_seguimiento(db, codigo):
            return codigo


def registrar_pedido(db: Session, datos: DatosNuevoPedido) -> PedidoRegistrado:
    """Registra el pedido, lo asigna automáticamente si hay un repartidor apto y devuelve el resultado."""
    pedido = pedidos.insertar(
        db,
        codigo_seguimiento=_nuevo_codigo_seguimiento(db),
        origen=datos.origen.strip(),
        destino=datos.destino.strip(),
        receptor_nombre=datos.receptor_nombre.strip(),
        receptor_dni=datos.receptor_dni,
        peso_kg=datos.peso_kg,
        alto_cm=datos.alto_cm,
        ancho_cm=datos.ancho_cm,
        largo_cm=datos.largo_cm,
    )
    # Primer registro del historial: de acá salen la fecha y hora en que se registró el pedido.
    cambios_estado.insertar(db, pedido["id"], EstadoPedido.REGISTRADO)

    repartidor = asignacion.asignar(db, pedido)
    # Todo junto en una transacción: o queda el pedido con su historial y su asignación, o no queda nada.
    db.commit()

    if repartidor is None:
        return PedidoRegistrado(**pedido, repartidor=None, aviso=AVISO_SIN_REPARTIDOR)
    return PedidoRegistrado(
        **(dict(pedido) | {"estado": EstadoPedido.REPARTIDOR_ASIGNADO, "repartidor_id": repartidor["id"]}),
        repartidor=RepartidorDelPedido(**repartidor),
    )


def cancelar_pedido(db: Session, pedido_id: int) -> EstadoActualizado:
    """HU-06: solo hasta "repartidor asignado" inclusive (después el paquete ya está en la calle)."""
    pedido = pedidos.buscar_por_id_y_bloquear(db, pedido_id)
    if pedido is None:
        raise PedidoNoEncontrado
    if pedido["estado"] not in (EstadoPedido.REGISTRADO, EstadoPedido.REPARTIDOR_ASIGNADO):
        raise EstadoNoPermitido

    # El repartidor_id se conserva: queda registrado a quién estaba asignado cuando se canceló.
    pedidos.cambiar_estado(db, pedido_id, EstadoPedido.CANCELADO)
    cambios_estado.insertar(
        db, pedido_id, EstadoPedido.CANCELADO, repartidor_id=pedido["repartidor_id"], detalle="Cancelado por el operario"
    )
    db.commit()
    return EstadoActualizado(id=pedido_id, estado=EstadoPedido.CANCELADO)


def _repartidor(repartidor_id: int | None, nombre: str | None) -> RepartidorDelPedido | None:
    return RepartidorDelPedido(id=repartidor_id, nombre=nombre) if repartidor_id is not None else None


def detalle_pedido(db: Session, pedido_id: int) -> DetallePedidoOperario:
    """HU-23: datos, código, repartidor e historial; si se entregó, la foto; si falló, el motivo."""
    pedido = pedidos.buscar_detalle(db, pedido_id)
    if pedido is None:
        raise PedidoNoEncontrado

    historial = [
        CambioDeEstadoOperario(
            estado=c["estado"],
            fecha_hora=c["fecha_hora"],
            repartidor=_repartidor(c["repartidor_id"], c["repartidor_nombre"]),
            detalle=c["detalle"],
        )
        for c in cambios_estado.listar_de_pedido(db, pedido_id)
    ]
    return DetallePedidoOperario(
        **{k: v for k, v in pedido.items() if k not in ("repartidor_id", "repartidor_nombre", "foto_entrega")},
        repartidor=_repartidor(pedido["repartidor_id"], pedido["repartidor_nombre"]),
        historial=historial,
        foto_url=f"/operario/pedidos/{pedido_id}/foto" if pedido["foto_entrega"] else None,
    )


def ruta_foto(db: Session, pedido_id: int) -> Path:
    """El archivo de la foto de la entrega. PedidoNoEncontrado si el pedido no existe o no tiene foto."""
    pedido = pedidos.buscar_detalle(db, pedido_id)
    if pedido is None or not pedido["foto_entrega"]:
        raise PedidoNoEncontrado
    ruta = settings.carpeta_fotos / pedido["foto_entrega"]
    if not ruta.is_file():
        raise PedidoNoEncontrado
    return ruta
