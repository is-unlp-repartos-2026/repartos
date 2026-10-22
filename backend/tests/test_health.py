"""Prueba de humo: verifica que toda la cadena de tests funciona (pytest, base de prueba, migraciones, cliente)."""

from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.orm import Session


def test_la_api_responde(cliente: TestClient) -> None:
    respuesta = cliente.get("/")

    assert respuesta.status_code == 200
    assert respuesta.json() == {"status": "ok"}


def test_la_base_de_prueba_tiene_las_tablas(db: Session) -> None:
    tablas = db.scalars(
        text("SELECT tablename FROM pg_tables WHERE schemaname = 'public' ORDER BY tablename")
    ).all()

    assert tablas == ["alembic_version", "cambios_estado", "operarios", "pedidos", "repartidores"]
