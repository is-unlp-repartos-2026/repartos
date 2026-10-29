"""HU-08 · Reasignar pedido.

Criterios de aceptación:
  1. Hay otro repartidor apto → se le asigna.
  2. No hay otro apto → queda "Registrado" con aviso.
Además: el motivo es obligatorio y queda en el historial, nunca vuelve al mismo repartidor, solo en
"Repartidor asignado" y solo el operario puede reasignar.
"""

from itertools import count

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.orm import Session

from repartos.core.security import crear_token, hashear_codigo_acceso
from repartos.repositories import repartidores

HEADERS_OPERARIO = {"Authorization": f"Bearer {crear_token(1, rol='operario', minutos=30)}"}
_numeros = count(1)


def headers_de(repartidor_id: int) -> dict[str, str]:
    return {"Authorization": f"Bearer {crear_token(repartidor_id, rol='repartidor', minutos=30)}"}


def repartidor_activo(cliente: TestClient, db: Session, peso: float = 20) -> int:
    n = next(_numeros)
    repartidor_id = repartidores.insertar(
        db,
        nombre=f"Repartidor {n}",
        dni=f"{52000000 + n}",
        correo=f"reasignar{n}@mail.com",
        peso_max_kg=peso,
        alto_max_cm=50,
        ancho_max_cm=50,
        largo_max_cm=50,
        codigo_acceso_hash=hashear_codigo_acceso(f"REA{n}"),
    )["id"]
    cliente.post("/repartidor/jornada/comenzar", headers=headers_de(repartidor_id))
    return repartidor_id


def registrar_pedido(cliente: TestClient) -> dict:
    datos = {
        "origen": "Almacén Don Pepe",
        "destino": "Calle 50 nro 456",
        "receptor_nombre": "Ana Gómez",
        "receptor_dni": "28111222",
        "peso_kg": 5,
        "alto_cm": 30,
        "ancho_cm": 20,
        "largo_cm": 40,
    }
    return cliente.post("/operario/pedidos", json=datos, headers=HEADERS_OPERARIO).json()


def reasignar(cliente: TestClient, pedido_id: int, cuerpo: dict | None = None, headers: dict = HEADERS_OPERARIO):
    cuerpo = {"motivo": "El repartidor avisó que se le rompió la moto"} if cuerpo is None else cuerpo
    return cliente.post(f"/operario/pedidos/{pedido_id}/reasignar", json=cuerpo, headers=headers)


def pedido_en_base(db: Session, pedido_id: int) -> tuple:
    return db.execute(
        text("SELECT estado, repartidor_id FROM pedidos WHERE id = :id"), {"id": pedido_id}
    ).one()


def ultimo_detalle(db: Session, pedido_id: int) -> str:
    return db.execute(
        text("SELECT detalle FROM cambios_estado WHERE pedido_id = :id ORDER BY id DESC LIMIT 1"),
        {"id": pedido_id},
    ).scalar_one()


# --- Criterio de aceptación 1: hay otro apto ------------------------------------------------


def test_hay_otro_apto_se_le_asigna(cliente: TestClient, db: Session) -> None:
    actual = repartidor_activo(cliente, db)
    pedido = registrar_pedido(cliente)
    otro = repartidor_activo(cliente, db)

    respuesta = reasignar(cliente, pedido["id"])

    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    assert cuerpo["estado"] == "repartidor_asignado"
    assert cuerpo["repartidor"]["id"] == otro
    assert cuerpo["aviso"] is None
    assert pedido_en_base(db, pedido["id"]) == ("repartidor_asignado", otro)
    assert ultimo_detalle(db, pedido["id"]) == "Reasignado: El repartidor avisó que se le rompió la moto"
    assert actual != otro


def test_desaparece_de_la_lista_del_repartidor_anterior(cliente: TestClient, db: Session) -> None:
    actual = repartidor_activo(cliente, db)
    pedido = registrar_pedido(cliente)
    repartidor_activo(cliente, db)

    reasignar(cliente, pedido["id"])

    assert cliente.get("/repartidor/pedidos", headers=headers_de(actual)).json() == []


# --- Criterio de aceptación 2: no hay otro apto ---------------------------------------------


def test_sin_otro_apto_queda_registrado_con_aviso(cliente: TestClient, db: Session) -> None:
    repartidor_activo(cliente, db)
    pedido = registrar_pedido(cliente)
    repartidor_activo(cliente, db, peso=1)  # activo, pero no puede llevar 5 kg

    respuesta = reasignar(cliente, pedido["id"])

    cuerpo = respuesta.json()
    assert cuerpo["estado"] == "registrado"
    assert cuerpo["repartidor"] is None
    assert cuerpo["aviso"]
    assert pedido_en_base(db, pedido["id"]) == ("registrado", None)
    assert ultimo_detalle(db, pedido["id"]) == (
        "Sin otro repartidor apto: El repartidor avisó que se le rompió la moto"
    )


def test_nunca_vuelve_al_mismo_repartidor(cliente: TestClient, db: Session) -> None:
    repartidor_activo(cliente, db)  # es el único apto
    pedido = registrar_pedido(cliente)

    cuerpo = reasignar(cliente, pedido["id"]).json()

    assert cuerpo["estado"] == "registrado"


# --- Motivo obligatorio y estados -----------------------------------------------------------


@pytest.mark.parametrize("cuerpo", [{}, {"motivo": ""}, {"motivo": "   "}], ids=["sin motivo", "vacio", "espacios"])
def test_sin_motivo_no_reasigna(cliente: TestClient, db: Session, cuerpo: dict) -> None:
    actual = repartidor_activo(cliente, db)
    pedido = registrar_pedido(cliente)
    repartidor_activo(cliente, db)

    respuesta = reasignar(cliente, pedido["id"], cuerpo)

    assert respuesta.status_code == 422
    assert pedido_en_base(db, pedido["id"]) == ("repartidor_asignado", actual)


@pytest.mark.parametrize("estado", ["registrado", "en_camino", "entregado", "entrega_fallida", "cancelado"])
def test_solo_en_repartidor_asignado(cliente: TestClient, db: Session, estado: str) -> None:
    repartidor_activo(cliente, db)
    pedido = registrar_pedido(cliente)
    db.execute(text("UPDATE pedidos SET estado = :estado WHERE id = :id"), {"estado": estado, "id": pedido["id"]})

    respuesta = reasignar(cliente, pedido["id"])

    assert respuesta.status_code == 409
    assert respuesta.json()["detail"] == "Solo se puede reasignar un pedido con repartidor asignado (todavía no retirado)"


def test_pedido_inexistente(cliente: TestClient) -> None:
    assert reasignar(cliente, 999999).status_code == 404


# --- Permisos -------------------------------------------------------------------------------


def test_un_repartidor_no_puede_reasignar(cliente: TestClient, db: Session) -> None:
    actual = repartidor_activo(cliente, db)
    pedido = registrar_pedido(cliente)

    assert reasignar(cliente, pedido["id"], headers=headers_de(actual)).status_code == 403


def test_sin_sesion_no_puede_reasignar(cliente: TestClient) -> None:
    assert cliente.post("/operario/pedidos/1/reasignar", json={"motivo": "x"}).status_code == 401
