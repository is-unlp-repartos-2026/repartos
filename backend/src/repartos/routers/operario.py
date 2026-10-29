"""Endpoints de la interfaz del operario (todos empiezan con /operario)."""

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import FileResponse

from repartos.core.security import OperarioActual
from repartos.db.session import SesionDB
from repartos.repositories import operarios
from repartos.schemas.auth import CredencialesOperario, OperarioLogueado, SesionIniciada
from repartos.schemas.pedidos import DatosNuevoPedido, DetallePedidoOperario, EstadoActualizado, PedidoRegistrado
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


@router.post("/pedidos/{pedido_id}/cancelar")
def cancelar_pedido(pedido_id: int, operario_id: OperarioActual, db: SesionDB) -> EstadoActualizado:
    """HU-06: el operario cancela un pedido que todavía no fue retirado."""
    try:
        return pedidos.cancelar_pedido(db, pedido_id)
    except pedidos.PedidoNoEncontrado:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pedido no encontrado")
    except pedidos.EstadoNoPermitido:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Solo se puede cancelar un pedido registrado o con repartidor asignado",
        )


@router.get("/pedidos/{pedido_id}")
def detalle_pedido(pedido_id: int, operario_id: OperarioActual, db: SesionDB) -> DetallePedidoOperario:
    """HU-23: el detalle completo de un pedido (desde el tablero o el historial)."""
    try:
        return pedidos.detalle_pedido(db, pedido_id)
    except pedidos.PedidoNoEncontrado:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pedido no encontrado")


@router.get("/pedidos/{pedido_id}/foto", response_class=FileResponse)
def foto_entrega(pedido_id: int, operario_id: OperarioActual, db: SesionDB) -> FileResponse:
    """HU-23: la foto de la entrega de un pedido entregado. Solo el operario la puede ver."""
    try:
        return FileResponse(pedidos.ruta_foto(db, pedido_id))
    except pedidos.PedidoNoEncontrado:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="El pedido no tiene foto de entrega")
