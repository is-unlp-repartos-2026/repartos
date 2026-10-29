"""Endpoints de la app del repartidor (todos empiezan con /repartidor)."""

from typing import Annotated

from fastapi import APIRouter, File, Form, HTTPException, UploadFile, status

from repartos.core.config import settings
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


@router.post("/pedidos/{pedido_id}/confirmar-entrega")
def confirmar_entrega(
    pedido_id: int,
    # multipart/form-data (como un formulario con un archivo adjunto): no es JSON porque lleva una foto.
    foto: Annotated[UploadFile, File(description="Foto de la entrega, sacada con la cámara de la app")],
    dni: Annotated[str, Form(pattern=r"^\d{7,8}$", description="DNI de quien recibe, sin puntos")],
    repartidor_id: RepartidorActual,
    db: SesionDB,
) -> EstadoActualizado:
    """HU-20: el repartidor confirma la entrega con foto y el DNI de quien recibe; pasa a "entregado"."""
    # Se lee como mucho 1 byte más que el máximo: alcanza para saber si se pasa, sin cargar un archivo gigante.
    contenido = foto.file.read(settings.tamano_max_foto_mb * 1024 * 1024 + 1)
    try:
        return entregas.confirmar_entrega(db, pedido_id, repartidor_id, contenido, dni)
    except entregas.PedidoNoEncontrado:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pedido no encontrado")
    except entregas.EstadoNoPermitido:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Solo se puede confirmar la entrega de un pedido en camino"
        )
    except entregas.DniNoCoincide:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="El DNI no coincide con el de quien tiene que recibir el pedido"
        )
    except entregas.FotoInvalida:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=f"La foto tiene que ser una imagen JPG, PNG o WEBP de hasta {settings.tamano_max_foto_mb} MB",
        )
