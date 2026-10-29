"""HU-09 · Registrar repartidor.

Criterios de aceptación:
  1. Alta exitosa → el operario ve el código de acceso.
  2. DNI repetido → no permite el alta.
Además, se prueban las reglas: queda habilitado e inactivo, el código se guarda hasheado, correo repetido,
datos inválidos y que solo el operario puede dar altas.
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.orm import Session

from repartos.core.security import LARGO_CODIGO_ACCESO, crear_token, hashear_codigo_acceso

URL = "/operario/repartidores"


def datos_repartidor(**cambios) -> dict:
    datos = {
        "nombre": "Juan Pérez",
        "dni": "30123456",
        "correo": "juan@mail.com",
        "peso_max_kg": 20,
        "alto_max_cm": 50,
        "ancho_max_cm": 40,
        "largo_max_cm": 60,
    }
    return datos | cambios


@pytest.fixture
def headers_operario() -> dict[str, str]:
    return {"Authorization": f"Bearer {crear_token(1, rol='operario', minutos=30)}"}


def registrar(cliente: TestClient, headers: dict[str, str], **cambios):
    return cliente.post(URL, json=datos_repartidor(**cambios), headers=headers)


# --- Criterio de aceptación 1: alta exitosa -------------------------------------------------


def test_alta_exitosa_muestra_el_codigo(cliente: TestClient, headers_operario: dict) -> None:
    respuesta = registrar(cliente, headers_operario)

    assert respuesta.status_code == 201
    cuerpo = respuesta.json()
    assert cuerpo["dni"] == "30123456"
    assert cuerpo["nombre"] == "Juan Pérez"
    assert len(cuerpo["codigo_acceso"]) == LARGO_CODIGO_ACCESO


def test_queda_habilitado_e_inactivo(cliente: TestClient, headers_operario: dict) -> None:
    cuerpo = registrar(cliente, headers_operario).json()

    assert cuerpo["habilitado"] is True
    assert cuerpo["activo"] is False


def test_el_codigo_se_guarda_hasheado(cliente: TestClient, headers_operario: dict, db: Session) -> None:
    cuerpo = registrar(cliente, headers_operario).json()

    guardado = db.execute(
        text("SELECT codigo_acceso_hash FROM repartidores WHERE id = :id"), {"id": cuerpo["id"]}
    ).scalar_one()
    assert guardado != cuerpo["codigo_acceso"]
    assert guardado == hashear_codigo_acceso(cuerpo["codigo_acceso"])


def test_cada_repartidor_recibe_un_codigo_distinto(cliente: TestClient, headers_operario: dict) -> None:
    primero = registrar(cliente, headers_operario).json()
    segundo = registrar(cliente, headers_operario, dni="30999999", correo="otro@mail.com").json()

    assert primero["codigo_acceso"] != segundo["codigo_acceso"]


# --- Criterio de aceptación 2: DNI repetido -------------------------------------------------


def test_dni_repetido_no_permite_el_alta(cliente: TestClient, headers_operario: dict, db: Session) -> None:
    registrar(cliente, headers_operario)

    respuesta = registrar(cliente, headers_operario, correo="otro@mail.com")

    assert respuesta.status_code == 409
    assert respuesta.json()["detail"] == "Ya existe un repartidor con ese DNI"
    assert db.execute(text("SELECT count(*) FROM repartidores")).scalar_one() == 1


# --- Otras reglas ---------------------------------------------------------------------------


def test_correo_repetido_no_permite_el_alta(cliente: TestClient, headers_operario: dict) -> None:
    registrar(cliente, headers_operario)

    respuesta = registrar(cliente, headers_operario, dni="30999999", correo="JUAN@mail.com")

    assert respuesta.status_code == 409
    assert respuesta.json()["detail"] == "Ya existe un repartidor con ese correo"


@pytest.mark.parametrize(
    "cambio",
    [
        {"dni": "30.123.456"},
        {"dni": "abc"},
        {"correo": "no-es-un-correo"},
        {"nombre": ""},
        {"peso_max_kg": 0},
        {"alto_max_cm": -5},
    ],
)
def test_datos_invalidos_no_permiten_el_alta(cliente: TestClient, headers_operario: dict, cambio: dict) -> None:
    respuesta = registrar(cliente, headers_operario, **cambio)

    assert respuesta.status_code == 422


def test_sin_sesion_no_puede_registrar(cliente: TestClient) -> None:
    respuesta = cliente.post(URL, json=datos_repartidor())

    assert respuesta.status_code == 401


def test_un_repartidor_no_puede_registrar(cliente: TestClient) -> None:
    headers = {"Authorization": f"Bearer {crear_token(1, rol='repartidor', minutos=30)}"}

    respuesta = cliente.post(URL, json=datos_repartidor(), headers=headers)

    assert respuesta.status_code == 403
