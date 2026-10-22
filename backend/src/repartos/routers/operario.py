"""Endpoints de la interfaz del operario (todos empiezan con /operario)."""

from fastapi import APIRouter, HTTPException, status

from repartos.core.security import OperarioActual
from repartos.db.session import SesionDB
from repartos.repositories import operarios
from repartos.schemas.auth import CredencialesOperario, OperarioLogueado, SesionIniciada
from repartos.services import auth

router = APIRouter(prefix="/operario", tags=["Operario"])


@router.post("/login")
def iniciar_sesion(datos: CredencialesOperario, db: SesionDB) -> SesionIniciada:
    """HU-01: el operario inicia sesión con usuario y contraseña."""
    try:
        token = auth.iniciar_sesion_operario(db, datos.usuario, datos.contrasena)
    except auth.CredencialesInvalidas:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Usuario o contraseña incorrectos")
    return SesionIniciada(token=token)


@router.get("/sesion")
def consultar_sesion(operario_id: OperarioActual, db: SesionDB) -> OperarioLogueado:
    """Devuelve quién es el operario de la sesión actual. Sirve para que el frontend sepa si el token sigue válido."""
    operario = operarios.buscar_por_id(db, operario_id)
    if operario is None:  # el token es válido, pero el operario ya no existe
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Sesión inválida")
    return OperarioLogueado(id=operario["id"], usuario=operario["usuario"])
