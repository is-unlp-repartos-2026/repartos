"""Asignación automática de pedidos (regla de HU-04).

No es una HU propia: la usan todas las que necesitan buscarle repartidor a un pedido (registrar,
comenzar y terminar jornada, reasignar, rechazar, deshabilitar repartidor y modificar pedido).
"""

from sqlalchemy import RowMapping
from sqlalchemy.orm import Session

from repartos.models import EstadoPedido
from repartos.repositories import cambios_estado, pedidos, repartidores


def asignar(
    db: Session,
    pedido: RowMapping,
    excluir_repartidor_id: int | None = None,
    detalle: str = "Asignación automática",
) -> RowMapping | None:
    """Busca un repartidor apto para el pedido y se lo asigna. Devuelve el repartidor (id, nombre) o None.

    Si no hay ninguno apto, no cambia nada: quien llama decide en qué estado queda el pedido.
    No hace commit: es parte de la transacción de la HU que la llama.
    """
    repartidor = repartidores.buscar_apto_y_bloquear(
        db,
        peso_kg=pedido["peso_kg"],
        alto_cm=pedido["alto_cm"],
        ancho_cm=pedido["ancho_cm"],
        largo_cm=pedido["largo_cm"],
        excluir_id=excluir_repartidor_id,
    )
    if repartidor is None:
        return None

    pedidos.asignar_repartidor(db, pedido["id"], repartidor["id"])
    repartidores.registrar_asignacion(db, repartidor["id"])
    cambios_estado.insertar(
        db, pedido["id"], EstadoPedido.REPARTIDOR_ASIGNADO, repartidor_id=repartidor["id"], detalle=detalle
    )
    return repartidor


def reasignar(db: Session, pedido: RowMapping, excluir_repartidor_id: int, motivo: str) -> RowMapping | None:
    """Le saca el pedido a un repartidor y lo asigna a otro apto; si no hay, vuelve a "registrado".

    La usan las HU que le quitan pedidos a un repartidor: terminar jornada, reasignar, rechazar,
    deshabilitar repartidor. `motivo` queda en el historial. Devuelve el nuevo repartidor o None.
    """
    nuevo = asignar(db, pedido, excluir_repartidor_id=excluir_repartidor_id, detalle=f"Reasignado: {motivo}")
    if nuevo is None:
        pedidos.volver_a_registrado(db, pedido["id"])
        cambios_estado.insertar(
            db, pedido["id"], EstadoPedido.REGISTRADO, detalle=f"Sin otro repartidor apto: {motivo}"
        )
    return nuevo
