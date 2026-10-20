"""Importar todos los modelos acá hace que SQLAlchemy los conozca al crear las tablas."""

from repartos.models.operario import Operario
from repartos.models.pedido import CambioEstado, EstadoPedido, Pedido
from repartos.models.repartidor import Repartidor

__all__ = ["CambioEstado", "EstadoPedido", "Operario", "Pedido", "Repartidor"]
