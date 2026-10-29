"""Reglas del inicio de sesión (HU-01 Autenticar operario, HU-02 Autenticar repartidor)."""

from sqlalchemy.orm import Session

from repartos.core.config import settings
from repartos.core.security import crear_token, hashear_codigo_acceso, verificar_contrasena
from repartos.repositories import operarios, repartidores


class CredencialesInvalidas(Exception):
    """El usuario no existe o la contraseña no coincide."""


class CodigoAccesoInvalido(Exception):
    """Ningún repartidor tiene ese código de acceso."""


class RepartidorDeshabilitado(Exception):
    """El código es correcto, pero el operario deshabilitó al repartidor."""


def iniciar_sesion_operario(db: Session, usuario: str, contrasena: str) -> str:
    """Si el usuario y la contraseña son correctos, devuelve un token de sesión del operario."""
    operario = operarios.buscar_por_usuario(db, usuario)

    # Mismo error para "no existe" y "contraseña incorrecta": así un atacante no puede averiguar
    # qué usuarios existen probando nombres.
    if operario is None or not verificar_contrasena(contrasena, operario["password_hash"]):
        raise CredencialesInvalidas

    return crear_token(operario["id"], rol="operario", minutos=settings.minutos_token_operario)


def iniciar_sesion_repartidor(db: Session, codigo: str) -> str:
    """Si el código es de un repartidor habilitado, devuelve un token de sesión del repartidor.

    Ingresar NO lo activa: para recibir pedidos tiene que comenzar su jornada (HU-13).
    """
    # Se busca por el hash: en la base nunca está el código en claro (ver HU-09).
    repartidor = repartidores.buscar_por_codigo_acceso_hash(db, hashear_codigo_acceso(codigo.strip()))
    if repartidor is None:
        raise CodigoAccesoInvalido
    if not repartidor["habilitado"]:
        raise RepartidorDeshabilitado

    return crear_token(repartidor["id"], rol="repartidor", minutos=settings.minutos_token_repartidor)
