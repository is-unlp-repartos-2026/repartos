"""Reglas de la jornada laboral del repartidor (HU-13 Comenzar jornada laboral)."""

from sqlalchemy.orm import Session

from repartos.repositories import pedidos, repartidores
from repartos.schemas.jornada import JornadaComenzada
from repartos.services import asignacion


class JornadaYaComenzada(Exception):
    """El repartidor ya está activo."""


def comenzar_jornada(db: Session, repartidor_id: int) -> JornadaComenzada:
    """Activa al repartidor y le asigna los pedidos pendientes ("registrado") que puede llevar."""
    repartidor = repartidores.buscar_por_id(db, repartidor_id)
    if repartidor["activo"]:
        raise JornadaYaComenzada

    # Primero se activa: así la regla de asignación ya lo cuenta como apto.
    repartidores.cambiar_activo(db, repartidor_id, True)

    pendientes = pedidos.buscar_registrados_que_puede_llevar_y_bloquear(
        db,
        peso_max_kg=repartidor["peso_max_kg"],
        alto_max_cm=repartidor["alto_max_cm"],
        ancho_max_cm=repartidor["ancho_max_cm"],
        largo_max_cm=repartidor["largo_max_cm"],
    )
    # Se usa la regla general (y no "dárselos todos a él"): si justo hay otro repartidor apto
    # que hace más tiempo que no recibe un pedido, le toca a ese. Normalmente el único apto es él,
    # porque si hubiera habido otro, estos pedidos no estarían pendientes.
    asignados = 0
    for pedido in pendientes:
        if asignacion.asignar(db, pedido, detalle="Asignación al comenzar la jornada") is not None:
            asignados += 1

    db.commit()
    return JornadaComenzada(activo=True, pedidos_asignados=asignados)
