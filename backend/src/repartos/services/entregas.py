"""Reglas de las acciones del repartidor sobre sus pedidos (HU-18 Retirar pedido, HU-07 Entrega fallida,
HU-20 Confirmar entrega, HU-16 y HU-17 Consultar pedidos asignados y su detalle)."""

from sqlalchemy import RowMapping
from sqlalchemy.orm import Session

from repartos.core import fotos
from repartos.core.config import settings
from repartos.models import EstadoPedido
from repartos.repositories import cambios_estado, pedidos
from repartos.schemas.pedidos import (
    DatosEntregaFallida,
    DetallePedidoAsignado,
    EstadoActualizado,
    PedidoAsignado,
)
from repartos.services.pedidos import EstadoNoPermitido, PedidoNoEncontrado


class FotoInvalida(Exception):
    """El archivo no es una imagen JPG, PNG o WEBP, o es demasiado grande."""


class DniNoCoincide(Exception):
    """El DNI de quien recibe no es el que se cargó en el pedido."""


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


def registrar_entrega_fallida(
    db: Session, pedido_id: int, repartidor_id: int, datos: DatosEntregaFallida
) -> EstadoActualizado:
    """HU-07: solo desde "en camino"; "entrega fallida" es final (el paquete vuelve al comercio)."""
    pedido = _pedido_del_repartidor(db, pedido_id, repartidor_id)
    if pedido["estado"] != EstadoPedido.EN_CAMINO:
        raise EstadoNoPermitido

    motivo = datos.como_texto()
    pedidos.registrar_entrega_fallida(db, pedido_id, motivo)
    cambios_estado.insertar(db, pedido_id, EstadoPedido.ENTREGA_FALLIDA, repartidor_id=repartidor_id, detalle=motivo)
    db.commit()
    return EstadoActualizado(id=pedido_id, estado=EstadoPedido.ENTREGA_FALLIDA)


def confirmar_entrega(
    db: Session, pedido_id: int, repartidor_id: int, foto: bytes, dni: str
) -> EstadoActualizado:
    """HU-20: solo desde "en camino"; foto y DNI obligatorios; el DNI tiene que coincidir con el del pedido."""
    pedido = _pedido_del_repartidor(db, pedido_id, repartidor_id)
    if pedido["estado"] != EstadoPedido.EN_CAMINO:
        raise EstadoNoPermitido
    if dni != pedido["receptor_dni"]:
        raise DniNoCoincide

    extension = fotos.extension_de_imagen(foto)
    if extension is None or len(foto) > settings.tamano_max_foto_mb * 1024 * 1024:
        raise FotoInvalida

    nombre_foto = fotos.guardar(foto, extension)
    try:
        pedidos.registrar_entrega(db, pedido_id, nombre_foto)
        cambios_estado.insertar(
            db, pedido_id, EstadoPedido.ENTREGADO, repartidor_id=repartidor_id, detalle="DNI de quien recibe verificado"
        )
        db.commit()
    except Exception:
        # Si la base falla, no queda una foto suelta en el disco que no corresponde a ningún pedido.
        fotos.borrar(nombre_foto)
        raise
    return EstadoActualizado(id=pedido_id, estado=EstadoPedido.ENTREGADO)


def listar_pedidos_asignados(db: Session, repartidor_id: int) -> list[PedidoAsignado]:
    """HU-16: los pedidos que tiene que hacer (asignados y en camino), por fecha de asignación."""
    return [PedidoAsignado(**fila) for fila in pedidos.listar_en_curso_de(db, repartidor_id)]


def detalle_pedido_asignado(db: Session, pedido_id: int, repartidor_id: int) -> DetallePedidoAsignado:
    """HU-17: el detalle de un pedido que tiene que hacer (asignado o en camino).

    Si no es suyo, o ya terminó (entregado, fallido, cancelado), responde "no encontrado": el repartidor
    solo ve los datos del receptor mientras los necesita para entregar.
    """
    pedido = pedidos.buscar_por_id(db, pedido_id)
    if (
        pedido is None
        or pedido["repartidor_id"] != repartidor_id
        or pedido["estado"] not in (EstadoPedido.REPARTIDOR_ASIGNADO, EstadoPedido.EN_CAMINO)
    ):
        raise PedidoNoEncontrado
    return DetallePedidoAsignado(**pedido)
