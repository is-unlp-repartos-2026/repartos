from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from repartos.db.base import Base


class Operario(Base):
    """El sistema tiene un único operario; su cuenta se crea al instalar el sistema."""

    __tablename__ = "operarios"

    id: Mapped[int] = mapped_column(primary_key=True)
    usuario: Mapped[str] = mapped_column(String(50), unique=True)
    # Nunca se guarda la contraseña: solo su hash (ver core/security.py).
    password_hash: Mapped[str] = mapped_column(String(255))
