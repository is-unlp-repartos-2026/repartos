"""HU-22 · Monitorear pedidos en curso (tablero del operario).

Criterios de aceptación:
  1. Cada pedido aparece en su grupo: "Registrado", "Repartidor asignado", "En camino".
  2. Cuando un repartidor retira un pedido, pasa a "En camino" (el frontend vuelve a consultar solo).
Además: los finales no aparecen y solo el operario ve el tablero.
"""

from itertools import count

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from repartos.core.security import crear_token, hashear_codigo_acceso
from repartos.repositories import repartidores

URL = "/operario/tablero"
HEADERS_OPERARIO = {"Authorization": f"Bearer {crear_token(1, rol='operario', minutos=30)}"}
_numeros = count(1)


def headers_de(repartidor_id: int) -> dict[str, str]:
    return {"Authorization": f"Bearer {crear_token(repartidor_id, rol='repartidor', minutos=30)}"}


def repartidor_activo(cliente: TestClient, db: Session, peso: float = 20) -> int:
    n = next(_numeros)
    repartidor_id = repartidores.insertar(
        db,
        nombre=f"Repartidor {n}",
        dni=f"{51000000 + n}",
        correo=f"tablero{n}@mail.com",
        peso_max_kg=peso,
        alto_max_cm=50,
        ancho_max_cm=50,
        largo_max_cm=50,
        codigo_acceso_hash=hashear_codigo_acceso(f"TAB{n}"),
    )["id"]
    cliente.post("/repartidor/jornada/comenzar", headers=headers_de(repartidor_id))
    return repartidor_id


def registrar_pedido(cliente: TestClient, peso: float = 5) -> int:
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
    return cliente.post("/operario/pedidos", json=datos, headers=HEADERS_OPERARIO).json()["id"]


def tablero(cliente: TestClient) -> dict:
    respuesta = cliente.get(URL, headers=HEADERS_OPERARIO)
    assert respuesta.status_code == 200
    return respuesta.json()


def ids(grupo: list[dict]) -> list[int]:
    return [p["id"] for p in grupo]


# --- Criterio de aceptación 1: cada pedido en su grupo --------------------------------------


def test_cada_pedido_en_su_grupo(cliente: TestClient, db: Session) -> None:
    repartidor = repartidor_activo(cliente, db)
    asignado = registrar_pedido(cliente)
    en_camino = registrar_pedido(cliente)
    cliente.post(f"/repartidor/pedidos/{en_camino}/retirar", headers=headers_de(repartidor))
    sin_repartidor = registrar_pedido(cliente, peso=50)  # nadie puede llevarlo

    cuerpo = tablero(cliente)

    assert ids(cuerpo["registrado"]) == [sin_repartidor]
    assert ids(cuerpo["repartidor_asignado"]) == [asignado]
    assert ids(cuerpo["en_camino"]) == [en_camino]
    assert cuerpo["registrado"][0]["repartidor"] is None
    assert cuerpo["en_camino"][0]["repartidor"]["id"] == repartidor
    assert cuerpo["en_camino"][0]["desde"]


def test_los_finales_no_aparecen(cliente: TestClient, db: Session) -> None:
    repartidor = repartidor_activo(cliente, db)
    cancelado = registrar_pedido(cliente)
    cliente.post(f"/operario/pedidos/{cancelado}/cancelar", headers=HEADERS_OPERARIO)
    fallido = registrar_pedido(cliente)
    cliente.post(f"/repartidor/pedidos/{fallido}/retirar", headers=headers_de(repartidor))
    cliente.post(
        f"/repartidor/pedidos/{fallido}/entrega-fallida",
        json={"motivo": "Destinatario ausente"},
        headers=headers_de(repartidor),
    )

    cuerpo = tablero(cliente)

    assert cuerpo == {"registrado": [], "repartidor_asignado": [], "en_camino": []}


def test_tablero_vacio(cliente: TestClient) -> None:
    assert tablero(cliente) == {"registrado": [], "repartidor_asignado": [], "en_camino": []}


# --- Criterio de aceptación 2: retirar lo pasa a "en camino" --------------------------------


def test_al_retirar_pasa_a_en_camino(cliente: TestClient, db: Session) -> None:
    repartidor = repartidor_activo(cliente, db)
    pedido = registrar_pedido(cliente)
    assert ids(tablero(cliente)["repartidor_asignado"]) == [pedido]

    cliente.post(f"/repartidor/pedidos/{pedido}/retirar", headers=headers_de(repartidor))

    cuerpo = tablero(cliente)  # lo que hace el frontend cada pocos segundos
    assert ids(cuerpo["repartidor_asignado"]) == []
    assert ids(cuerpo["en_camino"]) == [pedido]


# --- Permisos -------------------------------------------------------------------------------


def test_un_repartidor_no_ve_el_tablero(cliente: TestClient, db: Session) -> None:
    repartidor = repartidor_activo(cliente, db)

    assert cliente.get(URL, headers=headers_de(repartidor)).status_code == 403


def test_sin_sesion_no_ve_el_tablero(cliente: TestClient) -> None:
    assert cliente.get(URL).status_code == 401
