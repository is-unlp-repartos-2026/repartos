"""Schemas de los pedidos.

Por privacidad, el contenido del paquete NUNCA se pide ni se devuelve.
"""

from pydantic import BaseModel, Field

from repartos.models import EstadoPedido


class DatosNuevoPedido(BaseModel):
    """Lo que manda el operario para registrar un pedido (body del POST /operario/pedidos)."""

    origen: str = Field(min_length=1, max_length=200)
    destino: str = Field(min_length=1, max_length=200)
    receptor_nombre: str = Field(min_length=1, max_length=100)
    receptor_dni: str = Field(pattern=r"^\d{7,8}$")  # solo números, sin puntos
    peso_kg: float = Field(gt=0)
    alto_cm: float = Field(gt=0)
    ancho_cm: float = Field(gt=0)
    largo_cm: float = Field(gt=0)


class RepartidorDelPedido(BaseModel):
    id: int
    nombre: str


class PedidoRegistrado(BaseModel):
    """Respuesta del registro: el pedido con su código de seguimiento y a quién se asignó."""

    id: int
    codigo_seguimiento: str
    origen: str
    destino: str
    receptor_nombre: str
    receptor_dni: str
    peso_kg: float
    alto_cm: float
    ancho_cm: float
    largo_cm: float
    estado: EstadoPedido
    repartidor: RepartidorDelPedido | None  # None: no había ningún repartidor apto
    aviso: str | None = None  # mensaje para el operario cuando el pedido queda sin asignar


class EstadoActualizado(BaseModel):
    """Respuesta de un cambio de estado: el pedido y el estado en que quedó."""

    id: int
    estado: EstadoPedido
