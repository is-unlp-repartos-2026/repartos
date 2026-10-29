"""HU-16 · Consultar pedidos asignados.

Criterios de aceptación:
  1. Con pedidos → los lista (origen, destino y estado).
  2. Sin pedidos → lista vacía (la app muestra el mensaje).
Además: solo los suyos, solo asignados y en camino (no los finales), ordenados por fecha de asignación,
nunca datos de más, y solo el repartidor puede consultarlos.
"""

from itertools import count

from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.orm import Session

from repartos.core.security import crear_token, hashear_codigo_acceso
from repartos.repositories import repartidores

URL = "/repartidor/pedidos"
HEADERS_OPERARIO = {"Authorization": f"Bearer {crear_token(1, rol='operario', minutos=30)}"}
_numeros = count(1)


def headers_de(repartidor_id: int) -> dict[str, str]:
    return {"Authorization": f"Bearer {crear_token(repartidor_id, rol='repartidor', minutos=30)}"}


def crear_repartidor(db: Session) -> int:
    n = next(_numeros)
    return repartidores.insertar(
        db,
        nombre=f"Repartidor {n}",
        dni=f"{47000000 + n}",
        correo=f"lista{n}@mail.com",
        peso_max_kg=20,
        alto_max_cm=50,
        ancho_max_cm=50,
        largo_max_cm=50,
        codigo_acceso_hash=hashear_codigo_acceso(f"LIS{n}"),
    )["id"]


def comenzar(cliente: TestClient, repartidor_id: int) -> None:
    cliente.post("/repartidor/jornada/comenzar", headers=headers_de(repartidor_id))


def registrar_pedido(cliente: TestClient, destino: str = "Calle 50 nro 456") -> int:
    datos = {
        "origen": "Almacén Don Pepe",
        "destino": destino,
        "receptor_nombre": "Ana Gómez",
        "receptor_dni": "28111222",
        "peso_kg": 5,
        "alto_cm": 30,
        "ancho_cm": 20,
        "largo_cm": 40,
    }
    return cliente.post("/operario/pedidos", json=datos, headers=HEADERS_OPERARIO).json()["id"]


def listar(cliente: TestClient, repartidor_id: int) -> list[dict]:
    respuesta = cliente.get(URL, headers=headers_de(repartidor_id))
    assert respuesta.status_code == 200
    return respuesta.json()


# --- Criterio de aceptación 1: con pedidos --------------------------------------------------


def test_lista_sus_pedidos_con_origen_destino_y_estado(cliente: TestClient, db: Session) -> None:
    repartidor = crear_repartidor(db)
    comenzar(cliente, repartidor)
    pedido = registrar_pedido(cliente)

    lista = listar(cliente, repartidor)

    assert len(lista) == 1
    assert lista[0]["id"] == pedido
    assert lista[0]["origen"] == "Almacén Don Pepe"
    assert lista[0]["destino"] == "Calle 50 nro 456"
    assert lista[0]["estado"] == "repartidor_asignado"
    # Solo lo necesario: ni el receptor ni su DNI aparecen en la lista.
    assert set(lista[0]) == {"id", "origen", "destino", "estado", "asignado_el"}


def test_incluye_los_en_camino_y_no_los_finales(cliente: TestClient, db: Session) -> None:
    repartidor = crear_repartidor(db)
    comenzar(cliente, repartidor)
    asignado, en_camino, entregado, fallido, cancelado = (registrar_pedido(cliente) for _ in range(5))
    for pedido in (en_camino, entregado, fallido):
        cliente.post(f"/repartidor/pedidos/{pedido}/retirar", headers=headers_de(repartidor))
    db.execute(text("UPDATE pedidos SET estado = 'entregado' WHERE id = :id"), {"id": entregado})
    cliente.post(
        f"/repartidor/pedidos/{fallido}/entrega-fallida",
        json={"motivo": "Destinatario ausente"},
        headers=headers_de(repartidor),
    )
    cliente.post(f"/operario/pedidos/{cancelado}/cancelar", headers=HEADERS_OPERARIO)

    lista = listar(cliente, repartidor)

    assert {(p["id"], p["estado"]) for p in lista} == {
        (asignado, "repartidor_asignado"),
        (en_camino, "en_camino"),
    }


def test_ordenados_por_fecha_de_asignacion(cliente: TestClient, db: Session) -> None:
    repartidor = crear_repartidor(db)
    comenzar(cliente, repartidor)
    primero = registrar_pedido(cliente)
    segundo = registrar_pedido(cliente)
    # El primero se reasigna más tarde (como si hubiera vuelto de otro repartidor): pasa al final.
    db.execute(
        text(
            "UPDATE cambios_estado SET fecha_hora = now() + interval '1 hour' "
            "WHERE pedido_id = :id AND estado = 'repartidor_asignado'"
        ),
        {"id": primero},
    )

    lista = listar(cliente, repartidor)

    assert [p["id"] for p in lista] == [segundo, primero]


def test_no_ve_pedidos_de_otros(cliente: TestClient, db: Session) -> None:
    yo = crear_repartidor(db)
    otro = crear_repartidor(db)
    comenzar(cliente, otro)
    registrar_pedido(cliente)  # va al otro (yo todavía no comencé)
    comenzar(cliente, yo)

    assert listar(cliente, yo) == []


# --- Criterio de aceptación 2: sin pedidos --------------------------------------------------


def test_sin_pedidos_devuelve_lista_vacia(cliente: TestClient, db: Session) -> None:
    repartidor = crear_repartidor(db)

    assert listar(cliente, repartidor) == []


# --- Permisos -------------------------------------------------------------------------------


def test_el_operario_no_puede_consultarla(cliente: TestClient) -> None:
    assert cliente.get(URL, headers=HEADERS_OPERARIO).status_code == 403


def test_sin_sesion_no_puede_consultarla(cliente: TestClient) -> None:
    assert cliente.get(URL).status_code == 401
