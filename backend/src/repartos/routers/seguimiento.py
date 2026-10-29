"""Endpoints de la web del cliente final (todos empiezan con /seguimiento). No piden login."""

from fastapi import APIRouter, HTTPException, status

from repartos.db.session import SesionDB
from repartos.schemas.seguimiento import EstadoDelPedido
from repartos.services import seguimiento
from repartos.services.pedidos import PedidoNoEncontrado

router = APIRouter(prefix="/seguimiento", tags=["Cliente final"])


@router.get("/{codigo}")
def consultar_estado(codigo: str, db: SesionDB) -> EstadoDelPedido:
    """HU-21: el cliente final consulta su pedido con el código de seguimiento, sin iniciar sesión."""
    try:
        return seguimiento.consultar_estado(db, codigo)
    except PedidoNoEncontrado:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No encontramos un pedido con ese código. Revisalo e intentá de nuevo",
        )
