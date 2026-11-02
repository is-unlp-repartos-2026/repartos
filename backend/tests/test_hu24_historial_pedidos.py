"""HU-24 · Consultar historial de pedidos.

Criterios de aceptación:
  1. Filtrar por fechas y repartidor.
  2. Sin resultados → mensaje (el backend devuelve una lista vacía y el frontend muestra el mensaje).
Además: por defecto, los pedidos del día; filtro por estado; el día es de Argentina (no de UTC);
"desde" posterior a "hasta" no se permite; solo el operario.
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
    repartidor_id = repartidores.insertar(
        db,
        nombre=f"Repartidor {n}",
        dni=f"{61000000 + n}",
        correo=f"historial{n}@mail.com",
        peso_max_kg=20,
        alto_max_cm=50,
        ancho_max_cm=50,
        largo_max_cm=50,
        codigo_acceso_hash=hashear_codigo_acceso(f"HIS{n}"),
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


def registrado_el(db: Session, pedido_id: int, fecha_hora: str) -> None:
    """Cambia la fecha y hora de todo el historial del pedido (para simular que se registró otro día)."""
    db.execute(
        text("UPDATE cambios_estado SET fecha_hora = CAST(:fecha_hora AS TIMESTAMPTZ) WHERE pedido_id = :id"),
        {"fecha_hora": fecha_hora, "id": pedido_id},
    )


def historial(cliente: TestClient, **filtros):
    return cliente.get("/operario/pedidos", params=filtros, headers=HEADERS_OPERARIO)


def ids(respuesta) -> list[int]:
    return [p["id"] for p in respuesta.json()]


# --- Por defecto: los pedidos del día -------------------------------------------------------


def test_por_defecto_muestra_los_pedidos_de_hoy(cliente: TestClient, db: Session) -> None:
    de_hoy = registrar_pedido(cliente)
    de_otro_dia = registrar_pedido(cliente)
    registrado_el(db, de_otro_dia["id"], "2026-03-10 12:00-03")

    respuesta = historial(cliente)

    assert respuesta.status_code == 200
    assert ids(respuesta) == [de_hoy["id"]]
    pedido = respuesta.json()[0]
    assert pedido["codigo_seguimiento"] == de_hoy["codigo_seguimiento"]
    assert pedido["estado"] == "registrado"
    assert pedido["repartidor"] is None


# --- Criterio de aceptación 1: filtrar por fechas y repartidor ------------------------------


def test_filtra_por_fechas(cliente: TestClient, db: Session) -> None:
    antes = registrar_pedido(cliente)
    dentro_1 = registrar_pedido(cliente)
    dentro_2 = registrar_pedido(cliente)
    despues = registrar_pedido(cliente)
    registrado_el(db, antes["id"], "2026-03-09 12:00-03")
    registrado_el(db, dentro_1["id"], "2026-03-10 09:00-03")
    registrado_el(db, dentro_2["id"], "2026-03-12 18:00-03")
    registrado_el(db, despues["id"], "2026-03-13 12:00-03")

    respuesta = historial(cliente, desde="2026-03-10", hasta="2026-03-12")

    assert ids(respuesta) == [dentro_2["id"], dentro_1["id"]]  # del más nuevo al más viejo


def test_filtra_por_repartidor(cliente: TestClient, db: Session) -> None:
    juan = repartidor_activo(cliente, db)
    de_juan = registrar_pedido(cliente)
    repartidor_activo(cliente, db)
    de_otro = registrar_pedido(cliente)  # va al otro: es el que hace más que no recibe

    respuesta = historial(cliente, repartidor_id=juan)

    assert ids(respuesta) == [de_juan["id"]]
    assert respuesta.json()[0]["repartidor"] == {"id": juan, "nombre": de_juan["repartidor"]["nombre"]}
    assert de_otro["repartidor"]["id"] != juan


def test_filtra_por_fechas_y_repartidor_a_la_vez(cliente: TestClient, db: Session) -> None:
    juan = repartidor_activo(cliente, db)
    viejo = registrar_pedido(cliente)
    nuevo = registrar_pedido(cliente)
    registrado_el(db, viejo["id"], "2026-01-05 12:00-03")
    registrado_el(db, nuevo["id"], "2026-03-10 12:00-03")

    respuesta = historial(cliente, desde="2026-03-01", hasta="2026-03-31", repartidor_id=juan)

    assert ids(respuesta) == [nuevo["id"]]


def test_filtra_por_estado(cliente: TestClient, db: Session) -> None:
    repartidor_activo(cliente, db)
    asignado = registrar_pedido(cliente)
    cancelado = registrar_pedido(cliente)
    cliente.post(f"/operario/pedidos/{cancelado['id']}/cancelar", headers=HEADERS_OPERARIO)

    assert ids(historial(cliente, estado="cancelado")) == [cancelado["id"]]
    assert ids(historial(cliente, estado="repartidor_asignado")) == [asignado["id"]]


# --- Criterio de aceptación 2: sin resultados -----------------------------------------------


def test_sin_resultados_devuelve_lista_vacia(cliente: TestClient) -> None:
    registrar_pedido(cliente)

    respuesta = historial(cliente, desde="2020-01-01", hasta="2020-01-31")

    assert respuesta.status_code == 200
    assert respuesta.json() == []


# --- Reglas ---------------------------------------------------------------------------------


def test_el_dia_es_de_argentina_y_no_de_utc(cliente: TestClient, db: Session) -> None:
    """Las 23:30 del 10/3 en Argentina son las 2:30 del 11/3 en UTC: tiene que contar como del 10."""
    pedido = registrar_pedido(cliente)
    registrado_el(db, pedido["id"], "2026-03-10 23:30-03")

    assert ids(historial(cliente, desde="2026-03-10", hasta="2026-03-10")) == [pedido["id"]]
    assert ids(historial(cliente, desde="2026-03-11", hasta="2026-03-11")) == []


def test_desde_posterior_a_hasta_no_se_permite(cliente: TestClient) -> None:
    respuesta = historial(cliente, desde="2026-03-12", hasta="2026-03-10")

    assert respuesta.status_code == 422


def test_sin_sesion_de_operario_no_se_puede(cliente: TestClient, db: Session) -> None:
    repartidor_id = repartidor_activo(cliente, db)

    assert cliente.get("/operario/pedidos").status_code == 401
    assert cliente.get("/operario/pedidos", headers=headers_de(repartidor_id)).status_code == 403
