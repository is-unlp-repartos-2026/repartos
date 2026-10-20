"""Configuración de la aplicación.

Los valores se leen de variables de entorno o del archivo .env (que no se sube al repo).
Cada desarrollador copia .env.example a .env y lo ajusta.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # extra="ignore": el .env también tiene variables para docker compose (POSTGRES_*)
    # que la app no usa; se ignoran en vez de dar error.
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Dirección de la base: postgresql+psycopg://USUARIO:CLAVE@HOST:PUERTO/BASE
    database_url: str = "postgresql+psycopg://siger:siger@localhost:5432/siger"


settings = Settings()
