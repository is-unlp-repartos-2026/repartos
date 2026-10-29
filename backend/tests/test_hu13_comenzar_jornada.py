"""HU-13 · Comenzar jornada laboral.

Criterios de aceptación:
  1. Sin pedidos pendientes → queda activo.
  2. Con un pedido pendiente que puede llevar → queda activo y se le asigna.
Además: no se le asignan pendientes que no puede llevar ni pedidos que ya tienen repartidor, recibe los
nuevos pedidos que registra el operario, no puede comenzar dos veces y solo el repartidor puede hacerlo.
"""

from itertools import count

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.orm import Session

from repartos.core.security import crear_token, hashear_codigo_acceso
from repartos.repositories import repartidores

URL = "/repartidor/jornada/comenzar"
_numeros = count(1)


def crear_repartidor(db: Session, *, peso: float = 20, medida: float = 50) -> int:
    n = next(_numeros)
    fila = repartidores.insertar(
        db,
        nombre=f"Repartidor {n}",
        dni=f"{41000000 + n}",
        correo=f"jornada{n}@mail.com",
        peso_max_kg=peso,
        alto_max_cm=medida,
        ancho_max_cm=medida,
        largo_max_cm=medida,
        codigo_acceso_hash=hashear_codigo_acceso(f"JOR{n}"),
    )
    return fila["id"]


def headers_de(repartidor_id: int) -> dict[str, str]:
    return {"Authorization": f"Bearer {crear_token(repartidor_id, rol='repartidor', minutos=30)}"}


HEADERS_OPERARIO = {"Authorization": f"Bearer {crear_token(1, rol='operario', minutos=30)}"}


def registrar_pedido(cliente: TestClient, peso: float = 5) -> dict:
    """Registra un pedido como lo hace el operario (HU-04)."""
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


def pedido_en_base(db: Session, pedido_id: int) -> tuple:
    return db.execute(
        text("SELECT estado, repartidor_id FROM pedidos WHERE id = :id"), {"id": pedido_id}
    ).one()


def esta_activo(db: Session, repartidor_id: int) -> bool:
    return db.execute(
        text("SELECT activo FROM repartidores WHERE id = :id"), {"id": repartidor_id}
    ).scalar_one()


@pytest.fixture
def repartidor_id(db: Session) -> int:
    return crear_repartidor(db)


# --- Criterio de aceptación 1: sin pendientes -----------------------------------------------


def test_sin_pendientes_queda_activo(cliente: TestClient, db: Session, repartidor_id: int) -> None:
    respuesta = cliente.post(URL, headers=headers_de(repartidor_id))

    assert respuesta.status_code == 200
    assert respuesta.json() == {"activo": True, "pedidos_asignados": 0}
    assert esta_activo(db, repartidor_id)


# --- Criterio de aceptación 2: con un pendiente apto ----------------------------------------


def test_con_un_pendiente_apto_se_le_asigna(cliente: TestClient, db: Session, repartidor_id: int) -> None:
    pedido = registrar_pedido(cliente)
    assert pedido["estado"] == "registrado"  # todavía no había nadie activo

    respuesta = cliente.post(URL, headers=headers_de(repartidor_id))

    assert respuesta.json() == {"activo": True, "pedidos_asignados": 1}
    assert pedido_en_base(db, pedido["id"]) == ("repartidor_asignado", repartidor_id)
    detalle = db.execute(
        text("SELECT detalle FROM cambios_estado WHERE pedido_id = :id AND estado = 'repartidor_asignado'"),
        {"id": pedido["id"]},
    ).scalar_one()
    assert detalle == "Asignación al comenzar la jornada"


def test_recibe_todos_los_pendientes_que_puede_llevar(
    cliente: TestClient, db: Session, repartidor_id: int
) -> None:
    pedidos = [registrar_pedido(cliente) for _ in range(3)]

    respuesta = cliente.post(URL, headers=headers_de(repartidor_id))

    assert respuesta.json()["pedidos_asignados"] == 3
    for pedido in pedidos:
        assert pedido_en_base(db, pedido["id"]) == ("repartidor_asignado", repartidor_id)


# --- Otras reglas ---------------------------------------------------------------------------


def test_no_recibe_pendientes_que_no_puede_llevar(cliente: TestClient, db: Session, repartidor_id: int) -> None:
    pesado = registrar_pedido(cliente, peso=50)  # el repartidor lleva hasta 20 kg

    respuesta = cliente.post(URL, headers=headers_de(repartidor_id))

    assert respuesta.json()["pedidos_asignados"] == 0
    assert pedido_en_base(db, pesado["id"]) == ("registrado", None)


def test_no_toca_pedidos_que_ya_tienen_repartidor(cliente: TestClient, db: Session) -> None:
    otro = crear_repartidor(db)
    cliente.post(URL, headers=headers_de(otro))
    pedido_del_otro = registrar_pedido(cliente)
    nuevo = crear_repartidor(db)

    respuesta = cliente.post(URL, headers=headers_de(nuevo))

    assert respuesta.json()["pedidos_asignados"] == 0
    assert pedido_en_base(db, pedido_del_otro["id"]) == ("repartidor_asignado", otro)


def test_despues_de_comenzar_recibe_pedidos_nuevos(cliente: TestClient, repartidor_id: int) -> None:
    cliente.post(URL, headers=headers_de(repartidor_id))

    pedido = registrar_pedido(cliente)

    assert pedido["repartidor"]["id"] == repartidor_id


def test_no_puede_comenzar_dos_veces(cliente: TestClient, repartidor_id: int) -> None:
    cliente.post(URL, headers=headers_de(repartidor_id))

    respuesta = cliente.post(URL, headers=headers_de(repartidor_id))

    assert respuesta.status_code == 409
    assert respuesta.json()["detail"] == "Ya comenzaste tu jornada"


# --- Permisos -------------------------------------------------------------------------------


def test_deshabilitado_no_puede_comenzar(cliente: TestClient, db: Session, repartidor_id: int) -> None:
    db.execute(text("UPDATE repartidores SET habilitado = false WHERE id = :id"), {"id": repartidor_id})

    respuesta = cliente.post(URL, headers=headers_de(repartidor_id))

    assert respuesta.status_code == 403
    assert not esta_activo(db, repartidor_id)


def test_sin_sesion_no_puede_comenzar(cliente: TestClient) -> None:
    assert cliente.post(URL).status_code == 401


def test_el_operario_no_puede_comenzar_una_jornada(cliente: TestClient) -> None:
    assert cliente.post(URL, headers=HEADERS_OPERARIO).status_code == 403
