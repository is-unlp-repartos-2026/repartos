"""HU-19 · Rechazar pedido asignado.

Criterios de aceptación:
  1. Hay otro apto → se le asigna y desaparece de la lista de quien rechazó.
  2. No hay otro apto → "Registrado" y el operario lo ve en el tablero.
Además: el rechazo queda en el historial, nunca vuelve a quien lo rechazó, solo en "Repartidor asignado"
(antes de retirarlo) y solo pedidos propios.
"""

from itertools import count

from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.orm import Session

from repartos.core.security import crear_token, hashear_codigo_acceso
from repartos.repositories import repartidores

HEADERS_OPERARIO = {"Authorization": f"Bearer {crear_token(1, rol='operario', minutos=30)}"}
_numeros = count(1)


def headers_de(repartidor_id: int) -> dict[str, str]:
    return {"Authorization": f"Bearer {crear_token(repartidor_id, rol='repartidor', minutos=30)}"}


def repartidor_activo(cliente: TestClient, db: Session, peso: float = 20, nombre: str | None = None) -> int:
    n = next(_numeros)
    repartidor_id = repartidores.insertar(
        db,
        nombre=nombre or f"Repartidor {n}",
        dni=f"{62000000 + n}",
        correo=f"rechazar{n}@mail.com",
        peso_max_kg=peso,
        alto_max_cm=50,
        ancho_max_cm=50,
        largo_max_cm=50,
        codigo_acceso_hash=hashear_codigo_acceso(f"REC{n}"),
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


def rechazar(cliente: TestClient, pedido_id: int, repartidor_id: int):
    return cliente.post(f"/repartidor/pedidos/{pedido_id}/rechazar", headers=headers_de(repartidor_id))


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
    juan = repartidor_activo(cliente, db, nombre="Juan Pérez")
    pedido = registrar_pedido(cliente)
    otro = repartidor_activo(cliente, db)

    respuesta = rechazar(cliente, pedido["id"], juan)

    assert respuesta.status_code == 200
    assert respuesta.json() == {"id": pedido["id"], "estado": "repartidor_asignado"}
    assert pedido_en_base(db, pedido["id"]) == ("repartidor_asignado", otro)


def test_desaparece_de_la_lista_de_quien_rechazo(cliente: TestClient, db: Session) -> None:
    juan = repartidor_activo(cliente, db)
    pedido = registrar_pedido(cliente)
    otro = repartidor_activo(cliente, db)

    rechazar(cliente, pedido["id"], juan)

    assert cliente.get("/repartidor/pedidos", headers=headers_de(juan)).json() == []
    assert [p["id"] for p in cliente.get("/repartidor/pedidos", headers=headers_de(otro)).json()] == [pedido["id"]]


# --- Criterio de aceptación 2: no hay otro apto ---------------------------------------------


def test_sin_otro_apto_queda_registrado_y_aparece_en_el_tablero(cliente: TestClient, db: Session) -> None:
    juan = repartidor_activo(cliente, db)
    pedido = registrar_pedido(cliente)
    repartidor_activo(cliente, db, peso=1)  # activo, pero no puede llevar 5 kg

    respuesta = rechazar(cliente, pedido["id"], juan)

    assert respuesta.status_code == 200
    assert respuesta.json()["estado"] == "registrado"
    assert pedido_en_base(db, pedido["id"]) == ("registrado", None)
    tablero = cliente.get("/operario/tablero", headers=HEADERS_OPERARIO).json()
    assert [p["id"] for p in tablero["registrado"]] == [pedido["id"]]


# --- Reglas ---------------------------------------------------------------------------------


def test_el_rechazo_queda_en_el_historial(cliente: TestClient, db: Session) -> None:
    juan = repartidor_activo(cliente, db, nombre="Juan Pérez")
    pedido = registrar_pedido(cliente)
    repartidor_activo(cliente, db)

    rechazar(cliente, pedido["id"], juan)

    assert ultimo_detalle(db, pedido["id"]) == "Reasignado: Juan Pérez rechazó el pedido"


def test_nunca_vuelve_a_quien_lo_rechazo(cliente: TestClient, db: Session) -> None:
    """Aunque sea el único repartidor apto, no se le vuelve a asignar."""
    juan = repartidor_activo(cliente, db, nombre="Juan Pérez")
    pedido = registrar_pedido(cliente)

    rechazar(cliente, pedido["id"], juan)

    assert pedido_en_base(db, pedido["id"]) == ("registrado", None)
    assert ultimo_detalle(db, pedido["id"]) == "Sin otro repartidor apto: Juan Pérez rechazó el pedido"


def test_no_se_puede_rechazar_un_pedido_ya_retirado(cliente: TestClient, db: Session) -> None:
    juan = repartidor_activo(cliente, db)
    pedido = registrar_pedido(cliente)
    cliente.post(f"/repartidor/pedidos/{pedido['id']}/retirar", headers=headers_de(juan))

    respuesta = rechazar(cliente, pedido["id"], juan)

    assert respuesta.status_code == 409
    assert pedido_en_base(db, pedido["id"]) == ("en_camino", juan)


def test_no_se_puede_rechazar_un_pedido_de_otro(cliente: TestClient, db: Session) -> None:
    juan = repartidor_activo(cliente, db)
    pedido = registrar_pedido(cliente)
    otro = repartidor_activo(cliente, db)

    respuesta = rechazar(cliente, pedido["id"], otro)

    assert respuesta.status_code == 404
    assert pedido_en_base(db, pedido["id"]) == ("repartidor_asignado", juan)


def test_sin_sesion_de_repartidor_no_se_puede(cliente: TestClient, db: Session) -> None:
    repartidor_activo(cliente, db)
    pedido = registrar_pedido(cliente)

    assert cliente.post(f"/repartidor/pedidos/{pedido['id']}/rechazar").status_code == 401
    assert (
        cliente.post(f"/repartidor/pedidos/{pedido['id']}/rechazar", headers=HEADERS_OPERARIO).status_code == 403
    )
