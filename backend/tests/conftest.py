"""Piezas compartidas por todos los tests (pytest carga este archivo solo).

- Los tests usan una base aparte: la de desarrollo + "_test" (por ejemplo, siger_test).
  Se crea sola la primera vez y se le aplican las mismas migraciones de Alembic.
- Fixture `db`: una sesión cuya transacción se deshace al terminar cada test → cada test arranca vacío.
- Fixture `cliente`: hace requests a la API (sin levantar Uvicorn) usando la base de prueba.
"""

from collections.abc import Generator
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import Engine, create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session

from repartos.core.config import settings
from repartos.db.session import get_db
from repartos.main import app

RAIZ_BACKEND = Path(__file__).resolve().parents[1]

URL_DESARROLLO = make_url(settings.database_url)
URL_TESTS = URL_DESARROLLO.set(database=f"{URL_DESARROLLO.database}_test")


def _crear_base_de_tests_si_no_existe() -> None:
    # Para crear una base hay que estar conectado a otra: "postgres" existe siempre.
    # AUTOCOMMIT porque PostgreSQL no permite CREATE DATABASE dentro de una transacción.
    engine = create_engine(URL_DESARROLLO.set(database="postgres"), isolation_level="AUTOCOMMIT")
    with engine.connect() as conexion:
        existe = conexion.scalar(
            text("SELECT 1 FROM pg_database WHERE datname = :nombre"),
            {"nombre": URL_TESTS.database},
        )
        if not existe:
            # El nombre de una base es un identificador, no un valor: no se puede pasar como parámetro (:nombre).
            # Por eso se escapa con quote(), que lo pone entre comillas dobles de forma segura.
            nombre = conexion.dialect.identifier_preparer.quote(URL_TESTS.database)
            conexion.execute(text(f"CREATE DATABASE {nombre}"))
    engine.dispose()


@pytest.fixture(scope="session")
def engine_tests() -> Generator[Engine]:
    """Se ejecuta UNA vez por corrida de pytest: prepara la base de prueba."""
    _crear_base_de_tests_si_no_existe()

    # Aplicar las migraciones a la base de prueba (las mismas que a la de desarrollo).
    config_alembic = Config(str(RAIZ_BACKEND / "alembic.ini"))
    config_alembic.attributes["url"] = URL_TESTS.render_as_string(hide_password=False)
    command.upgrade(config_alembic, "head")

    engine = create_engine(URL_TESTS)
    yield engine
    engine.dispose()


@pytest.fixture
def db(engine_tests: Engine) -> Generator[Session]:
    """Se ejecuta en CADA test: una sesión dentro de una transacción que al final se deshace."""
    conexion = engine_tests.connect()
    transaccion = conexion.begin()
    # create_savepoint: si el código del test hace commit(), en realidad guarda un punto intermedio
    # dentro de la transacción de arriba; al final del test se deshace todo igual.
    sesion = Session(bind=conexion, join_transaction_mode="create_savepoint")

    yield sesion

    sesion.close()
    transaccion.rollback()
    conexion.close()


@pytest.fixture
def cliente(db: Session) -> Generator[TestClient]:
    """Cliente HTTP de prueba: los endpoints reciben la sesión `db` en lugar de la base de desarrollo."""
    app.dependency_overrides[get_db] = lambda: db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
