"""HU-04 · Registrar pedido (incluye la regla de asignación automática).

Criterios de aceptación:
  1. Con un repartidor apto → "Repartidor asignado" y se muestra el código de seguimiento.
  2. Sin repartidor apto → "Registrado", se muestra el código y un aviso.
Además, se prueba la regla de asignación (activo, habilitado, peso y medidas; entre varios, el que hace
más tiempo que no recibe un pedido), el historial, los datos inválidos y que solo el operario puede registrar.
"""

from itertools import count

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.orm import Session

from repartos.core.security import LARGO_CODIGO_SEGUIMIENTO, crear_token, hashear_codigo_acceso
from repartos.repositories import repartidores

URL = "/operario/pedidos"
_numeros = count(1)


def datos_pedido(**cambios) -> dict:
    datos = {
        "origen": "Almacén Don Pepe, calle 7 nro 123",
        "destino": "Calle 50 nro 456, depto 2",
        "receptor_nombre": "Ana Gómez",
        "receptor_dni": "28111222",
        "peso_kg": 5,
        "alto_cm": 30,
        "ancho_cm": 20,
        "largo_cm": 40,
    }
    return datos | cambios


def crear_repartidor(
    db: Session, *, activo: bool = True, habilitado: bool = True, peso: float = 20, medida: float = 50
) -> int:
    n = next(_numeros)
    fila = repartidores.insertar(
        db,
        nombre=f"Repartidor {n}",
        dni=f"{40000000 + n}",
        correo=f"repartidor{n}@mail.com",
        peso_max_kg=peso,
        alto_max_cm=medida,
        ancho_max_cm=medida,
        largo_max_cm=medida,
        codigo_acceso_hash=hashear_codigo_acceso(f"COD{n}"),
    )
    db.execute(
        text("UPDATE repartidores SET activo = :activo, habilitado = :habilitado WHERE id = :id"),
        {"activo": activo, "habilitado": habilitado, "id": fila["id"]},
    )
    return fila["id"]


def historial(db: Session, pedido_id: int) -> list[tuple]:
    filas = db.execute(
        text("SELECT estado, repartidor_id FROM cambios_estado WHERE pedido_id = :id ORDER BY id"),
        {"id": pedido_id},
    )
    return [tuple(f) for f in filas]


@pytest.fixture
def headers() -> dict[str, str]:
    return {"Authorization": f"Bearer {crear_token(1, rol='operario', minutos=30)}"}


def registrar(cliente: TestClient, headers: dict[str, str], **cambios):
    return cliente.post(URL, json=datos_pedido(**cambios), headers=headers)


# --- Criterio de aceptación 1: con repartidor apto ------------------------------------------


def test_con_repartidor_apto_queda_asignado(cliente: TestClient, headers: dict, db: Session) -> None:
    repartidor_id = crear_repartidor(db)

    respuesta = registrar(cliente, headers)

    assert respuesta.status_code == 201
    cuerpo = respuesta.json()
    assert cuerpo["estado"] == "repartidor_asignado"
    assert cuerpo["repartidor"]["id"] == repartidor_id
    assert len(cuerpo["codigo_seguimiento"]) == LARGO_CODIGO_SEGUIMIENTO
    assert cuerpo["aviso"] is None
    assert historial(db, cuerpo["id"]) == [("registrado", None), ("repartidor_asignado", repartidor_id)]


def test_la_asignacion_queda_guardada(cliente: TestClient, headers: dict, db: Session) -> None:
    repartidor_id = crear_repartidor(db)

    pedido_id = registrar(cliente, headers).json()["id"]

    estado, asignado = db.execute(
        text("SELECT estado, repartidor_id FROM pedidos WHERE id = :id"), {"id": pedido_id}
    ).one()
    assert (estado, asignado) == ("repartidor_asignado", repartidor_id)
    ultima = db.execute(
        text("SELECT ultima_asignacion FROM repartidores WHERE id = :id"), {"id": repartidor_id}
    ).scalar_one()
    assert ultima is not None


# --- Criterio de aceptación 2: sin repartidor apto ------------------------------------------


def test_sin_repartidores_queda_registrado_con_aviso(cliente: TestClient, headers: dict, db: Session) -> None:
    respuesta = registrar(cliente, headers)

    assert respuesta.status_code == 201
    cuerpo = respuesta.json()
    assert cuerpo["estado"] == "registrado"
    assert cuerpo["repartidor"] is None
    assert len(cuerpo["codigo_seguimiento"]) == LARGO_CODIGO_SEGUIMIENTO
    assert cuerpo["aviso"]
    assert historial(db, cuerpo["id"]) == [("registrado", None)]


@pytest.mark.parametrize(
    "repartidor",
    [
        {"activo": False},
        {"habilitado": False},
        {"peso": 4.9},  # el pedido pesa 5 kg
        {"medida": 39},  # el pedido mide 40 cm de largo
    ],
    ids=["inactivo", "deshabilitado", "peso insuficiente", "medida insuficiente"],
)
def test_repartidor_no_apto_no_recibe_el_pedido(
    cliente: TestClient, headers: dict, db: Session, repartidor: dict
) -> None:
    crear_repartidor(db, **repartidor)

    cuerpo = registrar(cliente, headers).json()

    assert cuerpo["estado"] == "registrado"
    assert cuerpo["repartidor"] is None


# --- Regla de asignación --------------------------------------------------------------------


def test_peso_y_medidas_justas_alcanzan(cliente: TestClient, headers: dict, db: Session) -> None:
    repartidor_id = crear_repartidor(db, peso=5, medida=40)

    cuerpo = registrar(cliente, headers, alto_cm=40, ancho_cm=40, largo_cm=40).json()

    assert cuerpo["repartidor"]["id"] == repartidor_id


def test_elige_al_que_hace_mas_tiempo_que_no_recibe(cliente: TestClient, headers: dict, db: Session) -> None:
    reciente = crear_repartidor(db)
    antiguo = crear_repartidor(db)
    db.execute(text("UPDATE repartidores SET ultima_asignacion = now() WHERE id = :id"), {"id": reciente})
    db.execute(
        text("UPDATE repartidores SET ultima_asignacion = now() - interval '2 hours' WHERE id = :id"),
        {"id": antiguo},
    )

    cuerpo = registrar(cliente, headers).json()

    assert cuerpo["repartidor"]["id"] == antiguo


def test_el_que_nunca_recibio_va_primero(cliente: TestClient, headers: dict, db: Session) -> None:
    con_pedidos = crear_repartidor(db)
    db.execute(
        text("UPDATE repartidores SET ultima_asignacion = now() - interval '1 day' WHERE id = :id"),
        {"id": con_pedidos},
    )
    sin_pedidos = crear_repartidor(db)

    cuerpo = registrar(cliente, headers).json()

    assert cuerpo["repartidor"]["id"] == sin_pedidos


def test_los_pedidos_se_reparten_entre_los_aptos(cliente: TestClient, headers: dict, db: Session) -> None:
    primero = crear_repartidor(db)
    segundo = crear_repartidor(db)

    asignados = [registrar(cliente, headers).json()["repartidor"]["id"] for _ in range(2)]

    assert sorted(asignados) == sorted([primero, segundo])


def test_cada_pedido_tiene_un_codigo_distinto(cliente: TestClient, headers: dict) -> None:
    codigos = {registrar(cliente, headers).json()["codigo_seguimiento"] for _ in range(5)}

    assert len(codigos) == 5


# --- Datos inválidos y permisos -------------------------------------------------------------


@pytest.mark.parametrize(
    "cambio",
    [
        {"origen": ""},
        {"destino": ""},
        {"receptor_nombre": ""},
        {"receptor_dni": "28.111.222"},
        {"peso_kg": 0},
        {"largo_cm": -1},
    ],
)
def test_datos_invalidos_no_registran(cliente: TestClient, headers: dict, db: Session, cambio: dict) -> None:
    respuesta = registrar(cliente, headers, **cambio)

    assert respuesta.status_code == 422
    assert db.execute(text("SELECT count(*) FROM pedidos")).scalar_one() == 0


def test_sin_sesion_no_registra(cliente: TestClient) -> None:
    assert cliente.post(URL, json=datos_pedido()).status_code == 401


def test_un_repartidor_no_registra(cliente: TestClient) -> None:
    headers = {"Authorization": f"Bearer {crear_token(1, rol='repartidor', minutos=30)}"}

    assert cliente.post(URL, json=datos_pedido(), headers=headers).status_code == 403
