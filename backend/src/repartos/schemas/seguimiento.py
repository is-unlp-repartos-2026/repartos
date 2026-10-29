"""Schemas del seguimiento del cliente final (sin login).

Lo que ve cualquiera que tenga el código: por eso se muestra lo mínimo. Ni el DNI ni el nombre de quien
recibe, ni el repartidor, ni los detalles internos del historial (motivos de reasignación, etc.).
"""

from datetime import datetime

from pydantic import BaseModel

from repartos.models import EstadoPedido


class CambioDeEstado(BaseModel):
    estado: EstadoPedido
    fecha_hora: datetime


class EstadoDelPedido(BaseModel):
    codigo_seguimiento: str
    estado: EstadoPedido
    historial: list[CambioDeEstado]
