import enum
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from repartos.db.base import Base
from repartos.models.repartidor import Repartidor


class EstadoPedido(enum.StrEnum):
    """Ciclo de vida del pedido. Finales: ENTREGADO, ENTREGA_FALLIDA y CANCELADO."""

    REGISTRADO = "registrado"
    REPARTIDOR_ASIGNADO = "repartidor_asignado"
    EN_CAMINO = "en_camino"
    ENTREGADO = "entregado"
    ENTREGA_FALLIDA = "entrega_fallida"
    CANCELADO = "cancelado"


class Pedido(Base):
    __tablename__ = "pedidos"

    id: Mapped[int] = mapped_column(primary_key=True)
    # Único y no deducible: es el único control de acceso del cliente final (HU-21).
    codigo_seguimiento: Mapped[str] = mapped_column(String(20), unique=True)

    origen: Mapped[str] = mapped_column(String(200))
    destino: Mapped[str] = mapped_column(String(200))
    receptor_nombre: Mapped[str] = mapped_column(String(100))
    receptor_dni: Mapped[str] = mapped_column(String(10))
    # Por privacidad, el contenido del paquete NUNCA se registra.
    peso_kg: Mapped[float]
    alto_cm: Mapped[float]
    ancho_cm: Mapped[float]
    largo_cm: Mapped[float]

    estado: Mapped[EstadoPedido] = mapped_column(
        Enum(EstadoPedido, values_callable=lambda e: [x.value for x in e]),
        default=EstadoPedido.REGISTRADO,
    )
    repartidor_id: Mapped[int | None] = mapped_column(ForeignKey("repartidores.id"))
    repartidor: Mapped[Repartidor | None] = relationship()

    # Datos de cierre: confirmación de entrega (HU-20) o entrega fallida (HU-07).
    foto_entrega: Mapped[str | None] = mapped_column(String(255))
    dni_entrega: Mapped[str | None] = mapped_column(String(10))
    motivo_fallo: Mapped[str | None] = mapped_column(String(200))

    creado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    historial: Mapped[list["CambioEstado"]] = relationship(
        back_populates="pedido", order_by="CambioEstado.fecha_hora"
    )


class CambioEstado(Base):
    """Historial: cada cambio de estado de un pedido, con su fecha y hora."""

    __tablename__ = "cambios_estado"

    id: Mapped[int] = mapped_column(primary_key=True)
    pedido_id: Mapped[int] = mapped_column(ForeignKey("pedidos.id"))
    estado: Mapped[EstadoPedido] = mapped_column(
        Enum(EstadoPedido, values_callable=lambda e: [x.value for x in e])
    )
    fecha_hora: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    # Motivo o aclaración: cancelación, reasignación, rechazo, entrega fallida, etc.
    detalle: Mapped[str | None] = mapped_column(String(200))

    pedido: Mapped[Pedido] = relationship(back_populates="historial")
