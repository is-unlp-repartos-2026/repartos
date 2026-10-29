"""Reglas de los repartidores (HU-09 Registrar repartidor)."""

from sqlalchemy.orm import Session

from repartos.core.security import generar_codigo_acceso, hashear_codigo_acceso
from repartos.repositories import repartidores
from repartos.schemas.repartidores import DatosNuevoRepartidor, RepartidorRegistrado


class DniRepetido(Exception):
    """Ya hay un repartidor con ese DNI."""


class CorreoRepetido(Exception):
    """Ya hay un repartidor con ese correo."""


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
