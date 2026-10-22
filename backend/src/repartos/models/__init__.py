"""Definición de las tablas de la base de datos.

Los modelos se usan SOLO para describir la estructura de las tablas: a partir de ellos Alembic genera las
migraciones. Las consultas (SELECT, INSERT, UPDATE, DELETE) NO se hacen con estos modelos: se escriben en
SQL dentro de repositories/.

Importar todos los modelos acá hace que Alembic los conozca.
"""

from repartos.models.operario import Operario
from repartos.models.pedido import CambioEstado, EstadoPedido, Pedido
from repartos.models.repartidor import Repartidor

__all__ = ["CambioEstado", "EstadoPedido", "Operario", "Pedido", "Repartidor"]
