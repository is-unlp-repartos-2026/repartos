"""HU-01 · Autenticar operario.

Criterios de aceptación:
  1. Credenciales válidas → ingresa (recibe un token).
  2. Credenciales inválidas → no ingresa y ve un mensaje de error.
Además, se prueba que los endpoints del operario quedan protegidos (sin sesión, sesión vencida o
alterada, o con la sesión de otro rol, no se puede usar).
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from repartos.core.security import crear_token, hashear_contrasena
from repartos.repositories import operarios

USUARIO = "martin"
CONTRASENA = "clave-de-prueba"


@pytest.fixture
def operario_id(db: Session) -> int:
    """Crea el operario en la base de prueba (como lo haría el comando crear_operario)."""
    return operarios.insertar(db, USUARIO, hashear_contrasena(CONTRASENA))


def iniciar_sesion(cliente: TestClient, usuario: str, contrasena: str):
    return cliente.post("/operario/login", json={"usuario": usuario, "contrasena": contrasena})


def autorizacion(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


# --- Criterio de aceptación 1: credenciales válidas ------------------------------------------


def test_credenciales_validas_ingresa(cliente: TestClient, operario_id: int) -> None:
    respuesta = iniciar_sesion(cliente, USUARIO, CONTRASENA)

    assert respuesta.status_code == 200
    token = respuesta.json()["token"]

    # Con ese token puede usar los endpoints del operario.
    sesion = cliente.get("/operario/sesion", headers=autorizacion(token))
    assert sesion.status_code == 200
    assert sesion.json() == {"id": operario_id, "usuario": USUARIO}


# --- Criterio de aceptación 2: credenciales inválidas ----------------------------------------


def test_contrasena_incorrecta_no_ingresa(cliente: TestClient, operario_id: int) -> None:
    respuesta = iniciar_sesion(cliente, USUARIO, "otra-contrasena")

    assert respuesta.status_code == 401
    assert respuesta.json()["detail"] == "Usuario o contraseña incorrectos"


def test_usuario_inexistente_no_ingresa_con_el_mismo_mensaje(cliente: TestClient, operario_id: int) -> None:
    respuesta = iniciar_sesion(cliente, "usuario-que-no-existe", CONTRASENA)

    # El mismo mensaje que con la contraseña incorrecta: no se revela qué usuarios existen.
    assert respuesta.status_code == 401
    assert respuesta.json()["detail"] == "Usuario o contraseña incorrectos"


# --- Protección de los endpoints del operario ------------------------------------------------


def test_sin_sesion_no_accede(cliente: TestClient) -> None:
    respuesta = cliente.get("/operario/sesion")

    assert respuesta.status_code == 401


def test_sesion_vencida_no_accede(cliente: TestClient, operario_id: int) -> None:
    token_vencido = crear_token(operario_id, rol="operario", minutos=-1)  # venció hace un minuto

    respuesta = cliente.get("/operario/sesion", headers=autorizacion(token_vencido))

    assert respuesta.status_code == 401


def test_token_alterado_no_accede(cliente: TestClient, operario_id: int) -> None:
    token = crear_token(operario_id, rol="operario", minutos=30)
    token_alterado = token[:-4] + ("AAAA" if not token.endswith("AAAA") else "BBBB")  # se cambia la firma

    respuesta = cliente.get("/operario/sesion", headers=autorizacion(token_alterado))

    assert respuesta.status_code == 401


def test_sesion_de_repartidor_no_accede_a_funciones_del_operario(cliente: TestClient) -> None:
    token_repartidor = crear_token(1, rol="repartidor", minutos=30)

    respuesta = cliente.get("/operario/sesion", headers=autorizacion(token_repartidor))

    assert respuesta.status_code == 403
