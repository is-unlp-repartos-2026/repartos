"""HU-14 · Terminar jornada laboral.

Criterios de aceptación:
  1. Sin pedidos en camino → queda inactivo y sus pedidos asignados se reasignan.
  2. Con un pedido en camino → no permite terminar e indica que termine sus entregas.
Además: si no hay otro apto el pedido vuelve a "registrado", el historial guarda el motivo, deja de recibir
pedidos nuevos, no puede terminar una jornada que no comenzó y solo el repartidor puede hacerlo.
"""

from itertools import count

from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.orm import Session

from repartos.core.security import crear_token, hashear_codigo_acceso
from repartos.repositories import repartidores

URL_COMENZAR = "/repartidor/jornada/comenzar"
URL_TERMINAR = "/repartidor/jornada/terminar"
HEADERS_OPERARIO = {"Authorization": f"Bearer {crear_token(1, rol='operario', minutos=30)}"}
_numeros = count(1)


def headers_de(repartidor_id: int) -> dict[str, str]:
    return {"Authorization": f"Bearer {crear_token(repartidor_id, rol='repartidor', minutos=30)}"}


def crear_repartidor(db: Session, *, peso: float = 20) -> int:
    n = next(_numeros)
    fila = repartidores.insertar(
        db,
        nombre=f"Repartidor {n}",
        dni=f"{42000000 + n}",
        correo=f"terminar{n}@mail.com",
        peso_max_kg=peso,
        alto_max_cm=50,
        ancho_max_cm=50,
        largo_max_cm=50,
        codigo_acceso_hash=hashear_codigo_acceso(f"TER{n}"),
    )
    return fila["id"]


def comenzar(cliente: TestClient, repartidor_id: int) -> None:
    assert cliente.post(URL_COMENZAR, headers=headers_de(repartidor_id)).status_code == 200


def terminar(cliente: TestClient, repartidor_id: int):
    return cliente.post(URL_TERMINAR, headers=headers_de(repartidor_id))


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


def pedido_en_base(db: Session, pedido_id: int) -> tuple:
    return db.execute(
        text("SELECT estado, repartidor_id FROM pedidos WHERE id = :id"), {"id": pedido_id}
    ).one()


def ultimo_cambio(db: Session, pedido_id: int) -> tuple:
    return db.execute(
        text(
            "SELECT estado, repartidor_id, detalle FROM cambios_estado "
            "WHERE pedido_id = :id ORDER BY id DESC LIMIT 1"
        ),
        {"id": pedido_id},
    ).one()


def esta_activo(db: Session, repartidor_id: int) -> bool:
    return db.execute(
        text("SELECT activo FROM repartidores WHERE id = :id"), {"id": repartidor_id}
    ).scalar_one()


def poner_en_camino(db: Session, pedido_id: int) -> None:
    # Mientras no exista HU-18 (Retirar pedido), se hace directo en la base.
    db.execute(text("UPDATE pedidos SET estado = 'en_camino' WHERE id = :id"), {"id": pedido_id})


# --- Criterio de aceptación 1: sin pedidos en camino ----------------------------------------


def test_sin_pedidos_queda_inactivo(cliente: TestClient, db: Session) -> None:
    repartidor = crear_repartidor(db)
    comenzar(cliente, repartidor)

    respuesta = terminar(cliente, repartidor)

    assert respuesta.status_code == 200
    assert respuesta.json() == {"activo": False, "pedidos_reasignados": 0, "pedidos_sin_repartidor": 0}
    assert not esta_activo(db, repartidor)


def test_sus_pedidos_asignados_pasan_a_otro_apto(cliente: TestClient, db: Session) -> None:
    se_va = crear_repartidor(db)
    comenzar(cliente, se_va)
    pedido = registrar_pedido(cliente)
    assert pedido["repartidor"]["id"] == se_va
    se_queda = crear_repartidor(db)
    comenzar(cliente, se_queda)

    respuesta = terminar(cliente, se_va)

    assert respuesta.json()["pedidos_reasignados"] == 1
    assert pedido_en_base(db, pedido["id"]) == ("repartidor_asignado", se_queda)
    assert ultimo_cambio(db, pedido["id"]) == (
        "repartidor_asignado",
        se_queda,
        "Reasignado: el repartidor terminó su jornada",
    )


def test_sin_otro_apto_el_pedido_vuelve_a_registrado(cliente: TestClient, db: Session) -> None:
    se_va = crear_repartidor(db)
    comenzar(cliente, se_va)
    pedido = registrar_pedido(cliente)
    chico = crear_repartidor(db, peso=1)  # está activo, pero no puede llevar 5 kg
    comenzar(cliente, chico)

    respuesta = terminar(cliente, se_va)

    assert respuesta.json() == {"activo": False, "pedidos_reasignados": 0, "pedidos_sin_repartidor": 1}
    assert pedido_en_base(db, pedido["id"]) == ("registrado", None)
    assert ultimo_cambio(db, pedido["id"]) == (
        "registrado",
        None,
        "Sin otro repartidor apto: el repartidor terminó su jornada",
    )


def test_despues_de_terminar_no_recibe_pedidos_nuevos(cliente: TestClient, db: Session) -> None:
    repartidor = crear_repartidor(db)
    comenzar(cliente, repartidor)
    terminar(cliente, repartidor)

    pedido = registrar_pedido(cliente)

    assert pedido["estado"] == "registrado"


# --- Criterio de aceptación 2: con un pedido en camino --------------------------------------


def test_con_pedido_en_camino_no_puede_terminar(cliente: TestClient, db: Session) -> None:
    repartidor = crear_repartidor(db)
    comenzar(cliente, repartidor)
    en_camino = registrar_pedido(cliente)
    asignado = registrar_pedido(cliente)
    poner_en_camino(db, en_camino["id"])

    respuesta = terminar(cliente, repartidor)

    assert respuesta.status_code == 409
    assert respuesta.json()["detail"] == "Tenés pedidos en camino: terminá tus entregas antes de terminar la jornada"
    # No cambió nada: sigue activo y conserva el pedido asignado.
    assert esta_activo(db, repartidor)
    assert pedido_en_base(db, asignado["id"]) == ("repartidor_asignado", repartidor)


# --- Otras reglas y permisos ----------------------------------------------------------------


def test_no_puede_terminar_sin_haber_comenzado(cliente: TestClient, db: Session) -> None:
    repartidor = crear_repartidor(db)

    respuesta = terminar(cliente, repartidor)

    assert respuesta.status_code == 409
    assert respuesta.json()["detail"] == "No comenzaste tu jornada"


def test_puede_volver_a_comenzar_despues_de_terminar(cliente: TestClient, db: Session) -> None:
    repartidor = crear_repartidor(db)
    comenzar(cliente, repartidor)
    terminar(cliente, repartidor)

    comenzar(cliente, repartidor)

    assert esta_activo(db, repartidor)


def test_sin_sesion_no_puede_terminar(cliente: TestClient) -> None:
    assert cliente.post(URL_TERMINAR).status_code == 401


def test_el_operario_no_puede_terminar_una_jornada(cliente: TestClient) -> None:
    assert cliente.post(URL_TERMINAR, headers=HEADERS_OPERARIO).status_code == 403
