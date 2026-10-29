"""HU-06 · Cancelar pedido.

Criterio de aceptación:
  1. Cancelar en un estado permitido → "Cancelado".
Además: se puede desde "Registrado" y "Repartidor asignado", no después de retirado; "Cancelado" es final;
queda en el historial con fecha y hora; solo el operario puede cancelar.
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


def repartidor_activo(cliente: TestClient, db: Session) -> int:
    n = next(_numeros)
    fila = repartidores.insertar(
        db,
        nombre=f"Repartidor {n}",
        dni=f"{44000000 + n}",
        correo=f"cancelar{n}@mail.com",
        peso_max_kg=20,
        alto_max_cm=50,
        ancho_max_cm=50,
        largo_max_cm=50,
        codigo_acceso_hash=hashear_codigo_acceso(f"CAN{n}"),
    )
    cliente.post("/repartidor/jornada/comenzar", headers=headers_de(fila["id"]))
    return fila["id"]


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


def cancelar(cliente: TestClient, pedido_id: int, headers: dict = HEADERS_OPERARIO):
    return cliente.post(f"/operario/pedidos/{pedido_id}/cancelar", headers=headers)


def estado_en_base(db: Session, pedido_id: int) -> str:
    return db.execute(text("SELECT estado FROM pedidos WHERE id = :id"), {"id": pedido_id}).scalar_one()


# --- Criterio de aceptación 1: cancelar en estado permitido ---------------------------------


def test_cancelar_un_pedido_registrado(cliente: TestClient, db: Session) -> None:
    pedido = registrar_pedido(cliente)  # sin repartidores activos → "registrado"

    respuesta = cancelar(cliente, pedido["id"])

    assert respuesta.status_code == 200
    assert respuesta.json() == {"id": pedido["id"], "estado": "cancelado"}
    assert estado_en_base(db, pedido["id"]) == "cancelado"


def test_cancelar_un_pedido_con_repartidor_asignado(cliente: TestClient, db: Session) -> None:
    repartidor = repartidor_activo(cliente, db)
    pedido = registrar_pedido(cliente)

    respuesta = cancelar(cliente, pedido["id"])

    assert respuesta.status_code == 200
    cambio = db.execute(
        text(
            "SELECT repartidor_id, detalle, fecha_hora FROM cambios_estado "
            "WHERE pedido_id = :id AND estado = 'cancelado'"
        ),
        {"id": pedido["id"]},
    ).one()
    assert cambio.repartidor_id == repartidor
    assert cambio.detalle == "Cancelado por el operario"
    assert cambio.fecha_hora is not None


def test_el_repartidor_ya_no_puede_retirar_un_pedido_cancelado(cliente: TestClient, db: Session) -> None:
    repartidor = repartidor_activo(cliente, db)
    pedido = registrar_pedido(cliente)
    cancelar(cliente, pedido["id"])

    respuesta = cliente.post(f"/repartidor/pedidos/{pedido['id']}/retirar", headers=headers_de(repartidor))

    assert respuesta.status_code == 409


# --- Estados no permitidos ------------------------------------------------------------------


@pytest.mark.parametrize("estado", ["en_camino", "entregado", "entrega_fallida", "cancelado"])
def test_no_se_puede_cancelar_despues_de_retirado_ni_en_un_estado_final(
    cliente: TestClient, db: Session, estado: str
) -> None:
    pedido = registrar_pedido(cliente)
    db.execute(text("UPDATE pedidos SET estado = :estado WHERE id = :id"), {"estado": estado, "id": pedido["id"]})

    respuesta = cancelar(cliente, pedido["id"])

    assert respuesta.status_code == 409
    assert respuesta.json()["detail"] == "Solo se puede cancelar un pedido registrado o con repartidor asignado"
    assert estado_en_base(db, pedido["id"]) == estado


def test_pedido_inexistente(cliente: TestClient) -> None:
    assert cancelar(cliente, 999999).status_code == 404


# --- Permisos -------------------------------------------------------------------------------


def test_un_repartidor_no_puede_cancelar(cliente: TestClient, db: Session) -> None:
    repartidor = repartidor_activo(cliente, db)
    pedido = registrar_pedido(cliente)

    assert cancelar(cliente, pedido["id"], headers=headers_de(repartidor)).status_code == 403


def test_sin_sesion_no_puede_cancelar(cliente: TestClient) -> None:
    assert cliente.post("/operario/pedidos/1/cancelar").status_code == 401
