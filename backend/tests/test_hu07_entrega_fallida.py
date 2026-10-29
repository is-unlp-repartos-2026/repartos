"""HU-07 · Registrar entrega fallida.

Criterio de aceptación:
  1. Con motivo → "Entrega fallida" y el motivo queda guardado.
Además: el motivo es obligatorio (y "Otro" necesita aclaración), solo desde "En camino", "Entrega fallida"
es final, solo pedidos propios y solo el repartidor puede registrarla.
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
        dni=f"{45000000 + n}",
        correo=f"fallida{n}@mail.com",
        peso_max_kg=20,
        alto_max_cm=50,
        ancho_max_cm=50,
        largo_max_cm=50,
        codigo_acceso_hash=hashear_codigo_acceso(f"FAL{n}"),
    )
    cliente.post("/repartidor/jornada/comenzar", headers=headers_de(fila["id"]))
    return fila["id"]


def pedido_en_camino(cliente: TestClient, repartidor_id: int) -> int:
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
    pedido_id = cliente.post("/operario/pedidos", json=datos, headers=HEADERS_OPERARIO).json()["id"]
    cliente.post(f"/repartidor/pedidos/{pedido_id}/retirar", headers=headers_de(repartidor_id))
    return pedido_id


def fallida(cliente: TestClient, pedido_id: int, repartidor_id: int, cuerpo: dict):
    return cliente.post(
        f"/repartidor/pedidos/{pedido_id}/entrega-fallida", json=cuerpo, headers=headers_de(repartidor_id)
    )


def pedido_en_base(db: Session, pedido_id: int) -> tuple:
    return db.execute(
        text("SELECT estado, motivo_fallo FROM pedidos WHERE id = :id"), {"id": pedido_id}
    ).one()


# --- Criterio de aceptación 1: con motivo ---------------------------------------------------


def test_con_motivo_queda_entrega_fallida(cliente: TestClient, db: Session) -> None:
    repartidor = repartidor_activo(cliente, db)
    pedido = pedido_en_camino(cliente, repartidor)

    respuesta = fallida(cliente, pedido, repartidor, {"motivo": "Destinatario ausente"})

    assert respuesta.status_code == 200
    assert respuesta.json() == {"id": pedido, "estado": "entrega_fallida"}
    assert pedido_en_base(db, pedido) == ("entrega_fallida", "Destinatario ausente")
    detalle = db.execute(
        text("SELECT detalle FROM cambios_estado WHERE pedido_id = :id AND estado = 'entrega_fallida'"),
        {"id": pedido},
    ).scalar_one()
    assert detalle == "Destinatario ausente"


def test_motivo_otro_guarda_la_aclaracion(cliente: TestClient, db: Session) -> None:
    repartidor = repartidor_activo(cliente, db)
    pedido = pedido_en_camino(cliente, repartidor)

    fallida(cliente, pedido, repartidor, {"motivo": "Otro", "aclaracion": "Se rompió la moto"})

    assert pedido_en_base(db, pedido) == ("entrega_fallida", "Otro: Se rompió la moto")


# --- Motivo obligatorio ---------------------------------------------------------------------


@pytest.mark.parametrize(
    "cuerpo",
    [{}, {"motivo": "Llovía"}, {"motivo": "Otro"}, {"motivo": "Otro", "aclaracion": "   "}],
    ids=["sin motivo", "motivo inventado", "otro sin aclaracion", "otro con aclaracion vacia"],
)
def test_sin_motivo_valido_no_se_registra(cliente: TestClient, db: Session, cuerpo: dict) -> None:
    repartidor = repartidor_activo(cliente, db)
    pedido = pedido_en_camino(cliente, repartidor)

    respuesta = fallida(cliente, pedido, repartidor, cuerpo)

    assert respuesta.status_code == 422
    assert pedido_en_base(db, pedido) == ("en_camino", None)


# --- Estados y pertenencia ------------------------------------------------------------------


def test_solo_desde_en_camino(cliente: TestClient, db: Session) -> None:
    repartidor = repartidor_activo(cliente, db)
    datos = {
        "origen": "A", "destino": "B", "receptor_nombre": "C", "receptor_dni": "28111222",
        "peso_kg": 1, "alto_cm": 1, "ancho_cm": 1, "largo_cm": 1,
    }
    asignado = cliente.post("/operario/pedidos", json=datos, headers=HEADERS_OPERARIO).json()["id"]

    respuesta = fallida(cliente, asignado, repartidor, {"motivo": "Destinatario ausente"})

    assert respuesta.status_code == 409
    assert respuesta.json()["detail"] == "Solo se puede registrar una entrega fallida de un pedido en camino"


def test_entrega_fallida_es_final(cliente: TestClient, db: Session) -> None:
    repartidor = repartidor_activo(cliente, db)
    pedido = pedido_en_camino(cliente, repartidor)
    fallida(cliente, pedido, repartidor, {"motivo": "Destinatario ausente"})

    otra_vez = fallida(cliente, pedido, repartidor, {"motivo": "Pedido rechazado"})
    cancelar = cliente.post(f"/operario/pedidos/{pedido}/cancelar", headers=HEADERS_OPERARIO)

    assert otra_vez.status_code == 409
    assert cancelar.status_code == 409
    assert pedido_en_base(db, pedido) == ("entrega_fallida", "Destinatario ausente")


def test_no_puede_registrarla_en_un_pedido_de_otro(cliente: TestClient, db: Session) -> None:
    dueno = repartidor_activo(cliente, db)
    pedido = pedido_en_camino(cliente, dueno)
    otro = repartidor_activo(cliente, db)

    respuesta = fallida(cliente, pedido, otro, {"motivo": "Destinatario ausente"})

    assert respuesta.status_code == 404


# --- Permisos -------------------------------------------------------------------------------


def test_el_operario_no_puede_registrarla(cliente: TestClient) -> None:
    respuesta = cliente.post(
        "/repartidor/pedidos/1/entrega-fallida", json={"motivo": "Destinatario ausente"}, headers=HEADERS_OPERARIO
    )
    assert respuesta.status_code == 403


def test_sin_sesion_no_puede_registrarla(cliente: TestClient) -> None:
    respuesta = cliente.post("/repartidor/pedidos/1/entrega-fallida", json={"motivo": "Destinatario ausente"})
    assert respuesta.status_code == 401
