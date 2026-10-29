"""Schemas de la jornada laboral del repartidor."""

from pydantic import BaseModel


class JornadaComenzada(BaseModel):
    """Respuesta de "Comenzar jornada": queda activo y cuántos pedidos pendientes se le asignaron."""

    activo: bool
    pedidos_asignados: int


class JornadaTerminada(BaseModel):
    """Respuesta de "Terminar jornada": queda inactivo y qué pasó con los pedidos que tenía asignados."""

    activo: bool
    pedidos_reasignados: int  # pasaron a otro repartidor apto
    pedidos_sin_repartidor: int  # no había otro apto: volvieron a "registrado"
