"""HU-05 · Modificar pedido.

Criterios de aceptación:
  1. Corregir el destino → se guarda y queda en el historial.
  2. Subir el peso por encima de lo que puede llevar el repartidor → se reasigna.
Además: solo hasta "Repartidor asignado" inclusive; si cambian peso o medidas se reevalúa la asignación
(sin otro apto → "Registrado" con aviso; un pedido sin repartidor puede conseguir uno); si el repartidor
sigue pudiendo llevarlo, no cambia; la corrección no cuenta como cambio de estado (tablero, app del
repartidor, cliente final); solo el operario.
"""

from itertools import count

from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.orm import Session

from repartos.core.security import crear_token, hashear_codigo_acceso
from repartos.repositories import repartidores

HEADERS_OPERARIO = {"Authorization": f"Bearer {crear_token(1, rol='operario', minutos=30)}"}
DATOS = {
    "origen": "Almacén Don Pepe",
    "destino": "Calle 50 nro 456",
    "receptor_nombre": "Ana Gómez",
    "receptor_dni": "28111222",
    "peso_kg": 5,
    "alto_cm": 30,
    "ancho_cm": 20,
    "largo_cm": 40,
}
_numeros = count(1)


def headers_de(repartidor_id: int) -> dict[str, str]:
    return {"Authorization": f"Bearer {crear_token(repartidor_id, rol='repartidor', minutos=30)}"}


def repartidor_activo(cliente: TestClient, db: Session, peso: float = 20, nombre: str | None = None) -> int:
    n = next(_numeros)
    repartidor_id = repartidores.insertar(
        db,
        nombre=nombre or f"Repartidor {n}",
        dni=f"{63000000 + n}",
        correo=f"modificar{n}@mail.com",
        peso_max_kg=peso,
        alto_max_cm=50,
        ancho_max_cm=50,
        largo_max_cm=50,
        codigo_acceso_hash=hashear_codigo_acceso(f"MOD{n}"),
    )["id"]
    cliente.post("/repartidor/jornada/comenzar", headers=headers_de(repartidor_id))
    return repartidor_id


def registrar_pedido(cliente: TestClient, **cambios) -> dict:
    return cliente.post("/operario/pedidos", json=DATOS | cambios, headers=HEADERS_OPERARIO).json()


def modificar(cliente: TestClient, pedido_id: int, headers: dict = HEADERS_OPERARIO, **cambios):
    return cliente.put(f"/operario/pedidos/{pedido_id}", json=DATOS | cambios, headers=headers)


def pedido_en_base(db: Session, pedido_id: int) -> dict:
    return dict(
        db.execute(
            text("SELECT destino, peso_kg, estado, repartidor_id FROM pedidos WHERE id = :id"), {"id": pedido_id}
        ).mappings().one()
    )


def detalle(cliente: TestClient, pedido_id: int) -> dict:
    return cliente.get(f"/operario/pedidos/{pedido_id}", headers=HEADERS_OPERARIO).json()


# --- Criterio de aceptación 1: corregir el destino ------------------------------------------


def test_corregir_destino_se_guarda(cliente: TestClient, db: Session) -> None:
    juan = repartidor_activo(cliente, db)
    pedido = registrar_pedido(cliente)

    respuesta = modificar(cliente, pedido["id"], destino="Calle 7 nro 1234")

    assert respuesta.status_code == 200
    assert respuesta.json()["estado"] == "repartidor_asignado"
    assert respuesta.json()["repartidor"]["id"] == juan
    assert respuesta.json()["aviso"] is None
    assert pedido_en_base(db, pedido["id"])["destino"] == "Calle 7 nro 1234"


def test_la_correccion_queda_en_el_historial(cliente: TestClient, db: Session) -> None:
    juan = repartidor_activo(cliente, db, nombre="Juan Pérez")
    pedido = registrar_pedido(cliente)

    modificar(cliente, pedido["id"], destino="Calle 7 nro 1234")

    ultimo = detalle(cliente, pedido["id"])["historial"][-1]
    assert ultimo["modificacion"] is True
    assert ultimo["detalle"] == "Datos modificados: destino"
    assert ultimo["estado"] == "repartidor_asignado"  # el estado que tenía: no cambió
    assert ultimo["repartidor"] == {"id": juan, "nombre": "Juan Pérez"}


def test_el_historial_nombra_todos_los_datos_corregidos(cliente: TestClient) -> None:
    pedido = registrar_pedido(cliente)

    modificar(cliente, pedido["id"], destino="Calle 7 nro 1234", receptor_dni="30111222")

    assert detalle(cliente, pedido["id"])["historial"][-1]["detalle"] == (
        "Datos modificados: destino, DNI de quien recibe"
    )


# --- Criterio de aceptación 2: subir el peso por encima del repartidor ----------------------


def test_subir_el_peso_por_encima_del_repartidor_lo_reasigna(cliente: TestClient, db: Session) -> None:
    liviano = repartidor_activo(cliente, db, peso=10)
    pedido = registrar_pedido(cliente)
    pesado = repartidor_activo(cliente, db, peso=50)

    respuesta = modificar(cliente, pedido["id"], peso_kg=30)

    assert respuesta.status_code == 200
    assert respuesta.json()["estado"] == "repartidor_asignado"
    assert respuesta.json()["repartidor"]["id"] == pesado
    assert pedido_en_base(db, pedido["id"])["repartidor_id"] == pesado
    assert liviano != pesado
    assert cliente.get("/repartidor/pedidos", headers=headers_de(liviano)).json() == []


def test_sin_otro_apto_queda_registrado_con_aviso(cliente: TestClient, db: Session) -> None:
    repartidor_activo(cliente, db, peso=10)
    pedido = registrar_pedido(cliente)

    respuesta = modificar(cliente, pedido["id"], peso_kg=30)

    assert respuesta.json()["estado"] == "registrado"
    assert respuesta.json()["repartidor"] is None
    assert respuesta.json()["aviso"]
    assert pedido_en_base(db, pedido["id"])["estado"] == "registrado"


def test_si_el_repartidor_sigue_pudiendo_llevarlo_no_cambia(cliente: TestClient, db: Session) -> None:
    juan = repartidor_activo(cliente, db, peso=20)
    pedido = registrar_pedido(cliente)
    repartidor_activo(cliente, db, peso=20)

    respuesta = modificar(cliente, pedido["id"], peso_kg=15)

    assert respuesta.json()["repartidor"]["id"] == juan


def test_un_pedido_sin_repartidor_consigue_uno_si_ahora_entra(cliente: TestClient, db: Session) -> None:
    pedido = registrar_pedido(cliente, peso_kg=30)  # nadie puede llevar 30 kg
    juan = repartidor_activo(cliente, db, peso=10)  # comienza la jornada, pero 30 kg no le entran

    respuesta = modificar(cliente, pedido["id"], peso_kg=8)

    assert respuesta.json()["estado"] == "repartidor_asignado"
    assert respuesta.json()["repartidor"]["id"] == juan


# --- Reglas ---------------------------------------------------------------------------------


def test_no_se_puede_modificar_un_pedido_en_camino(cliente: TestClient, db: Session) -> None:
    juan = repartidor_activo(cliente, db)
    pedido = registrar_pedido(cliente)
    cliente.post(f"/repartidor/pedidos/{pedido['id']}/retirar", headers=headers_de(juan))

    respuesta = modificar(cliente, pedido["id"], destino="Calle 7 nro 1234")

    assert respuesta.status_code == 409
    assert pedido_en_base(db, pedido["id"])["destino"] == DATOS["destino"]


def test_no_se_puede_modificar_un_pedido_cancelado(cliente: TestClient) -> None:
    pedido = registrar_pedido(cliente)
    cliente.post(f"/operario/pedidos/{pedido['id']}/cancelar", headers=HEADERS_OPERARIO)

    assert modificar(cliente, pedido["id"], destino="Calle 7 nro 1234").status_code == 409


def test_sin_cambios_no_agrega_nada_al_historial(cliente: TestClient) -> None:
    pedido = registrar_pedido(cliente)
    antes = len(detalle(cliente, pedido["id"])["historial"])

    respuesta = modificar(cliente, pedido["id"])

    assert respuesta.status_code == 200
    assert len(detalle(cliente, pedido["id"])["historial"]) == antes


def test_la_correccion_no_la_ve_el_cliente_final(cliente: TestClient) -> None:
    pedido = registrar_pedido(cliente)

    modificar(cliente, pedido["id"], destino="Calle 7 nro 1234")

    seguimiento = cliente.get(f"/seguimiento/{pedido['codigo_seguimiento']}").json()
    assert [c["estado"] for c in seguimiento["historial"]] == ["registrado"]


def test_la_correccion_no_cambia_desde_cuando_esta_en_el_tablero(cliente: TestClient, db: Session) -> None:
    pedido = registrar_pedido(cliente)
    db.execute(
        text("UPDATE cambios_estado SET fecha_hora = CAST('2026-03-10 09:00-03' AS TIMESTAMPTZ) WHERE pedido_id = :id"),
        {"id": pedido["id"]},
    )
    desde_antes = cliente.get("/operario/tablero", headers=HEADERS_OPERARIO).json()["registrado"][0]["desde"]

    modificar(cliente, pedido["id"], destino="Calle 7 nro 1234")

    assert cliente.get("/operario/tablero", headers=HEADERS_OPERARIO).json()["registrado"][0]["desde"] == desde_antes


def test_datos_invalidos_no_se_aceptan(cliente: TestClient) -> None:
    pedido = registrar_pedido(cliente)

    assert modificar(cliente, pedido["id"], receptor_dni="12.345").status_code == 422
    assert modificar(cliente, pedido["id"], peso_kg=0).status_code == 422


def test_pedido_inexistente(cliente: TestClient) -> None:
    assert modificar(cliente, 999999).status_code == 404


def test_sin_sesion_de_operario_no_se_puede(cliente: TestClient, db: Session) -> None:
    juan = repartidor_activo(cliente, db)
    pedido = registrar_pedido(cliente)

    assert cliente.put(f"/operario/pedidos/{pedido['id']}", json=DATOS).status_code == 401
    assert modificar(cliente, pedido["id"], headers=headers_de(juan)).status_code == 403
