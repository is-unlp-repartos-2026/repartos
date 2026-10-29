"""Endpoints de la interfaz del operario (todos empiezan con /operario)."""

from fastapi import APIRouter, HTTPException, status

from repartos.core.security import OperarioActual
from repartos.db.session import SesionDB
from repartos.repositories import operarios
from repartos.schemas.auth import CredencialesOperario, OperarioLogueado, SesionIniciada
from repartos.schemas.pedidos import DatosNuevoPedido, PedidoRegistrado
from repartos.schemas.repartidores import DatosNuevoRepartidor, RepartidorRegistrado
from repartos.services import auth, pedidos, repartidores

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


@router.post("/repartidores", status_code=status.HTTP_201_CREATED)
def registrar_repartidor(
    datos: DatosNuevoRepartidor, operario_id: OperarioActual, db: SesionDB
) -> RepartidorRegistrado:
    """HU-09: el operario da de alta un repartidor y recibe su código de acceso."""
    try:
        return repartidores.registrar_repartidor(db, datos)
    except repartidores.DniRepetido:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Ya existe un repartidor con ese DNI")
    except repartidores.CorreoRepetido:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Ya existe un repartidor con ese correo")


@router.post("/pedidos", status_code=status.HTTP_201_CREATED)
def registrar_pedido(datos: DatosNuevoPedido, operario_id: OperarioActual, db: SesionDB) -> PedidoRegistrado:
    """HU-04: el operario registra un pedido; se le asigna un repartidor apto si hay uno."""
    return pedidos.registrar_pedido(db, datos)
