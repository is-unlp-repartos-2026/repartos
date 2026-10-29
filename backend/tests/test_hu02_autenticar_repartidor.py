"""HU-02 · Autenticar repartidor.

Criterios de aceptación:
  1. Código válido → ingresa.
  2. Código inválido → no ingresa y ve un error.
  3. Repartidor deshabilitado → no ingresa.
  4. Reabrir la app → sigue logueado (el token dura días y la app lo vuelve a usar).
Además: ingresar no lo activa, y si lo deshabilitan pierde el acceso aunque su token no haya vencido.
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.orm import Session

from repartos.core.config import settings
from repartos.core.security import crear_token, generar_codigo_acceso, hashear_codigo_acceso
from repartos.repositories import repartidores


def autorizacion(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def iniciar_sesion(cliente: TestClient, codigo: str):
    return cliente.post("/repartidor/login", json={"codigo": codigo})


def deshabilitar(db: Session, repartidor_id: int) -> None:
    # Mientras no exista HU-12 (Habilitar o deshabilitar repartidor), se hace directo en la base.
    db.execute(text("UPDATE repartidores SET habilitado = false WHERE id = :id"), {"id": repartidor_id})


@pytest.fixture
def codigo() -> str:
    return generar_codigo_acceso()


@pytest.fixture
def repartidor_id(db: Session, codigo: str) -> int:
    """Un repartidor recién dado de alta (habilitado e inactivo), como lo deja HU-09."""
    fila = repartidores.insertar(
        db,
        nombre="Juan Pérez",
        dni="30123456",
        correo="juan@mail.com",
        peso_max_kg=20,
        alto_max_cm=50,
        ancho_max_cm=40,
        largo_max_cm=60,
        codigo_acceso_hash=hashear_codigo_acceso(codigo),
    )
    return fila["id"]


# --- Criterio de aceptación 1: código válido ------------------------------------------------


def test_codigo_valido_ingresa(cliente: TestClient, repartidor_id: int, codigo: str) -> None:
    respuesta = iniciar_sesion(cliente, codigo)

    assert respuesta.status_code == 200
    sesion = cliente.get("/repartidor/sesion", headers=autorizacion(respuesta.json()["token"]))
    assert sesion.status_code == 200
    assert sesion.json()["id"] == repartidor_id


def test_codigo_en_minusculas_y_con_espacios_ingresa(cliente: TestClient, repartidor_id: int, codigo: str) -> None:
    respuesta = iniciar_sesion(cliente, f"  {codigo.lower()} ")

    assert respuesta.status_code == 200


def test_ingresar_no_lo_activa(cliente: TestClient, repartidor_id: int, codigo: str) -> None:
    token = iniciar_sesion(cliente, codigo).json()["token"]

    sesion = cliente.get("/repartidor/sesion", headers=autorizacion(token))
    assert sesion.json()["activo"] is False


# --- Criterio de aceptación 2: código inválido ----------------------------------------------


def test_codigo_invalido_no_ingresa(cliente: TestClient, repartidor_id: int) -> None:
    respuesta = iniciar_sesion(cliente, "ZZZZZZZZ")

    assert respuesta.status_code == 401
    assert respuesta.json()["detail"] == "Código de acceso incorrecto"


# --- Criterio de aceptación 3: deshabilitado ------------------------------------------------


def test_deshabilitado_no_ingresa(cliente: TestClient, db: Session, repartidor_id: int, codigo: str) -> None:
    deshabilitar(db, repartidor_id)

    respuesta = iniciar_sesion(cliente, codigo)

    assert respuesta.status_code == 403
    assert respuesta.json()["detail"] == "Estás deshabilitado. Consultá con el operario"


def test_deshabilitado_pierde_el_acceso_aunque_tenga_sesion(
    cliente: TestClient, db: Session, repartidor_id: int, codigo: str
) -> None:
    token = iniciar_sesion(cliente, codigo).json()["token"]
    deshabilitar(db, repartidor_id)

    respuesta = cliente.get("/repartidor/sesion", headers=autorizacion(token))

    assert respuesta.status_code == 403


# --- Criterio de aceptación 4: sigue logueado -----------------------------------------------


def test_la_sesion_dura_dias(cliente: TestClient, repartidor_id: int) -> None:
    # Un token fabricado hace casi 30 días sigue sirviendo (simula reabrir la app mucho después).
    token = crear_token(repartidor_id, rol="repartidor", minutos=settings.minutos_token_repartidor - 1)

    respuesta = cliente.get("/repartidor/sesion", headers=autorizacion(token))

    assert respuesta.status_code == 200
    assert settings.minutos_token_repartidor >= 60 * 24 * 7  # al menos una semana


# --- Protección de los endpoints del repartidor ---------------------------------------------


def test_sin_sesion_no_accede(cliente: TestClient) -> None:
    assert cliente.get("/repartidor/sesion").status_code == 401


def test_sesion_vencida_no_accede(cliente: TestClient, repartidor_id: int) -> None:
    token = crear_token(repartidor_id, rol="repartidor", minutos=-1)

    assert cliente.get("/repartidor/sesion", headers=autorizacion(token)).status_code == 401


def test_sesion_del_operario_no_accede_a_funciones_del_repartidor(cliente: TestClient) -> None:
    token = crear_token(1, rol="operario", minutos=30)

    assert cliente.get("/repartidor/sesion", headers=autorizacion(token)).status_code == 403
