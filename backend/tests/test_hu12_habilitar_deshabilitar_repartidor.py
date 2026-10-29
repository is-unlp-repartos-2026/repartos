"""HU-12 · Habilitar o deshabilitar repartidor.

Criterios de aceptación:
  1. Deshabilitar → queda marcado y sus pedidos "Repartidor asignado" se reasignan.
  2. Con un pedido en camino → no permite deshabilitar.
  3. Volver a habilitar → recupera el acceso y su historial.
Además: deshabilitado no entra a la app ni recibe pedidos, nunca se borra, y solo el operario puede hacerlo.
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


def crear_repartidor(db: Session, peso: float = 20) -> tuple[int, str]:
    n = next(_numeros)
    codigo = f"HAB{n:05d}"
    repartidor_id = repartidores.insertar(
        db,
        nombre=f"Repartidor {n}",
        dni=f"{53000000 + n}",
        correo=f"habilitar{n}@mail.com",
        peso_max_kg=peso,
        alto_max_cm=50,
        ancho_max_cm=50,
        largo_max_cm=50,
        codigo_acceso_hash=hashear_codigo_acceso(codigo),
    )["id"]
    return repartidor_id, codigo


def repartidor_activo(cliente: TestClient, db: Session, peso: float = 20) -> int:
    repartidor_id, _ = crear_repartidor(db, peso)
    cliente.post("/repartidor/jornada/comenzar", headers=headers_de(repartidor_id))
    return repartidor_id


def registrar_pedido(cliente: TestClient) -> int:
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
    return cliente.post("/operario/pedidos", json=datos, headers=HEADERS_OPERARIO).json()["id"]


def deshabilitar(cliente: TestClient, repartidor_id: int, headers: dict = HEADERS_OPERARIO):
    return cliente.post(f"/operario/repartidores/{repartidor_id}/deshabilitar", headers=headers)


def habilitar(cliente: TestClient, repartidor_id: int, headers: dict = HEADERS_OPERARIO):
    return cliente.post(f"/operario/repartidores/{repartidor_id}/habilitar", headers=headers)


def pedido_en_base(db: Session, pedido_id: int) -> tuple:
    return db.execute(
        text("SELECT estado, repartidor_id FROM pedidos WHERE id = :id"), {"id": pedido_id}
    ).one()


# --- Criterio de aceptación 1: deshabilitar y reasignar -------------------------------------


def test_deshabilitar_marca_y_reasigna(cliente: TestClient, db: Session) -> None:
    se_va = repartidor_activo(cliente, db)
    pedido = registrar_pedido(cliente)
    otro = repartidor_activo(cliente, db)

    respuesta = deshabilitar(cliente, se_va)

    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    assert cuerpo["repartidor"]["habilitado"] is False
    assert cuerpo["repartidor"]["activo"] is False
    assert (cuerpo["pedidos_reasignados"], cuerpo["pedidos_sin_repartidor"]) == (1, 0)
    assert pedido_en_base(db, pedido) == ("repartidor_asignado", otro)
    detalle = db.execute(
        text("SELECT detalle FROM cambios_estado WHERE pedido_id = :id ORDER BY id DESC LIMIT 1"), {"id": pedido}
    ).scalar_one()
    assert detalle == "Reasignado: el repartidor fue deshabilitado"


def test_sin_otro_apto_sus_pedidos_vuelven_a_registrado(cliente: TestClient, db: Session) -> None:
    se_va = repartidor_activo(cliente, db)
    pedido = registrar_pedido(cliente)

    cuerpo = deshabilitar(cliente, se_va).json()

    assert (cuerpo["pedidos_reasignados"], cuerpo["pedidos_sin_repartidor"]) == (0, 1)
    assert pedido_en_base(db, pedido) == ("registrado", None)


def test_deshabilitado_no_entra_a_la_app_ni_recibe_pedidos(cliente: TestClient, db: Session) -> None:
    repartidor_id, codigo = crear_repartidor(db)
    token = cliente.post("/repartidor/login", json={"codigo": codigo}).json()["token"]
    cliente.post("/repartidor/jornada/comenzar", headers={"Authorization": f"Bearer {token}"})

    deshabilitar(cliente, repartidor_id)

    assert cliente.post("/repartidor/login", json={"codigo": codigo}).status_code == 403
    assert cliente.get("/repartidor/sesion", headers={"Authorization": f"Bearer {token}"}).status_code == 403
    assert pedido_en_base(db, registrar_pedido(cliente)) == ("registrado", None)


def test_nunca_se_borra(cliente: TestClient, db: Session) -> None:
    repartidor_id, _ = crear_repartidor(db)

    deshabilitar(cliente, repartidor_id)

    deshabilitados = cliente.get("/operario/repartidores?habilitado=false", headers=HEADERS_OPERARIO).json()
    assert [r["id"] for r in deshabilitados] == [repartidor_id]


# --- Criterio de aceptación 2: con un pedido en camino --------------------------------------


def test_con_pedido_en_camino_no_permite(cliente: TestClient, db: Session) -> None:
    repartidor = repartidor_activo(cliente, db)
    pedido = registrar_pedido(cliente)
    cliente.post(f"/repartidor/pedidos/{pedido}/retirar", headers=headers_de(repartidor))

    respuesta = deshabilitar(cliente, repartidor)

    assert respuesta.status_code == 409
    assert respuesta.json()["detail"] == (
        "El repartidor tiene pedidos en camino: no se puede deshabilitar hasta que termine esas entregas"
    )
    habilitado = db.execute(
        text("SELECT habilitado FROM repartidores WHERE id = :id"), {"id": repartidor}
    ).scalar_one()
    assert habilitado is True


# --- Criterio de aceptación 3: volver a habilitar -------------------------------------------


def test_volver_a_habilitar_recupera_acceso_e_historial(cliente: TestClient, db: Session) -> None:
    repartidor_id, codigo = crear_repartidor(db)
    cliente.post("/repartidor/jornada/comenzar", headers=headers_de(repartidor_id))
    pedido = registrar_pedido(cliente)
    deshabilitar(cliente, repartidor_id)

    respuesta = habilitar(cliente, repartidor_id)

    assert respuesta.status_code == 200
    assert respuesta.json()["habilitado"] is True
    assert respuesta.json()["activo"] is False  # tiene que comenzar la jornada de nuevo
    assert cliente.post("/repartidor/login", json={"codigo": codigo}).status_code == 200
    # Su historial sigue: el pedido que tuvo figura con él.
    historial = cliente.get(f"/operario/pedidos/{pedido}", headers=HEADERS_OPERARIO).json()["historial"]
    assert any(c["repartidor"] and c["repartidor"]["id"] == repartidor_id for c in historial)


# --- Otros casos y permisos -----------------------------------------------------------------


def test_no_se_deshabilita_dos_veces_ni_se_habilita_a_uno_habilitado(cliente: TestClient, db: Session) -> None:
    repartidor_id, _ = crear_repartidor(db)

    assert habilitar(cliente, repartidor_id).status_code == 409
    deshabilitar(cliente, repartidor_id)
    assert deshabilitar(cliente, repartidor_id).status_code == 409


@pytest.mark.parametrize("accion", [deshabilitar, habilitar])
def test_repartidor_inexistente(cliente: TestClient, accion) -> None:
    assert accion(cliente, 999999).status_code == 404


def test_un_repartidor_no_puede_deshabilitar(cliente: TestClient, db: Session) -> None:
    repartidor_id, _ = crear_repartidor(db)

    assert deshabilitar(cliente, repartidor_id, headers=headers_de(repartidor_id)).status_code == 403


def test_sin_sesion_no_puede_deshabilitar(cliente: TestClient) -> None:
    assert cliente.post("/operario/repartidores/1/deshabilitar").status_code == 401
