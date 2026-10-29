"""Schemas del inicio de sesión."""

from pydantic import BaseModel


class CredencialesOperario(BaseModel):
    """Lo que manda el frontend para iniciar sesión (body del POST /operario/login)."""

    usuario: str
    contrasena: str


class SesionIniciada(BaseModel):
    """Lo que devuelve un login exitoso: el token para mandar en cada request siguiente."""

    token: str
    tipo: str = "bearer"  # indica que se manda en el header "Authorization: Bearer <token>"


class OperarioLogueado(BaseModel):
    """Lo que devuelve GET /operario/sesion: quién es el operario de la sesión actual."""

    id: int
    usuario: str


class CodigoAccesoRepartidor(BaseModel):
    """Lo que manda la app para iniciar sesión (body del POST /repartidor/login): solo el código."""

    codigo: str
