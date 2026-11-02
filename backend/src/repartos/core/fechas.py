"""Fechas en la zona horaria del negocio (la base guarda todo en UTC)."""

from datetime import date, datetime
from zoneinfo import ZoneInfo

from repartos.core.config import settings


def hoy() -> date:
    """El día de hoy en Argentina (en UTC, a las 22 h ya sería mañana)."""
    return datetime.now(ZoneInfo(settings.zona_horaria)).date()
