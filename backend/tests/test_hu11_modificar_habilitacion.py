"""HU-11 · Modificar habilitación de repartidor.

Criterios de aceptación:
  1. Sin pedidos en curso → se guarda y se usa en las próximas asignaciones.
  2. Con pedidos en curso → no permite y avisa.
Además: datos válidos, repartidor inexistente y solo el operario puede modificarla.
"""

from itertools import count

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from repartos.core.security import crear_token, hashear_codigo_acceso
from repartos.repositories import repartidores

HEADERS_OPERARIO = {"Authorization": f"Bearer {crear_token(1, rol='operario', minutos=30)}"}
NUEVA = {"peso_max_kg": 30, "alto_max_cm": 60, "ancho_max_cm": 60, "largo_max_cm": 80}
_numeros = count(1)


def headers_de(repartidor_id: int) -> dict[str, str]:
    return {"Authorization": f"Bearer {crear_token(repartidor_id, rol='repartidor', minutos=30)}"}


def crear_repartidor(db: Session, peso: float = 20) -> int:
    n = next(_numeros)
    return repartidores.insertar(
        db,
        nombre=f"Repartidor {n}",
        dni=f"{54000000 + n}",
        correo=f"habilitacion{n}@mail.com",
        peso_max_kg=peso,
        alto_max_cm=50,
        ancho_max_cm=50,
        largo_max_cm=50,
        codigo_acceso_hash=hashear_codigo_acceso(f"HBL{n}"),
    )["id"]


def registrar_pedido(cliente: TestClient, peso: float = 5) -> dict:
    datos = {
        "origen": "Almacén Don Pepe",
        "destino": "Calle 50 nro 456",
        "receptor_nombre": "Ana Gómez",
        "receptor_dni": "28111222",
        "peso_kg": peso,
        "alto_cm": 30,
        "ancho_cm": 20,
        "largo_cm": 40,
    }
    return cliente.post("/operario/pedidos", json=datos, headers=HEADERS_OPERARIO).json()


def modificar(cliente: TestClient, repartidor_id: int, cuerpo: dict = NUEVA, headers: dict = HEADERS_OPERARIO):
    return cliente.put(f"/operario/repartidores/{repartidor_id}/habilitacion", json=cuerpo, headers=headers)


# --- Criterio de aceptación 1: sin pedidos en curso -----------------------------------------


def test_sin_pedidos_en_curso_se_guarda(cliente: TestClient, db: Session) -> None:
    repartidor = crear_repartidor(db)

    respuesta = modificar(cliente, repartidor)

    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    assert {k: cuerpo[k] for k in NUEVA} == NUEVA


def test_la_nueva_habilitacion_se_usa_en_las_proximas_asignaciones(cliente: TestClient, db: Session) -> None:
    repartidor = crear_repartidor(db, peso=20)
    cliente.post("/repartidor/jornada/comenzar", headers=headers_de(repartidor))
    assert registrar_pedido(cliente, peso=25)["repartidor"] is None  # antes no podía con 25 kg

    modificar(cliente, repartidor)  # ahora hasta 30 kg

    assert registrar_pedido(cliente, peso=25)["repartidor"]["id"] == repartidor


def test_puede_modificarse_con_pedidos_ya_terminados(cliente: TestClient, db: Session) -> None:
    repartidor = crear_repartidor(db)
    cliente.post("/repartidor/jornada/comenzar", headers=headers_de(repartidor))
    pedido = registrar_pedido(cliente)
    cliente.post(f"/operario/pedidos/{pedido['id']}/cancelar", headers=HEADERS_OPERARIO)

    assert modificar(cliente, repartidor).status_code == 200


# --- Criterio de aceptación 2: con pedidos en curso -----------------------------------------


@pytest.mark.parametrize("retirado", [False, True], ids=["asignado", "en camino"])
def test_con_pedidos_en_curso_no_permite(cliente: TestClient, db: Session, retirado: bool) -> None:
    repartidor = crear_repartidor(db)
    cliente.post("/repartidor/jornada/comenzar", headers=headers_de(repartidor))
    pedido = registrar_pedido(cliente)
    if retirado:
        cliente.post(f"/repartidor/pedidos/{pedido['id']}/retirar", headers=headers_de(repartidor))

    respuesta = modificar(cliente, repartidor)

    assert respuesta.status_code == 409
    assert respuesta.json()["detail"] == (
        "El repartidor tiene pedidos en curso: no se puede cambiar su habilitación hasta que los termine"
    )
    lista = cliente.get("/operario/repartidores", headers=HEADERS_OPERARIO).json()
    assert lista[0]["peso_max_kg"] == 20  # no cambió


# --- Otros casos y permisos -----------------------------------------------------------------


@pytest.mark.parametrize("cambio", [{"peso_max_kg": 0}, {"alto_max_cm": -1}, {"largo_max_cm": None}])
def test_datos_invalidos(cliente: TestClient, db: Session, cambio: dict) -> None:
    repartidor = crear_repartidor(db)

    assert modificar(cliente, repartidor, NUEVA | cambio).status_code == 422


def test_repartidor_inexistente(cliente: TestClient) -> None:
    assert modificar(cliente, 999999).status_code == 404


def test_un_repartidor_no_puede_modificarla(cliente: TestClient, db: Session) -> None:
    repartidor = crear_repartidor(db)

    assert modificar(cliente, repartidor, headers=headers_de(repartidor)).status_code == 403


def test_sin_sesion_no_puede_modificarla(cliente: TestClient) -> None:
    assert cliente.put("/operario/repartidores/1/habilitacion", json=NUEVA).status_code == 401
