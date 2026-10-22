"""Reglas del inicio de sesión (HU-01 Autenticar operario)."""

from sqlalchemy.orm import Session

from repartos.core.config import settings
from repartos.core.security import crear_token, verificar_contrasena
from repartos.repositories import operarios


class CredencialesInvalidas(Exception):
    """El usuario no existe o la contraseña no coincide."""


def iniciar_sesion_operario(db: Session, usuario: str, contrasena: str) -> str:
    """Si el usuario y la contraseña son correctos, devuelve un token de sesión del operario."""
    operario = operarios.buscar_por_usuario(db, usuario)

    # Mismo error para "no existe" y "contraseña incorrecta": así un atacante no puede averiguar
    # qué usuarios existen probando nombres.
    if operario is None or not verificar_contrasena(contrasena, operario["password_hash"]):
        raise CredencialesInvalidas

    return crear_token(operario["id"], rol="operario", minutos=settings.minutos_token_operario)
