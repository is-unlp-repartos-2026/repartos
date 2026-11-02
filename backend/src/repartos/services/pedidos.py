"""Reglas de los pedidos del lado del operario (HU-04 Registrar, HU-06 Cancelar, HU-23 Consultar detalle,
HU-22 Monitorear pedidos en curso, HU-08 Reasignar pedido, HU-05 Modificar pedido, HU-24 Historial)."""

from datetime import date
from pathlib import Path

from sqlalchemy.orm import Session

from repartos.core import fechas
from repartos.core.config import settings
from repartos.core.security import generar_codigo_seguimiento
from repartos.models import EstadoPedido
from repartos.repositories import cambios_estado, pedidos, repartidores
from repartos.schemas.pedidos import (
    CambioDeEstadoOperario,
    DatosNuevoPedido,
    DatosReasignacion,
    DetallePedidoOperario,
    EstadoActualizado,
    PedidoEnHistorial,
    PedidoEnTablero,
    PedidoRegistrado,
    RepartidorDelPedido,
    ResultadoModificacion,
    ResultadoReasignacion,
    Tablero,
)
from repartos.services import asignacion

class PedidoNoEncontrado(Exception):
    """El pedido no existe (o, para un repartidor, no es suyo)."""


class EstadoNoPermitido(Exception):
    """El pedido no está en un estado que permita esa acción."""


class PeriodoInvalido(Exception):
    """La fecha "desde" es posterior a la fecha "hasta"."""


AVISO_SIN_REPARTIDOR = (
    "No hay ningún repartidor disponible que pueda llevar este pedido. "
    "Quedó registrado y se asignará cuando haya uno."
)
AVISO_SIN_OTRO_REPARTIDOR = (
    "No hay otro repartidor disponible que pueda llevar este pedido. "
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
            modificacion=c["modificacion"],
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


def tablero(db: Session) -> Tablero:
    """HU-22: los pedidos en curso, cada uno en el grupo de su estado."""
    grupos: dict[str, list[PedidoEnTablero]] = {
        EstadoPedido.REGISTRADO: [],
        EstadoPedido.REPARTIDOR_ASIGNADO: [],
        EstadoPedido.EN_CAMINO: [],
    }
    for fila in pedidos.listar_en_curso(db):
        grupos[fila["estado"]].append(
            PedidoEnTablero(
                id=fila["id"],
                codigo_seguimiento=fila["codigo_seguimiento"],
                origen=fila["origen"],
                destino=fila["destino"],
                repartidor=_repartidor(fila["repartidor_id"], fila["repartidor_nombre"]),
                desde=fila["desde"],
            )
        )
    return Tablero(
        registrado=grupos[EstadoPedido.REGISTRADO],
        repartidor_asignado=grupos[EstadoPedido.REPARTIDOR_ASIGNADO],
        en_camino=grupos[EstadoPedido.EN_CAMINO],
    )


def reasignar_pedido(db: Session, pedido_id: int, datos: DatosReasignacion) -> ResultadoReasignacion:
    """HU-08: solo en "repartidor asignado"; busca otro apto excluyendo al actual y guarda el motivo."""
    pedido = pedidos.buscar_por_id_y_bloquear(db, pedido_id)
    if pedido is None:
        raise PedidoNoEncontrado
    if pedido["estado"] != EstadoPedido.REPARTIDOR_ASIGNADO:
        raise EstadoNoPermitido

    nuevo = asignacion.reasignar(db, pedido, pedido["repartidor_id"], motivo=datos.motivo)
    db.commit()

    if nuevo is None:
        return ResultadoReasignacion(
            id=pedido_id, estado=EstadoPedido.REGISTRADO, repartidor=None, aviso=AVISO_SIN_OTRO_REPARTIDOR
        )
    return ResultadoReasignacion(
        id=pedido_id, estado=EstadoPedido.REPARTIDOR_ASIGNADO, repartidor=RepartidorDelPedido(**nuevo)
    )


# Nombre de cada dato del pedido tal como se lee en el historial ("Datos modificados: destino, peso").
_DATOS_DEL_PEDIDO = {
    "origen": "origen",
    "destino": "destino",
    "receptor_nombre": "nombre de quien recibe",
    "receptor_dni": "DNI de quien recibe",
    "peso_kg": "peso",
    "alto_cm": "alto",
    "ancho_cm": "ancho",
    "largo_cm": "largo",
}
_MEDIDAS = ("peso_kg", "alto_cm", "ancho_cm", "largo_cm")


def _puede_llevarlo(repartidor: dict, pedido: dict) -> bool:
    return (
        pedido["peso_kg"] <= repartidor["peso_max_kg"]
        and pedido["alto_cm"] <= repartidor["alto_max_cm"]
        and pedido["ancho_cm"] <= repartidor["ancho_max_cm"]
        and pedido["largo_cm"] <= repartidor["largo_max_cm"]
    )


def modificar_pedido(db: Session, pedido_id: int, datos: DatosNuevoPedido) -> ResultadoModificacion:
    """HU-05: hasta "repartidor asignado" inclusive. La corrección queda en el historial.

    Si cambian el peso o las medidas, se reevalúa la asignación:
    - con repartidor: si ya no puede llevarlo, se reasigna a otro apto (o vuelve a "registrado" con aviso);
    - sin repartidor: se intenta asignar (quizás ahora entra en la capacidad de alguien).
    """
    pedido = pedidos.buscar_por_id_y_bloquear(db, pedido_id)
    if pedido is None:
        raise PedidoNoEncontrado
    if pedido["estado"] not in (EstadoPedido.REGISTRADO, EstadoPedido.REPARTIDOR_ASIGNADO):
        raise EstadoNoPermitido

    nuevos = datos.model_dump()
    for campo in ("origen", "destino", "receptor_nombre"):
        nuevos[campo] = nuevos[campo].strip()
    cambiados = [campo for campo in _DATOS_DEL_PEDIDO if nuevos[campo] != pedido[campo]]

    aviso = None
    if cambiados:
        pedidos.modificar_datos(db, pedido_id, **nuevos)
        cambios_estado.insertar(
            db,
            pedido_id,
            pedido["estado"],
            repartidor_id=pedido["repartidor_id"],
            detalle="Datos modificados: " + ", ".join(_DATOS_DEL_PEDIDO[c] for c in cambiados),
            modificacion=True,
        )

        if any(campo in _MEDIDAS for campo in cambiados):
            modificado = pedidos.buscar_por_id(db, pedido_id)  # ya con el peso y las medidas nuevas
            if pedido["repartidor_id"] is None:
                if asignacion.asignar(db, modificado) is None:
                    aviso = AVISO_SIN_REPARTIDOR
            else:
                actual = repartidores.buscar_por_id(db, pedido["repartidor_id"])
                if not _puede_llevarlo(actual, modificado):
                    motivo = f"{actual['nombre']} no puede llevar el pedido modificado"
                    if asignacion.reasignar(db, modificado, actual["id"], motivo=motivo) is None:
                        aviso = AVISO_SIN_OTRO_REPARTIDOR
        db.commit()

    final = pedidos.buscar_detalle(db, pedido_id)
    return ResultadoModificacion(
        id=pedido_id,
        estado=final["estado"],
        repartidor=_repartidor(final["repartidor_id"], final["repartidor_nombre"]),
        aviso=aviso,
    )


def historial(
    db: Session,
    desde: date | None = None,
    hasta: date | None = None,
    estado: EstadoPedido | None = None,
    repartidor_id: int | None = None,
) -> list[PedidoEnHistorial]:
    """HU-24: por defecto, los pedidos registrados hoy; se puede filtrar por fechas, estado y repartidor."""
    desde = desde or fechas.hoy()
    hasta = hasta or fechas.hoy()
    if desde > hasta:
        raise PeriodoInvalido

    return [
        PedidoEnHistorial(
            **{k: v for k, v in fila.items() if k not in ("repartidor_id", "repartidor_nombre")},
            repartidor=_repartidor(fila["repartidor_id"], fila["repartidor_nombre"]),
        )
        for fila in pedidos.listar_historial(db, desde, hasta, settings.zona_horaria, estado, repartidor_id)
    ]
