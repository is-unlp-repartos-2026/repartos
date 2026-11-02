"""Schemas de los reportes (HU-25 Métricas de la operación, HU-26 Rendimiento de repartidores).

Los tiempos van en minutos; None cuando no hay datos para calcularlos (por ejemplo, ninguna entrega).
"""

from datetime import date

from pydantic import BaseModel

from repartos.models import EstadoPedido


class Metricas(BaseModel):
    desde: date
    hasta: date
    total_pedidos: int
    pedidos_por_estado: dict[EstadoPedido, int]  # siempre trae los 6 estados (con 0 si no hay)
    # "Tiempo promedio entre pedidos" es ambiguo: se muestran las dos lecturas.
    minutos_entre_pedidos: float | None  # cada cuánto entra un pedido nuevo
    minutos_entre_entregas: float | None  # cuánto tarda un repartidor entre una entrega y la siguiente
    minutos_promedio_entrega: float | None  # de "Registrado" a "Entregado"
    porcentaje_entregas_fallidas: float | None  # fallidas / (entregadas + fallidas) × 100


class RendimientoRepartidor(BaseModel):
    id: int
    nombre: str
    entregas_realizadas: int
    entregas_fallidas: int
    minutos_promedio_entrega: float | None  # desde que retira el pedido hasta que lo entrega
