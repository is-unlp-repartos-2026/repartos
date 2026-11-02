"""Consultas SQL de los reportes: métricas de la operación (HU-25) y rendimiento de repartidores (HU-26).

Todas trabajan sobre "los pedidos del período": los registrados entre `desde` y `hasta` (días de Argentina).
Los tiempos se devuelven en minutos (None si no hay datos para calcularlos).
"""

from datetime import date

from sqlalchemy import RowMapping, text
from sqlalchemy.orm import Session

from repartos.models import EstadoPedido
from repartos.repositories.pedidos import SQL_REGISTRADO_EL

# CTE (WITH ...): una "tabla temporal con nombre" que vive solo durante la consulta. Se define una vez y
# las consultas de abajo la usan como si fuera una tabla más. Es texto fijo del código (sin datos del usuario).
_DEL_PERIODO = (
    "WITH del_periodo AS ("
    "  SELECT p.id, p.estado, p.repartidor_id, reg.registrado_el "
    "  FROM pedidos p "
    f"  JOIN ({SQL_REGISTRADO_EL}) reg ON reg.pedido_id = p.id "
    "  WHERE (reg.registrado_el AT TIME ZONE :zona)::date BETWEEN :desde AND :hasta"
    ") "
)


def _periodo(desde: date, hasta: date, zona_horaria: str) -> dict:
    return {"desde": desde, "hasta": hasta, "zona": zona_horaria}


def contar_por_estado(db: Session, desde: date, hasta: date, zona_horaria: str) -> dict[str, int]:
    """Cuántos pedidos del período hay en cada estado. Los estados sin pedidos no aparecen."""
    resultado = db.execute(
        text(_DEL_PERIODO + "SELECT estado, count(*) AS cantidad FROM del_periodo GROUP BY estado"),
        _periodo(desde, hasta, zona_horaria),
    )
    return {fila["estado"]: fila["cantidad"] for fila in resultado.mappings()}


def minutos_entre_registros(db: Session, desde: date, hasta: date, zona_horaria: str) -> float | None:
    """Lectura 1 de "tiempo promedio entre pedidos": cada cuánto entra un pedido nuevo.

    Con 5 pedidos hay 4 intervalos entre uno y el siguiente, y su promedio es (último − primero) / 4.
    NULLIF(x, 0) devuelve NULL si x es 0: con un solo pedido no hay intervalos (y no se divide por cero).
    EXTRACT(EPOCH FROM intervalo) pasa la diferencia entre dos fechas a segundos.
    """
    resultado = db.execute(
        text(
            _DEL_PERIODO + "SELECT EXTRACT(EPOCH FROM MAX(registrado_el) - MIN(registrado_el)) "
            "/ NULLIF(count(*) - 1, 0) / 60 FROM del_periodo"
        ),
        _periodo(desde, hasta, zona_horaria),
    )
    return _a_float(resultado.scalar_one())


def minutos_entre_entregas(db: Session, desde: date, hasta: date, zona_horaria: str) -> float | None:
    """Lectura 2 de "tiempo promedio entre pedidos": cuánto tarda un repartidor entre una entrega y la siguiente.

    LAG(...) OVER (PARTITION BY ... ORDER BY ...) es una "función de ventana": para cada entrega trae la
    fecha de la entrega ANTERIOR del mismo repartidor el mismo día (PARTITION BY separa por repartidor y por
    día: así no se cuenta la noche entre dos jornadas). La primera entrega de cada día no tiene anterior (NULL).
    """
    resultado = db.execute(
        text(
            _DEL_PERIODO + "SELECT AVG(EXTRACT(EPOCH FROM fecha_hora - anterior)) / 60 FROM ("
            "  SELECT c.fecha_hora, LAG(c.fecha_hora) OVER ("
            "    PARTITION BY c.repartidor_id, (c.fecha_hora AT TIME ZONE :zona)::date ORDER BY c.fecha_hora"
            "  ) AS anterior "
            "  FROM cambios_estado c JOIN del_periodo d ON d.id = c.pedido_id "
            "  WHERE c.estado = :entregado"
            ") entregas WHERE anterior IS NOT NULL"
        ),
        _periodo(desde, hasta, zona_horaria) | {"entregado": EstadoPedido.ENTREGADO},
    )
    return _a_float(resultado.scalar_one())


def minutos_promedio_de_entrega(db: Session, desde: date, hasta: date, zona_horaria: str) -> float | None:
    """Tiempo promedio de entrega: de "Registrado" a "Entregado", de los pedidos entregados del período."""
    resultado = db.execute(
        text(
            _DEL_PERIODO + "SELECT AVG(EXTRACT(EPOCH FROM c.fecha_hora - d.registrado_el)) / 60 "
            "FROM del_periodo d JOIN cambios_estado c ON c.pedido_id = d.id AND c.estado = :entregado"
        ),
        _periodo(desde, hasta, zona_horaria) | {"entregado": EstadoPedido.ENTREGADO},
    )
    return _a_float(resultado.scalar_one())


def rendimiento_por_repartidor(db: Session, desde: date, hasta: date, zona_horaria: str) -> list[RowMapping]:
    """HU-26: por cada repartidor, entregas realizadas y fallidas y el tiempo promedio de entrega.

    - El tiempo es desde que retira el pedido ("En camino") hasta que lo entrega: lo que depende de él.
    - LEFT JOIN: los repartidores sin entregas en el período también salen (con 0).
    - count(*) FILTER (WHERE ...): cuenta solo las filas que cumplen la condición (dos conteos en una pasada).
    - Subconsultas en el SELECT: para cada pedido buscan en su historial cuándo se retiró y cuándo se entregó.
    """
    resultado = db.execute(
        text(
            _DEL_PERIODO + ", terminados AS ("
            "  SELECT d.id, d.estado, d.repartidor_id, "
            "    (SELECT MAX(c.fecha_hora) FROM cambios_estado c "
            "     WHERE c.pedido_id = d.id AND c.estado = :en_camino) AS retirado_el, "
            "    (SELECT MAX(c.fecha_hora) FROM cambios_estado c "
            "     WHERE c.pedido_id = d.id AND c.estado = :entregado) AS entregado_el "
            "  FROM del_periodo d WHERE d.estado IN (:entregado, :fallida)"
            ") "
            "SELECT r.id, r.nombre, "
            "  count(*) FILTER (WHERE t.estado = :entregado) AS entregas_realizadas, "
            "  count(*) FILTER (WHERE t.estado = :fallida) AS entregas_fallidas, "
            "  AVG(EXTRACT(EPOCH FROM t.entregado_el - t.retirado_el)) / 60 AS minutos_promedio_entrega "
            "FROM repartidores r LEFT JOIN terminados t ON t.repartidor_id = r.id "
            "GROUP BY r.id, r.nombre "
            "ORDER BY entregas_realizadas DESC, r.nombre"
        ),
        _periodo(desde, hasta, zona_horaria)
        | {
            "en_camino": EstadoPedido.EN_CAMINO,
            "entregado": EstadoPedido.ENTREGADO,
            "fallida": EstadoPedido.ENTREGA_FALLIDA,
        },
    )
    return list(resultado.mappings())


def _a_float(valor: object) -> float | None:
    """PostgreSQL devuelve los promedios como Decimal: se pasan a float (o None si no hubo datos)."""
    return None if valor is None else float(valor)  # type: ignore[arg-type]
