"""HU-21 · Consultar estado de pedido (cliente final, sin login).

Criterios de aceptación:
  1. Código válido → estado actual e historial con fecha y hora.
  2. Código inexistente → "no encontrado" (y se puede reintentar).
Además: no pide sesión, no muestra datos privados, acepta el código en minúsculas.
"""

from itertools import count

from fastapi.testclient import TestClient
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
        dni=f"{49000000 + n}",
        correo=f"seguimiento{n}@mail.com",
        peso_max_kg=20,
        alto_max_cm=50,
        ancho_max_cm=50,
        largo_max_cm=50,
        codigo_acceso_hash=hashear_codigo_acceso(f"SEG{n}"),
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


# --- Criterio de aceptación 1: código válido ------------------------------------------------


def test_codigo_valido_muestra_estado_e_historial(cliente: TestClient, db: Session) -> None:
    repartidor = repartidor_activo(cliente, db)
    pedido = registrar_pedido(cliente)
    cliente.post(f"/repartidor/pedidos/{pedido['id']}/retirar", headers=headers_de(repartidor))

    respuesta = cliente.get(f"/seguimiento/{pedido['codigo_seguimiento']}")  # sin headers: sin login

    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    assert cuerpo["codigo_seguimiento"] == pedido["codigo_seguimiento"]
    assert cuerpo["estado"] == "en_camino"
    assert [c["estado"] for c in cuerpo["historial"]] == ["registrado", "repartidor_asignado", "en_camino"]
    assert all(c["fecha_hora"] for c in cuerpo["historial"])


def test_no_muestra_datos_privados(cliente: TestClient, db: Session) -> None:
    repartidor_activo(cliente, db)
    pedido = registrar_pedido(cliente)

    cuerpo = cliente.get(f"/seguimiento/{pedido['codigo_seguimiento']}").json()

    assert set(cuerpo) == {"codigo_seguimiento", "estado", "historial"}
    assert all(set(c) == {"estado", "fecha_hora"} for c in cuerpo["historial"])
    assert "28111222" not in str(cuerpo) and "Ana" not in str(cuerpo)


def test_acepta_el_codigo_en_minusculas(cliente: TestClient) -> None:
    pedido = registrar_pedido(cliente)

    respuesta = cliente.get(f"/seguimiento/{pedido['codigo_seguimiento'].lower()}")

    assert respuesta.status_code == 200
    assert respuesta.json()["estado"] == "registrado"


# --- Criterio de aceptación 2: código inexistente -------------------------------------------


def test_codigo_inexistente_no_encontrado(cliente: TestClient) -> None:
    respuesta = cliente.get("/seguimiento/NOEXISTE")

    assert respuesta.status_code == 404
    assert respuesta.json()["detail"] == "No encontramos un pedido con ese código. Revisalo e intentá de nuevo"


def test_puede_reintentar_despues_de_equivocarse(cliente: TestClient) -> None:
    pedido = registrar_pedido(cliente)
    cliente.get("/seguimiento/NOEXISTE")

    assert cliente.get(f"/seguimiento/{pedido['codigo_seguimiento']}").status_code == 200
