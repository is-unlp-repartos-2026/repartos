"""Schemas de la jornada laboral del repartidor."""

from pydantic import BaseModel


class JornadaComenzada(BaseModel):
    """Respuesta de "Comenzar jornada": queda activo y cuántos pedidos pendientes se le asignaron."""

    activo: bool
    pedidos_asignados: int
