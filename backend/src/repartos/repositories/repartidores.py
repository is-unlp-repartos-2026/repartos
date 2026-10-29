"""Consultas SQL de la tabla repartidores."""

from sqlalchemy import RowMapping, text
from sqlalchemy.orm import Session

# Columnas que se devuelven al leer un repartidor (nunca el hash del código de acceso).
_COLUMNAS = (
    "id, nombre, dni, correo, peso_max_kg, alto_max_cm, ancho_max_cm, largo_max_cm, habilitado, activo"
)


def buscar_por_id(db: Session, repartidor_id: int) -> RowMapping | None:
    resultado = db.execute(
        text(f"SELECT {_COLUMNAS} FROM repartidores WHERE id = :id"),
        {"id": repartidor_id},
    )
    return resultado.mappings().first()


def buscar_por_codigo_acceso_hash(db: Session, codigo_acceso_hash: str) -> RowMapping | None:
    """Busca al dueño de un código de acceso por su hash (HU-02). Devuelve id y habilitado, o None."""
    resultado = db.execute(
        text("SELECT id, habilitado FROM repartidores WHERE codigo_acceso_hash = :hash"),
        {"hash": codigo_acceso_hash},
    )
    return resultado.mappings().first()


def existe_dni(db: Session, dni: str) -> bool:
    resultado = db.execute(
        # EXISTS corta en cuanto encuentra una fila: no hace falta traer los datos.
        text("SELECT EXISTS (SELECT 1 FROM repartidores WHERE dni = :dni)"),
        {"dni": dni},
    )
    return resultado.scalar_one()


def existe_correo(db: Session, correo: str) -> bool:
    resultado = db.execute(
        # lower(): "Juan@Mail.com" y "juan@mail.com" son el mismo correo.
        text("SELECT EXISTS (SELECT 1 FROM repartidores WHERE lower(correo) = lower(:correo))"),
        {"correo": correo},
    )
    return resultado.scalar_one()


def insertar(
    db: Session,
    nombre: str,
    dni: str,
    correo: str,
    peso_max_kg: float,
    alto_max_cm: float,
    ancho_max_cm: float,
    largo_max_cm: float,
    codigo_acceso_hash: str,
) -> RowMapping:
    """Inserta un repartidor y devuelve la fila creada.

    habilitado y activo no se mandan: los pone la base con su valor por defecto (habilitado e inactivo).
    RETURNING devuelve la fila tal como quedó guardada, con esos valores incluidos.
    """
    resultado = db.execute(
        text(
            "INSERT INTO repartidores "
            "(nombre, dni, correo, peso_max_kg, alto_max_cm, ancho_max_cm, largo_max_cm, codigo_acceso_hash) "
            "VALUES (:nombre, :dni, :correo, :peso_max_kg, :alto_max_cm, :ancho_max_cm, :largo_max_cm, "
            ":codigo_acceso_hash) "
            f"RETURNING {_COLUMNAS}"  # _COLUMNAS es texto fijo del código, nunca un dato del usuario
        ),
        {
            "nombre": nombre,
            "dni": dni,
            "correo": correo,
            "peso_max_kg": peso_max_kg,
            "alto_max_cm": alto_max_cm,
            "ancho_max_cm": ancho_max_cm,
            "largo_max_cm": largo_max_cm,
            "codigo_acceso_hash": codigo_acceso_hash,
        },
    )
    return resultado.mappings().one()


def buscar_apto_y_bloquear(
    db: Session,
    peso_kg: float,
    alto_cm: float,
    ancho_cm: float,
    largo_cm: float,
    excluir_id: int | None = None,
) -> RowMapping | None:
    """Regla de asignación (HU-04): el repartidor que puede llevar el pedido y hace más tiempo que no recibe uno.

    - Apto: activo, habilitado y con peso y cada medida máxima mayores o iguales a las del pedido.
    - excluir_id: para reasignar o rechazar (HU-08, HU-19), el repartidor actual no cuenta. Si es None,
      la condición ":excluir_id IS NULL" es verdadera y no excluye a nadie.
    - ORDER BY ultima_asignacion NULLS FIRST: primero los que nunca recibieron un pedido, después el que
      lo recibió hace más tiempo. "id" desempata para que el resultado no dependa del azar.
    - FOR UPDATE: bloquea la fila del elegido hasta el commit. Si al mismo tiempo ese repartidor intenta
      terminar su jornada (o el operario lo deshabilita), ese UPDATE espera a que termine esta asignación,
      y entonces ve el pedido nuevo y lo reasigna. Sin el bloqueo, el pedido podría quedar asignado a
      alguien que ya se fue.
    """
    resultado = db.execute(
        text(
            "SELECT id, nombre FROM repartidores "
            "WHERE activo AND habilitado "
            "AND peso_max_kg >= :peso_kg "
            "AND alto_max_cm >= :alto_cm AND ancho_max_cm >= :ancho_cm AND largo_max_cm >= :largo_cm "
            # CAST: con None, PostgreSQL no puede deducir el tipo de :excluir_id y da error.
            "AND (CAST(:excluir_id AS INTEGER) IS NULL OR id <> :excluir_id) "
            "ORDER BY ultima_asignacion NULLS FIRST, id "
            "LIMIT 1 "
            "FOR UPDATE"
        ),
        {
            "peso_kg": peso_kg,
            "alto_cm": alto_cm,
            "ancho_cm": ancho_cm,
            "largo_cm": largo_cm,
            "excluir_id": excluir_id,
        },
    )
    return resultado.mappings().first()


def registrar_asignacion(db: Session, repartidor_id: int) -> None:
    """Anota cuándo recibió su último pedido (para el orden de la próxima asignación).

    clock_timestamp() y no now(): now() es la hora en que EMPEZÓ la transacción, y una misma transacción
    puede asignar varios pedidos seguidos (por ejemplo, al terminar una jornada). Con now() todos quedarían
    con la misma hora y el orden "el que hace más tiempo que no recibe" no se respetaría.
    """
    db.execute(
        text("UPDATE repartidores SET ultima_asignacion = clock_timestamp() WHERE id = :id"),
        {"id": repartidor_id},
    )


def cambiar_activo(db: Session, repartidor_id: int, activo: bool) -> None:
    """Comenzar (True) o terminar (False) la jornada laboral (HU-13, HU-14)."""
    db.execute(
        text("UPDATE repartidores SET activo = :activo WHERE id = :id"),
        {"activo": activo, "id": repartidor_id},
    )
