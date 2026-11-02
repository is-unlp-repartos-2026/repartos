"""HU-15 · Enviar código de acceso por correo.

Criterio de aceptación:
  1. El repartidor recibe el correo con su código (al correo cargado en el alta).
Además: si el correo falla, el alta igual se hace (y se avisa); si el alta falla, no se manda nada.
Los tests nunca mandan correos de verdad: conftest.py reemplaza el envío por una lista (`correos_enviados`).
"""

import pytest
from fastapi.testclient import TestClient

from repartos.core import correo
from repartos.core.config import settings
from repartos.core.correo import enviar as enviar_real  # el de verdad (se importa antes del reemplazo)
from repartos.core.security import crear_token

HEADERS_OPERARIO = {"Authorization": f"Bearer {crear_token(1, rol='operario', minutos=30)}"}
DATOS = {
    "nombre": "Juan Pérez",
    "dni": "30111222",
    "correo": "juan.perez@mail.com",
    "peso_max_kg": 20,
    "alto_max_cm": 50,
    "ancho_max_cm": 50,
    "largo_max_cm": 50,
}


def alta(cliente: TestClient, **cambios):
    return cliente.post("/operario/repartidores", json=DATOS | cambios, headers=HEADERS_OPERARIO)


# --- Criterio de aceptación: recibe el correo con su código ---------------------------------


def test_el_alta_le_manda_el_codigo_a_su_correo(cliente: TestClient, correos_enviados: list[dict]) -> None:
    respuesta = alta(cliente)

    assert respuesta.status_code == 201
    assert respuesta.json()["correo_enviado"] is True
    assert len(correos_enviados) == 1
    enviado = correos_enviados[0]
    assert enviado["destinatario"] == "juan.perez@mail.com"
    assert respuesta.json()["codigo_acceso"] in enviado["cuerpo"]
    assert "Juan Pérez" in enviado["cuerpo"]


# --- Reglas ---------------------------------------------------------------------------------


def test_si_el_correo_falla_el_alta_igual_se_hace(cliente: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(correo, "enviar", lambda destinatario, asunto, cuerpo: False)

    respuesta = alta(cliente)

    assert respuesta.status_code == 201
    assert respuesta.json()["correo_enviado"] is False
    assert respuesta.json()["codigo_acceso"]  # el operario igual lo ve y se lo pasa en mano


def test_si_el_alta_falla_no_se_manda_nada(cliente: TestClient, correos_enviados: list[dict]) -> None:
    alta(cliente)
    correos_enviados.clear()

    respuesta = alta(cliente, correo="otro@mail.com")  # mismo DNI

    assert respuesta.status_code == 409
    assert correos_enviados == []


def test_sin_configurar_no_intenta_mandar(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "smtp_host", "")

    assert enviar_real("juan@mail.com", "Asunto", "Cuerpo") is False


def test_si_el_servidor_de_correo_no_responde_no_rompe(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "smtp_host", "127.0.0.1")
    monkeypatch.setattr(settings, "smtp_puerto", 1)  # nadie escucha en ese puerto: la conexión falla

    assert enviar_real("juan@mail.com", "Asunto", "Cuerpo") is False
