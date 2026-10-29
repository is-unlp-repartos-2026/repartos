"""Reglas de los pedidos (HU-04 Registrar pedido)."""

from sqlalchemy.orm import Session

from repartos.core.security import generar_codigo_seguimiento
from repartos.models import EstadoPedido
from repartos.repositories import cambios_estado, pedidos
from repartos.schemas.pedidos import DatosNuevoPedido, PedidoRegistrado, RepartidorDelPedido
from repartos.services import asignacion

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
