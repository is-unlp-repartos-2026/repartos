"""Schemas de los pedidos.

Por privacidad, el contenido del paquete NUNCA se pide ni se devuelve.
"""

import enum
from datetime import datetime

from pydantic import BaseModel, Field, model_validator

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


class MotivoFallo(enum.StrEnum):
    """Motivos de entrega fallida (supuesto del equipo, validar con Martín)."""

    DESTINATARIO_AUSENTE = "Destinatario ausente"
    DIRECCION_INCORRECTA = "Dirección incorrecta"
    PEDIDO_RECHAZADO = "Pedido rechazado"
    OTRO = "Otro"


class DatosEntregaFallida(BaseModel):
    """Lo que manda la app al registrar una entrega fallida. El motivo es obligatorio (HU-07)."""

    motivo: MotivoFallo  # solo acepta uno de los 4 valores; cualquier otro texto → 422
    aclaracion: str | None = Field(default=None, max_length=150)

    @model_validator(mode="after")
    def otro_necesita_aclaracion(self) -> "DatosEntregaFallida":
        """Si elige "Otro", tiene que escribir cuál fue el motivo."""
        if self.motivo == MotivoFallo.OTRO and not (self.aclaracion and self.aclaracion.strip()):
            raise ValueError('Con el motivo "Otro" hay que escribir una aclaración')
        return self

    def como_texto(self) -> str:
        """El motivo tal como se guarda: "Dirección incorrecta" o "Otro: se rompió la moto"."""
        if self.aclaracion and self.aclaracion.strip():
            return f"{self.motivo}: {self.aclaracion.strip()}"
        return str(self.motivo)


class PedidoAsignado(BaseModel):
    """Un pedido en la lista del repartidor (HU-16). Nunca el contenido del paquete."""

    id: int
    origen: str
    destino: str
    estado: EstadoPedido
    asignado_el: datetime


class DetallePedidoAsignado(BaseModel):
    """Lo que el repartidor necesita para hacer la entrega (HU-17). Nunca el contenido del paquete."""

    id: int
    origen: str
    destino: str
    receptor_nombre: str
    receptor_dni: str
    peso_kg: float
    alto_cm: float
    ancho_cm: float
    largo_cm: float
    estado: EstadoPedido


class CambioDeEstadoOperario(BaseModel):
    """Un cambio del historial, con todo el detalle (el operario ve quién y por qué)."""

    estado: EstadoPedido
    fecha_hora: datetime
    repartidor: RepartidorDelPedido | None
    detalle: str | None


class DetallePedidoOperario(BaseModel):
    """El detalle completo de un pedido para el operario (HU-23)."""

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
    repartidor: RepartidorDelPedido | None
    historial: list[CambioDeEstadoOperario]
    # Solo si está entregado: la dirección para ver la foto (GET /operario/pedidos/{id}/foto).
    foto_url: str | None
    # Solo si la entrega falló.
    motivo_fallo: str | None


class PedidoEnTablero(BaseModel):
    """Un pedido en el tablero del operario (HU-22)."""

    id: int
    codigo_seguimiento: str
    origen: str
    destino: str
    repartidor: RepartidorDelPedido | None
    desde: datetime  # cuándo pasó a su estado actual


class Tablero(BaseModel):
    """Los pedidos en curso agrupados por estado. Los finales (entregado, fallido, cancelado) no van.

    "registrado" son los que no tienen repartidor: el frontend los destaca.
    """

    registrado: list[PedidoEnTablero]
    repartidor_asignado: list[PedidoEnTablero]
    en_camino: list[PedidoEnTablero]
