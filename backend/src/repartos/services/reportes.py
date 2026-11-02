"""Reglas de los reportes (HU-25 Consultar métricas de la operación, HU-26 Consultar rendimiento de repartidores)."""

from datetime import date

from sqlalchemy.orm import Session

from repartos.core import fechas
from repartos.core.config import settings
from repartos.models import EstadoPedido
from repartos.repositories import reportes
from repartos.schemas.reportes import Metricas, RendimientoRepartidor
from repartos.services.pedidos import PeriodoInvalido


def _periodo(desde: date | None, hasta: date | None) -> tuple[date, date]:
    """Por defecto, el mes en curso: del día 1 hasta hoy."""
    hasta = hasta or fechas.hoy()
    desde = desde or hasta.replace(day=1)
    if desde > hasta:
        raise PeriodoInvalido
    return desde, hasta


def metricas(db: Session, desde: date | None = None, hasta: date | None = None) -> Metricas:
    """HU-25: pedidos por estado, tiempo promedio entre pedidos (dos lecturas), tiempo promedio de entrega
    y % de entregas fallidas, de los pedidos registrados en el período."""
    desde, hasta = _periodo(desde, hasta)
    zona = settings.zona_horaria

    por_estado = reportes.contar_por_estado(db, desde, hasta, zona)
    por_estado = {estado: por_estado.get(estado, 0) for estado in EstadoPedido}  # los 6, con 0 si no hay
    terminados = por_estado[EstadoPedido.ENTREGADO] + por_estado[EstadoPedido.ENTREGA_FALLIDA]

    return Metricas(
        desde=desde,
        hasta=hasta,
        total_pedidos=sum(por_estado.values()),
        pedidos_por_estado=por_estado,
        minutos_entre_pedidos=reportes.minutos_entre_registros(db, desde, hasta, zona),
        minutos_entre_entregas=reportes.minutos_entre_entregas(db, desde, hasta, zona),
        minutos_promedio_entrega=reportes.minutos_promedio_de_entrega(db, desde, hasta, zona),
        porcentaje_entregas_fallidas=(
            por_estado[EstadoPedido.ENTREGA_FALLIDA] * 100 / terminados if terminados else None
        ),
    )


def rendimiento(db: Session, desde: date | None = None, hasta: date | None = None) -> list[RendimientoRepartidor]:
    """HU-26: entregas realizadas, fallidas y tiempo promedio de cada repartidor en el período.
    Viene ordenado por entregas realizadas (el frontend permite ordenar por las otras columnas)."""
    desde, hasta = _periodo(desde, hasta)
    return [
        RendimientoRepartidor(**fila)
        for fila in reportes.rendimiento_por_repartidor(db, desde, hasta, settings.zona_horaria)
    ]
