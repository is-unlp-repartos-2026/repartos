"""Endpoints de la app del repartidor (todos empiezan con /repartidor)."""

from fastapi import APIRouter, HTTPException, status

from repartos.core.security import REPARTIDOR_DESHABILITADO, RepartidorActual
from repartos.db.session import SesionDB
from repartos.repositories import repartidores
from repartos.schemas.auth import CodigoAccesoRepartidor, SesionIniciada
from repartos.schemas.jornada import JornadaComenzada, JornadaTerminada
from repartos.schemas.pedidos import DatosEntregaFallida, EstadoActualizado
from repartos.schemas.repartidores import Repartidor
from repartos.services import auth, entregas, jornada

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


@router.post("/jornada/comenzar")
def comenzar_jornada(repartidor_id: RepartidorActual, db: SesionDB) -> JornadaComenzada:
    """HU-13: el repartidor comienza su jornada; queda activo y recibe los pedidos pendientes que puede llevar."""
    try:
        return jornada.comenzar_jornada(db, repartidor_id)
    except jornada.JornadaYaComenzada:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Ya comenzaste tu jornada")


@router.post("/jornada/terminar")
def terminar_jornada(repartidor_id: RepartidorActual, db: SesionDB) -> JornadaTerminada:
    """HU-14: el repartidor termina su jornada; queda inactivo y sus pedidos sin retirar se reasignan."""
    try:
        return jornada.terminar_jornada(db, repartidor_id)
    except jornada.JornadaNoComenzada:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="No comenzaste tu jornada")
    except jornada.TienePedidosEnCamino:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Tenés pedidos en camino: terminá tus entregas antes de terminar la jornada",
        )


@router.post("/pedidos/{pedido_id}/retirar")
def retirar_pedido(pedido_id: int, repartidor_id: RepartidorActual, db: SesionDB) -> EstadoActualizado:
    """HU-18: el repartidor retira un pedido asignado; pasa a "en camino"."""
    try:
        return entregas.retirar_pedido(db, pedido_id, repartidor_id)
    except entregas.PedidoNoEncontrado:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pedido no encontrado")
    except entregas.EstadoNoPermitido:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Solo se puede retirar un pedido con repartidor asignado"
        )


@router.post("/pedidos/{pedido_id}/entrega-fallida")
def registrar_entrega_fallida(
    pedido_id: int, datos: DatosEntregaFallida, repartidor_id: RepartidorActual, db: SesionDB
) -> EstadoActualizado:
    """HU-07: el repartidor no pudo entregar un pedido en camino; queda "entrega fallida" con el motivo."""
    try:
        return entregas.registrar_entrega_fallida(db, pedido_id, repartidor_id, datos)
    except entregas.PedidoNoEncontrado:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pedido no encontrado")
    except entregas.EstadoNoPermitido:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Solo se puede registrar una entrega fallida de un pedido en camino",
        )
