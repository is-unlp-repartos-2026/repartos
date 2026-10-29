"""Schemas de los repartidores."""

from pydantic import BaseModel, EmailStr, Field


class DatosNuevoRepartidor(BaseModel):
    """Lo que manda el operario para dar de alta un repartidor (body del POST /operario/repartidores).

    Las restricciones de Field las valida FastAPI antes de llegar al service: si no se cumplen,
    responde 422 con el detalle del campo que falló.
    """

    nombre: str = Field(min_length=1, max_length=100)
    dni: str = Field(pattern=r"^\d{7,8}$")  # solo números, sin puntos
    correo: EmailStr  # valida que tenga forma de correo (algo@dominio.com)

    # Habilitación: la carga máxima que puede transportar. gt=0: mayor que cero.
    peso_max_kg: float = Field(gt=0)
    alto_max_cm: float = Field(gt=0)
    ancho_max_cm: float = Field(gt=0)
    largo_max_cm: float = Field(gt=0)


class Habilitacion(BaseModel):
    """La carga máxima que puede transportar un repartidor (body del PUT .../habilitacion, HU-11)."""

    peso_max_kg: float = Field(gt=0)
    alto_max_cm: float = Field(gt=0)
    ancho_max_cm: float = Field(gt=0)
    largo_max_cm: float = Field(gt=0)


class Repartidor(BaseModel):
    """Los datos de un repartidor tal como los ve el operario."""

    id: int
    nombre: str
    dni: str
    correo: str
    peso_max_kg: float
    alto_max_cm: float
    ancho_max_cm: float
    largo_max_cm: float
    habilitado: bool
    activo: bool


class RepartidorRegistrado(Repartidor):
    """Respuesta del alta: los datos más el código de acceso.

    Es la ÚNICA vez que el código se ve en claro: en la base queda solo su hash.
    """

    codigo_acceso: str


class RepartidorDeshabilitado(BaseModel):
    """Respuesta de deshabilitar: el repartidor y qué pasó con los pedidos que tenía asignados."""

    repartidor: Repartidor
    pedidos_reasignados: int  # pasaron a otro repartidor apto
    pedidos_sin_repartidor: int  # no había otro apto: volvieron a "registrado"
