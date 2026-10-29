"""HU-17 · Consultar detalle de pedido asignado.

Criterio de aceptación:
  1. Muestra todos los datos: origen, destino, nombre y DNI de quien recibe, peso y dimensiones.
Además: nunca el contenido ni datos internos, solo pedidos propios y en curso, solo el repartidor.
"""

from itertools import count

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.orm import Session

from repartos.core.security import crear_token, hashear_codigo_acceso
from repartos.repositories import repartidores

HEADERS_OPERARIO = {"Authorization": f"Bearer {crear_token(1, rol='operario', minutos=30)}"}
DATOS_PEDIDO = {
    "origen": "Almacén Don Pepe",
    "destino": "Calle 50 nro 456",
    "receptor_nombre": "Ana Gómez",
    "receptor_dni": "28111222",
    "peso_kg": 5.5,
    "alto_cm": 30,
    "ancho_cm": 20,
    "largo_cm": 40,
}
_numeros = count(1)


def headers_de(repartidor_id: int) -> dict[str, str]:
    return {"Authorization": f"Bearer {crear_token(repartidor_id, rol='repartidor', minutos=30)}"}


def repartidor_activo(cliente: TestClient, db: Session) -> int:
    n = next(_numeros)
    repartidor_id = repartidores.insertar(
        db,
        nombre=f"Repartidor {n}",
        dni=f"{48000000 + n}",
        correo=f"detalle{n}@mail.com",
        peso_max_kg=20,
        alto_max_cm=50,
        ancho_max_cm=50,
        largo_max_cm=50,
        codigo_acceso_hash=hashear_codigo_acceso(f"DET{n}"),
    )["id"]
    cliente.post("/repartidor/jornada/comenzar", headers=headers_de(repartidor_id))
    return repartidor_id


def registrar_pedido(cliente: TestClient) -> int:
    return cliente.post("/operario/pedidos", json=DATOS_PEDIDO, headers=HEADERS_OPERARIO).json()["id"]


def detalle(cliente: TestClient, pedido_id: int, repartidor_id: int):
    return cliente.get(f"/repartidor/pedidos/{pedido_id}", headers=headers_de(repartidor_id))


# --- Criterio de aceptación 1: muestra todos los datos --------------------------------------


def test_muestra_todos_los_datos(cliente: TestClient, db: Session) -> None:
    repartidor = repartidor_activo(cliente, db)
    pedido = registrar_pedido(cliente)

    respuesta = detalle(cliente, pedido, repartidor)

    assert respuesta.status_code == 200
    assert respuesta.json() == DATOS_PEDIDO | {"id": pedido, "estado": "repartidor_asignado"}


def test_tambien_cuando_esta_en_camino(cliente: TestClient, db: Session) -> None:
    repartidor = repartidor_activo(cliente, db)
    pedido = registrar_pedido(cliente)
    cliente.post(f"/repartidor/pedidos/{pedido}/retirar", headers=headers_de(repartidor))

    assert detalle(cliente, pedido, repartidor).json()["estado"] == "en_camino"


# --- Pertenencia y estados ------------------------------------------------------------------


def test_no_ve_el_detalle_de_un_pedido_de_otro(cliente: TestClient, db: Session) -> None:
    repartidor_activo(cliente, db)
    pedido = registrar_pedido(cliente)
    otro = repartidor_activo(cliente, db)

    respuesta = detalle(cliente, pedido, otro)

    assert respuesta.status_code == 404
    assert respuesta.json()["detail"] == "Pedido no encontrado"


@pytest.mark.parametrize("estado", ["entregado", "entrega_fallida", "cancelado"])
def test_no_ve_el_detalle_de_pedidos_terminados(cliente: TestClient, db: Session, estado: str) -> None:
    repartidor = repartidor_activo(cliente, db)
    pedido = registrar_pedido(cliente)
    db.execute(text("UPDATE pedidos SET estado = :estado WHERE id = :id"), {"estado": estado, "id": pedido})

    assert detalle(cliente, pedido, repartidor).status_code == 404


def test_pedido_inexistente(cliente: TestClient, db: Session) -> None:
    repartidor = repartidor_activo(cliente, db)

    assert detalle(cliente, 999999, repartidor).status_code == 404


# --- Permisos -------------------------------------------------------------------------------


def test_el_operario_no_usa_este_endpoint(cliente: TestClient) -> None:
    assert cliente.get("/repartidor/pedidos/1", headers=HEADERS_OPERARIO).status_code == 403


def test_sin_sesion_no_puede_consultarlo(cliente: TestClient) -> None:
    assert cliente.get("/repartidor/pedidos/1").status_code == 401
