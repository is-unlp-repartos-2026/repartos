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

    # Clave para firmar los tokens (JWT). Quien la tenga puede fabricar tokens válidos:
    # en producción tiene que ser larga, aleatoria y secreta.
    secret_key: str = "clave-solo-para-desarrollo-cambiar-en-produccion"
    algoritmo_token: str = "HS256"

    # La sesión del operario vence a los 30 minutos (supuesto del equipo, HU-01).
    minutos_token_operario: int = 30
    # La sesión del repartidor queda guardada en el celular (HU-02): dura 30 días.
    # Si el operario lo deshabilita, pierde el acceso igual (se revisa en cada request).
    minutos_token_repartidor: int = 60 * 24 * 30


settings = Settings()
