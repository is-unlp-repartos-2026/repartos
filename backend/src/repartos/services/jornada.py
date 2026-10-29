"""Reglas de la jornada laboral del repartidor (HU-13 Comenzar y HU-14 Terminar jornada laboral)."""

from sqlalchemy.orm import Session

from repartos.repositories import pedidos, repartidores
from repartos.schemas.jornada import JornadaComenzada, JornadaTerminada
from repartos.services import asignacion


class JornadaYaComenzada(Exception):
    """El repartidor ya está activo."""


class JornadaNoComenzada(Exception):
    """El repartidor no está activo: no tiene jornada que terminar."""


class TienePedidosEnCamino(Exception):
    """No puede terminar la jornada con pedidos retirados sin entregar."""


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


def terminar_jornada(db: Session, repartidor_id: int) -> JornadaTerminada:
    """Desactiva al repartidor y reasigna sus pedidos "repartidor asignado" (si no hay otro apto, quedan "registrado")."""
    # Bloquea al repartidor: si justo se le está asignando un pedido nuevo, espera y después lo ve.
    repartidor = repartidores.buscar_por_id_y_bloquear(db, repartidor_id)
    if not repartidor["activo"]:
        raise JornadaNoComenzada
    if pedidos.contar_en_camino_de(db, repartidor_id) > 0:
        raise TienePedidosEnCamino

    repartidores.cambiar_activo(db, repartidor_id, False)

    reasignados = 0
    sin_repartidor = 0
    for pedido in pedidos.buscar_asignados_a_y_bloquear(db, repartidor_id):
        if asignacion.reasignar(db, pedido, repartidor_id, motivo="el repartidor terminó su jornada"):
            reasignados += 1
        else:
            sin_repartidor += 1

    db.commit()
    return JornadaTerminada(activo=False, pedidos_reasignados=reasignados, pedidos_sin_repartidor=sin_repartidor)
