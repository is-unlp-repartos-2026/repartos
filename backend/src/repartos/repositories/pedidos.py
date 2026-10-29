"""Consultas SQL de la tabla pedidos."""

from sqlalchemy import RowMapping, text
from sqlalchemy.orm import Session

from repartos.models import EstadoPedido

# Columnas que se devuelven al leer un pedido.
_COLUMNAS = (
    "id, codigo_seguimiento, origen, destino, receptor_nombre, receptor_dni, "
    "peso_kg, alto_cm, ancho_cm, largo_cm, estado, repartidor_id"
)


def existe_codigo_seguimiento(db: Session, codigo: str) -> bool:
    resultado = db.execute(
        text("SELECT EXISTS (SELECT 1 FROM pedidos WHERE codigo_seguimiento = :codigo)"),
        {"codigo": codigo},
    )
    return resultado.scalar_one()


def insertar(
    db: Session,
    codigo_seguimiento: str,
    origen: str,
    destino: str,
    receptor_nombre: str,
    receptor_dni: str,
    peso_kg: float,
    alto_cm: float,
    ancho_cm: float,
    largo_cm: float,
) -> RowMapping:
    """Inserta un pedido y devuelve la fila creada. El estado no se manda: la base pone "registrado"."""
    resultado = db.execute(
        text(
            "INSERT INTO pedidos "
            "(codigo_seguimiento, origen, destino, receptor_nombre, receptor_dni, "
            "peso_kg, alto_cm, ancho_cm, largo_cm) "
            "VALUES (:codigo_seguimiento, :origen, :destino, :receptor_nombre, :receptor_dni, "
            ":peso_kg, :alto_cm, :ancho_cm, :largo_cm) "
            f"RETURNING {_COLUMNAS}"  # _COLUMNAS es texto fijo del código, nunca un dato del usuario
        ),
        {
            "codigo_seguimiento": codigo_seguimiento,
            "origen": origen,
            "destino": destino,
            "receptor_nombre": receptor_nombre,
            "receptor_dni": receptor_dni,
            "peso_kg": peso_kg,
            "alto_cm": alto_cm,
            "ancho_cm": ancho_cm,
            "largo_cm": largo_cm,
        },
    )
    return resultado.mappings().one()


def asignar_repartidor(db: Session, pedido_id: int, repartidor_id: int) -> None:
    """Pasa el pedido a "repartidor asignado" con ese repartidor."""
    db.execute(
        text("UPDATE pedidos SET estado = :estado, repartidor_id = :repartidor_id WHERE id = :id"),
        {"estado": EstadoPedido.REPARTIDOR_ASIGNADO, "repartidor_id": repartidor_id, "id": pedido_id},
    )


def buscar_registrados_que_puede_llevar_y_bloquear(
    db: Session, peso_max_kg: float, alto_max_cm: float, ancho_max_cm: float, largo_max_cm: float
) -> list[RowMapping]:
    """Pedidos "registrado" sin repartidor que entran en esa capacidad, del más viejo al más nuevo (HU-13).

    FOR UPDATE: si dos repartidores comienzan su jornada al mismo tiempo, el segundo espera a que el
    primero termine; para entonces esos pedidos ya no están "registrado" y no se asignan dos veces.
    """
    resultado = db.execute(
        text(
            f"SELECT {_COLUMNAS} FROM pedidos "
            "WHERE estado = :estado AND repartidor_id IS NULL "
            "AND peso_kg <= :peso AND alto_cm <= :alto AND ancho_cm <= :ancho AND largo_cm <= :largo "
            "ORDER BY id "
            "FOR UPDATE"
        ),
        {
            "estado": EstadoPedido.REGISTRADO,
            "peso": peso_max_kg,
            "alto": alto_max_cm,
            "ancho": ancho_max_cm,
            "largo": largo_max_cm,
        },
    )
    return list(resultado.mappings())


def contar_en_camino_de(db: Session, repartidor_id: int) -> int:
    """Cuántos pedidos tiene "en camino" ese repartidor (los que ya retiró y todavía no entregó)."""
    resultado = db.execute(
        text("SELECT count(*) FROM pedidos WHERE repartidor_id = :repartidor_id AND estado = :estado"),
        {"repartidor_id": repartidor_id, "estado": EstadoPedido.EN_CAMINO},
    )
    return resultado.scalar_one()


def buscar_asignados_a_y_bloquear(db: Session, repartidor_id: int) -> list[RowMapping]:
    """Pedidos "repartidor asignado" de ese repartidor (todavía no los retiró), del más viejo al más nuevo."""
    resultado = db.execute(
        text(
            f"SELECT {_COLUMNAS} FROM pedidos "
            "WHERE repartidor_id = :repartidor_id AND estado = :estado "
            "ORDER BY id "
            "FOR UPDATE"
        ),
        {"repartidor_id": repartidor_id, "estado": EstadoPedido.REPARTIDOR_ASIGNADO},
    )
    return list(resultado.mappings())


def volver_a_registrado(db: Session, pedido_id: int) -> None:
    """El pedido queda "registrado" y sin repartidor (cuando se lo sacan a uno y no hay otro apto)."""
    db.execute(
        text("UPDATE pedidos SET estado = :estado, repartidor_id = NULL WHERE id = :id"),
        {"estado": EstadoPedido.REGISTRADO, "id": pedido_id},
    )


def buscar_por_id_y_bloquear(db: Session, pedido_id: int) -> RowMapping | None:
    """Trae el pedido y bloquea su fila hasta el commit (FOR UPDATE).

    Se usa antes de cambiarle el estado: si dos acciones llegan a la vez (por ejemplo, el operario cancela
    justo cuando el repartidor lo retira), la segunda espera y después ve el estado nuevo, en lugar de
    pisarlo.
    """
    resultado = db.execute(
        text(f"SELECT {_COLUMNAS} FROM pedidos WHERE id = :id FOR UPDATE"),
        {"id": pedido_id},
    )
    return resultado.mappings().first()


def cambiar_estado(db: Session, pedido_id: int, estado: EstadoPedido) -> None:
    db.execute(
        text("UPDATE pedidos SET estado = :estado WHERE id = :id"),
        {"estado": estado, "id": pedido_id},
    )


def registrar_entrega_fallida(db: Session, pedido_id: int, motivo: str) -> None:
    db.execute(
        text("UPDATE pedidos SET estado = :estado, motivo_fallo = :motivo WHERE id = :id"),
        {"estado": EstadoPedido.ENTREGA_FALLIDA, "motivo": motivo, "id": pedido_id},
    )


def registrar_entrega(db: Session, pedido_id: int, foto: str) -> None:
    db.execute(
        text("UPDATE pedidos SET estado = :estado, foto_entrega = :foto WHERE id = :id"),
        {"estado": EstadoPedido.ENTREGADO, "foto": foto, "id": pedido_id},
    )


def listar_en_curso_de(db: Session, repartidor_id: int) -> list[RowMapping]:
    """Pedidos que el repartidor tiene que hacer: asignados (sin retirar) y en camino (HU-16).

    Se ordenan por fecha de asignación (supuesto del equipo). Esa fecha no está en la tabla pedidos:
    sale del historial, de la última vez que el pedido pasó a "repartidor asignado" con ESTE repartidor
    (un pedido reasignado pudo haber sido de otro antes). Por eso el JOIN + MAX + GROUP BY.
    """
    resultado = db.execute(
        text(
            "SELECT p.id, p.origen, p.destino, p.estado, MAX(c.fecha_hora) AS asignado_el "
            "FROM pedidos p "
            "JOIN cambios_estado c ON c.pedido_id = p.id "
            "  AND c.estado = :asignado AND c.repartidor_id = p.repartidor_id "
            "WHERE p.repartidor_id = :repartidor_id AND p.estado IN (:asignado, :en_camino) "
            "GROUP BY p.id "
            "ORDER BY asignado_el, p.id"
        ),
        {
            "repartidor_id": repartidor_id,
            "asignado": EstadoPedido.REPARTIDOR_ASIGNADO,
            "en_camino": EstadoPedido.EN_CAMINO,
        },
    )
    return list(resultado.mappings())


def buscar_por_id(db: Session, pedido_id: int) -> RowMapping | None:
    """Trae el pedido sin bloquearlo (para consultas)."""
    resultado = db.execute(text(f"SELECT {_COLUMNAS} FROM pedidos WHERE id = :id"), {"id": pedido_id})
    return resultado.mappings().first()


def buscar_por_codigo_seguimiento(db: Session, codigo: str) -> RowMapping | None:
    resultado = db.execute(
        text(f"SELECT {_COLUMNAS} FROM pedidos WHERE codigo_seguimiento = :codigo"),
        {"codigo": codigo},
    )
    return resultado.mappings().first()


def buscar_detalle(db: Session, pedido_id: int) -> RowMapping | None:
    """Todo el pedido para el operario (HU-23): datos, repartidor actual, foto y motivo de fallo."""
    resultado = db.execute(
        text(
            "SELECT p.id, p.codigo_seguimiento, p.origen, p.destino, p.receptor_nombre, p.receptor_dni, "
            "p.peso_kg, p.alto_cm, p.ancho_cm, p.largo_cm, p.estado, p.repartidor_id, "
            "r.nombre AS repartidor_nombre, p.foto_entrega, p.motivo_fallo "
            "FROM pedidos p "
            "LEFT JOIN repartidores r ON r.id = p.repartidor_id "
            "WHERE p.id = :id"
        ),
        {"id": pedido_id},
    )
    return resultado.mappings().first()
