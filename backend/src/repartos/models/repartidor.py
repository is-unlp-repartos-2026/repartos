from datetime import datetime

from sqlalchemy import DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column

from repartos.db.base import Base


class Repartidor(Base):
    __tablename__ = "repartidores"

    id: Mapped[int] = mapped_column(primary_key=True)
    nombre: Mapped[str] = mapped_column(String(100))
    dni: Mapped[str] = mapped_column(String(10), unique=True)
    correo: Mapped[str] = mapped_column(String(120))

    # Habilitación: la carga máxima que puede transportar (HU-09, HU-11).
    peso_max_kg: Mapped[float]
    alto_max_cm: Mapped[float]
    ancho_max_cm: Mapped[float]
    largo_max_cm: Mapped[float]

    # Hash del código de acceso: el repartidor ingresa solo con su código (HU-02).
    codigo_acceso_hash: Mapped[str] = mapped_column(String(64), unique=True)

    # Dos ejes independientes:
    # - habilitado: lo decide el operario (HU-12). Nunca se borra un repartidor.
    # - activo: lo decide el repartidor al comenzar o terminar su jornada (HU-13, HU-14).
    habilitado: Mapped[bool] = mapped_column(default=True)
    activo: Mapped[bool] = mapped_column(default=False)

    # Para elegir entre varios repartidores aptos: el que hace más tiempo que no recibe un pedido.
    ultima_asignacion: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    creado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
