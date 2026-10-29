"""HU-18 · Retirar pedido.

Criterio de aceptación:
  1. Retirar → el pedido pasa a "En camino" (con fecha y hora en el historial).
Además: solo desde "Repartidor asignado", solo pedidos propios y solo el repartidor puede hacerlo.
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


def repartidor_activo(cliente: TestClient, db: Session) -> int:
    n = next(_numeros)
    fila = repartidores.insertar(
        db,
        nombre=f"Repartidor {n}",
        dni=f"{43000000 + n}",
        correo=f"retirar{n}@mail.com",
        peso_max_kg=20,
        alto_max_cm=50,
        ancho_max_cm=50,
        largo_max_cm=50,
        codigo_acceso_hash=hashear_codigo_acceso(f"RET{n}"),
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


def retirar(cliente: TestClient, pedido_id: int, repartidor_id: int):
    return cliente.post(f"/repartidor/pedidos/{pedido_id}/retirar", headers=headers_de(repartidor_id))


def estado_en_base(db: Session, pedido_id: int) -> str:
    return db.execute(text("SELECT estado FROM pedidos WHERE id = :id"), {"id": pedido_id}).scalar_one()


# --- Criterio de aceptación 1: retirar ------------------------------------------------------


def test_retirar_pasa_a_en_camino(cliente: TestClient, db: Session) -> None:
    repartidor = repartidor_activo(cliente, db)
    pedido = registrar_pedido(cliente)

    respuesta = retirar(cliente, pedido["id"], repartidor)

    assert respuesta.status_code == 200
    assert respuesta.json() == {"id": pedido["id"], "estado": "en_camino"}
    assert estado_en_base(db, pedido["id"]) == "en_camino"
    cambio = db.execute(
        text(
            "SELECT repartidor_id, fecha_hora FROM cambios_estado "
            "WHERE pedido_id = :id AND estado = 'en_camino'"
        ),
        {"id": pedido["id"]},
    ).one()
    assert cambio.repartidor_id == repartidor
    assert cambio.fecha_hora is not None


# --- Otras reglas ---------------------------------------------------------------------------


def test_no_se_puede_retirar_dos_veces(cliente: TestClient, db: Session) -> None:
    repartidor = repartidor_activo(cliente, db)
    pedido = registrar_pedido(cliente)
    retirar(cliente, pedido["id"], repartidor)

    respuesta = retirar(cliente, pedido["id"], repartidor)

    assert respuesta.status_code == 409
    assert respuesta.json()["detail"] == "Solo se puede retirar un pedido con repartidor asignado"


def test_no_puede_retirar_un_pedido_de_otro(cliente: TestClient, db: Session) -> None:
    dueno = repartidor_activo(cliente, db)
    pedido = registrar_pedido(cliente)
    otro = repartidor_activo(cliente, db)

    respuesta = retirar(cliente, pedido["id"], otro)

    assert respuesta.status_code == 404
    assert estado_en_base(db, pedido["id"]) == "repartidor_asignado"
    assert dueno != otro


def test_pedido_inexistente(cliente: TestClient, db: Session) -> None:
    repartidor = repartidor_activo(cliente, db)

    assert retirar(cliente, 999999, repartidor).status_code == 404


def test_el_operario_no_puede_retirar(cliente: TestClient, db: Session) -> None:
    repartidor_activo(cliente, db)
    pedido = registrar_pedido(cliente)

    respuesta = cliente.post(f"/repartidor/pedidos/{pedido['id']}/retirar", headers=HEADERS_OPERARIO)

    assert respuesta.status_code == 403


def test_sin_sesion_no_puede_retirar(cliente: TestClient) -> None:
    assert cliente.post("/repartidor/pedidos/1/retirar").status_code == 401
