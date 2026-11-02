"""Endpoints de la interfaz del operario (todos empiezan con /operario)."""

from datetime import date

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import FileResponse

from repartos.core.security import OperarioActual
from repartos.db.session import SesionDB
from repartos.models import EstadoPedido
from repartos.repositories import operarios
from repartos.schemas.auth import CredencialesOperario, OperarioLogueado, SesionIniciada
from repartos.schemas.pedidos import (
    DatosNuevoPedido,
    DatosReasignacion,
    DetallePedidoOperario,
    EstadoActualizado,
    PedidoEnHistorial,
    PedidoRegistrado,
    ResultadoModificacion,
    ResultadoReasignacion,
    Tablero,
)
from repartos.schemas.repartidores import (
    DatosNuevoRepartidor,
    Habilitacion,
    Repartidor,
    RepartidorDeshabilitado,
    RepartidorRegistrado,
)
from repartos.schemas.reportes import Metricas, RendimientoRepartidor
from repartos.services import auth, pedidos, repartidores, reportes

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


@router.get("/repartidores")
def listar_repartidores(
    operario_id: OperarioActual, db: SesionDB, habilitado: bool | None = None
) -> list[Repartidor]:
    """HU-10: lista los repartidores. ?habilitado=false muestra solo los deshabilitados (y true, los habilitados)."""
    return repartidores.listar_repartidores(db, habilitado)


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


@router.get("/tablero")
def tablero(operario_id: OperarioActual, db: SesionDB) -> Tablero:
    """HU-22: los pedidos en curso agrupados por estado.

    "Se actualiza solo, sin recargar": el frontend llama a este endpoint cada pocos segundos (polling)
    y redibuja el tablero. Así, cuando un repartidor retira un pedido, el operario lo ve pasar a "en camino".
    """
    return pedidos.tablero(db)


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


@router.post("/pedidos/{pedido_id}/reasignar")
def reasignar_pedido(
    pedido_id: int, datos: DatosReasignacion, operario_id: OperarioActual, db: SesionDB
) -> ResultadoReasignacion:
    """HU-08: el operario le saca el pedido a su repartidor y se lo asigna a otro apto."""
    try:
        return pedidos.reasignar_pedido(db, pedido_id, datos)
    except pedidos.PedidoNoEncontrado:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pedido no encontrado")
    except pedidos.EstadoNoPermitido:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Solo se puede reasignar un pedido con repartidor asignado (todavía no retirado)",
        )


@router.post("/repartidores/{repartidor_id}/deshabilitar")
def deshabilitar_repartidor(repartidor_id: int, operario_id: OperarioActual, db: SesionDB) -> RepartidorDeshabilitado:
    """HU-12: deshabilita al repartidor y reasigna sus pedidos sin retirar."""
    try:
        return repartidores.deshabilitar(db, repartidor_id)
    except repartidores.RepartidorNoEncontrado:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Repartidor no encontrado")
    except repartidores.YaEstaEnEseEstado:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="El repartidor ya está deshabilitado")
    except repartidores.TienePedidosEnCamino:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="El repartidor tiene pedidos en camino: no se puede deshabilitar hasta que termine esas entregas",
        )


@router.post("/repartidores/{repartidor_id}/habilitar")
def habilitar_repartidor(repartidor_id: int, operario_id: OperarioActual, db: SesionDB) -> Repartidor:
    """HU-12: vuelve a habilitar al repartidor; recupera el acceso a la app."""
    try:
        return repartidores.habilitar(db, repartidor_id)
    except repartidores.RepartidorNoEncontrado:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Repartidor no encontrado")
    except repartidores.YaEstaEnEseEstado:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="El repartidor ya está habilitado")


@router.put("/repartidores/{repartidor_id}/habilitacion")
def modificar_habilitacion(
    repartidor_id: int, datos: Habilitacion, operario_id: OperarioActual, db: SesionDB
) -> Repartidor:
    """HU-11: cambia el peso y las medidas máximas que puede llevar el repartidor."""
    try:
        return repartidores.modificar_habilitacion(db, repartidor_id, datos)
    except repartidores.RepartidorNoEncontrado:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Repartidor no encontrado")
    except repartidores.TienePedidosEnCurso:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="El repartidor tiene pedidos en curso: no se puede cambiar su habilitación hasta que los termine",
        )


PERIODO_INVALIDO = "La fecha \"desde\" no puede ser posterior a la fecha \"hasta\""


@router.get("/pedidos")
def historial_pedidos(
    operario_id: OperarioActual,
    db: SesionDB,
    desde: date | None = None,
    hasta: date | None = None,
    estado: EstadoPedido | None = None,
    repartidor_id: int | None = None,
) -> list[PedidoEnHistorial]:
    """HU-24: el historial de pedidos. Sin filtros, los registrados hoy. Fechas en formato AAAA-MM-DD."""
    try:
        return pedidos.historial(db, desde, hasta, estado, repartidor_id)
    except pedidos.PeriodoInvalido:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=PERIODO_INVALIDO)


@router.put("/pedidos/{pedido_id}")
def modificar_pedido(
    pedido_id: int, datos: DatosNuevoPedido, operario_id: OperarioActual, db: SesionDB
) -> ResultadoModificacion:
    """HU-05: corrige los datos de un pedido todavía no retirado; si cambian peso o medidas, reevalúa la asignación."""
    try:
        return pedidos.modificar_pedido(db, pedido_id, datos)
    except pedidos.PedidoNoEncontrado:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pedido no encontrado")
    except pedidos.EstadoNoPermitido:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Solo se puede modificar un pedido registrado o con repartidor asignado",
        )


@router.get("/metricas")
def metricas(
    operario_id: OperarioActual, db: SesionDB, desde: date | None = None, hasta: date | None = None
) -> Metricas:
    """HU-25: métricas de los pedidos registrados en el período (por defecto, el mes en curso)."""
    try:
        return reportes.metricas(db, desde, hasta)
    except pedidos.PeriodoInvalido:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=PERIODO_INVALIDO)


@router.get("/rendimiento")
def rendimiento(
    operario_id: OperarioActual, db: SesionDB, desde: date | None = None, hasta: date | None = None
) -> list[RendimientoRepartidor]:
    """HU-26: entregas y tiempo promedio de cada repartidor en el período (por defecto, el mes en curso)."""
    try:
        return reportes.rendimiento(db, desde, hasta)
    except pedidos.PeriodoInvalido:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=PERIODO_INVALIDO)
