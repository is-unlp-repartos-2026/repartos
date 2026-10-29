"""Reglas de los repartidores (HU-09 Registrar, HU-10 Listar, HU-12 Habilitar o deshabilitar)."""

from sqlalchemy.orm import Session

from repartos.core.security import generar_codigo_acceso, hashear_codigo_acceso
from repartos.repositories import pedidos, repartidores
from repartos.schemas.repartidores import (
    DatosNuevoRepartidor,
    Repartidor,
    RepartidorDeshabilitado,
    RepartidorRegistrado,
)
from repartos.services import asignacion


class DniRepetido(Exception):
    """Ya hay un repartidor con ese DNI."""


class CorreoRepetido(Exception):
    """Ya hay un repartidor con ese correo."""


class RepartidorNoEncontrado(Exception):
    """No hay un repartidor con ese id."""


class YaEstaEnEseEstado(Exception):
    """Se pidió habilitar a uno ya habilitado, o deshabilitar a uno ya deshabilitado."""


class TienePedidosEnCamino(Exception):
    """No se puede deshabilitar a un repartidor con pedidos retirados sin entregar."""


def registrar_repartidor(db: Session, datos: DatosNuevoRepartidor) -> RepartidorRegistrado:
    """Da de alta un repartidor (habilitado e inactivo) y devuelve sus datos con el código de acceso."""
    if repartidores.existe_dni(db, datos.dni):
        raise DniRepetido
    if repartidores.existe_correo(db, datos.correo):
        raise CorreoRepetido

    # El código en claro solo vive en esta función: se guarda el hash y se le muestra una vez al operario.
    codigo = generar_codigo_acceso()
    fila = repartidores.insertar(
        db,
        nombre=datos.nombre.strip(),
        dni=datos.dni,
        correo=datos.correo,
        peso_max_kg=datos.peso_max_kg,
        alto_max_cm=datos.alto_max_cm,
        ancho_max_cm=datos.ancho_max_cm,
        largo_max_cm=datos.largo_max_cm,
        codigo_acceso_hash=hashear_codigo_acceso(codigo),
    )
    db.commit()

    return RepartidorRegistrado(**fila, codigo_acceso=codigo)


def listar_repartidores(db: Session, habilitado: bool | None = None) -> list[Repartidor]:
    """HU-10: nombre, DNI, carga habilitada, habilitado/deshabilitado y activo/inactivo de cada repartidor."""
    return [Repartidor(**fila) for fila in repartidores.listar(db, habilitado)]


def deshabilitar(db: Session, repartidor_id: int) -> RepartidorDeshabilitado:
    """HU-12: no entra a la app ni recibe pedidos; sus pedidos asignados se reasignan; se conserva su historial.

    No se puede si tiene pedidos en camino (el paquete está con él: primero tiene que terminar esas entregas).
    """
    # Bloqueo: si justo se le está asignando un pedido, espera y después lo ve (igual que terminar jornada).
    repartidor = repartidores.buscar_por_id_y_bloquear(db, repartidor_id)
    if repartidor is None:
        raise RepartidorNoEncontrado
    if not repartidor["habilitado"]:
        raise YaEstaEnEseEstado
    if pedidos.contar_en_camino_de(db, repartidor_id) > 0:
        raise TienePedidosEnCamino

    repartidores.cambiar_habilitado(db, repartidor_id, False)
    # También queda inactivo: si lo vuelven a habilitar, tiene que comenzar la jornada de nuevo.
    repartidores.cambiar_activo(db, repartidor_id, False)
    reasignados, sin_repartidor = asignacion.reasignar_todos_los_de(
        db, repartidor_id, motivo="el repartidor fue deshabilitado"
    )
    db.commit()

    return RepartidorDeshabilitado(
        repartidor=Repartidor(**repartidores.buscar_por_id(db, repartidor_id)),
        pedidos_reasignados=reasignados,
        pedidos_sin_repartidor=sin_repartidor,
    )


def habilitar(db: Session, repartidor_id: int) -> Repartidor:
    """HU-12: recupera el acceso a la app (con el mismo código) y su historial sigue ahí. Queda inactivo."""
    repartidor = repartidores.buscar_por_id_y_bloquear(db, repartidor_id)
    if repartidor is None:
        raise RepartidorNoEncontrado
    if repartidor["habilitado"]:
        raise YaEstaEnEseEstado

    repartidores.cambiar_habilitado(db, repartidor_id, True)
    db.commit()
    return Repartidor(**repartidores.buscar_por_id(db, repartidor_id))
