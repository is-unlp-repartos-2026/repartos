"""Endpoints de la app del repartidor (todos empiezan con /repartidor)."""

from fastapi import APIRouter, HTTPException, status

from repartos.core.security import REPARTIDOR_DESHABILITADO, RepartidorActual
from repartos.db.session import SesionDB
from repartos.repositories import repartidores
from repartos.schemas.auth import CodigoAccesoRepartidor, SesionIniciada
from repartos.schemas.repartidores import Repartidor
from repartos.services import auth

router = APIRouter(prefix="/repartidor", tags=["Repartidor"])


@router.post("/login")
def iniciar_sesion(datos: CodigoAccesoRepartidor, db: SesionDB) -> SesionIniciada:
    """HU-02: el repartidor inicia sesión solo con su código de acceso."""
    try:
        token = auth.iniciar_sesion_repartidor(db, datos.codigo)
    except auth.CodigoAccesoInvalido:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Código de acceso incorrecto")
    except auth.RepartidorDeshabilitado:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=REPARTIDOR_DESHABILITADO)
    return SesionIniciada(token=token)


@router.get("/sesion")
def consultar_sesion(repartidor_id: RepartidorActual, db: SesionDB) -> Repartidor:
    """Devuelve los datos del repartidor de la sesión actual.

    La app lo llama al abrirse: si responde 200, sigue logueado; si responde 401/403, vuelve al ingreso.
    """
    return Repartidor(**repartidores.buscar_por_id(db, repartidor_id))
