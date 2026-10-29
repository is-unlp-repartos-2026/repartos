"""HU-23 · Consultar detalle de pedido (operario).

Criterios de aceptación:
  1. En curso → datos, código y estados.
  2. Entregado → además la foto y el DNI.
  3. Entrega fallida → además el motivo.
Además: el historial dice quién y por qué, la foto solo la ve el operario, y solo el operario consulta.
"""

from itertools import count
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from repartos.core.config import settings
from repartos.core.security import crear_token, hashear_codigo_acceso
from repartos.repositories import repartidores

HEADERS_OPERARIO = {"Authorization": f"Bearer {crear_token(1, rol='operario', minutos=30)}"}
DATOS_PEDIDO = {
    "origen": "Almacén Don Pepe",
    "destino": "Calle 50 nro 456",
    "receptor_nombre": "Ana Gómez",
    "receptor_dni": "28111222",
    "peso_kg": 5,
    "alto_cm": 30,
    "ancho_cm": 20,
    "largo_cm": 40,
}
FOTO_JPG = b"\xff\xd8\xff\xe0" + b"0" * 100
_numeros = count(1)


@pytest.fixture(autouse=True)
def carpeta_fotos(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setattr(settings, "carpeta_fotos", tmp_path)
    return tmp_path


def headers_de(repartidor_id: int) -> dict[str, str]:
    return {"Authorization": f"Bearer {crear_token(repartidor_id, rol='repartidor', minutos=30)}"}


def repartidor_activo(cliente: TestClient, db: Session) -> int:
    n = next(_numeros)
    repartidor_id = repartidores.insertar(
        db,
        nombre=f"Repartidor {n}",
        dni=f"{50000000 + n}",
        correo=f"detop{n}@mail.com",
        peso_max_kg=20,
        alto_max_cm=50,
        ancho_max_cm=50,
        largo_max_cm=50,
        codigo_acceso_hash=hashear_codigo_acceso(f"DOP{n}"),
    )["id"]
    cliente.post("/repartidor/jornada/comenzar", headers=headers_de(repartidor_id))
    return repartidor_id


def registrar_pedido(cliente: TestClient) -> dict:
    return cliente.post("/operario/pedidos", json=DATOS_PEDIDO, headers=HEADERS_OPERARIO).json()


def retirar(cliente: TestClient, pedido_id: int, repartidor_id: int) -> None:
    cliente.post(f"/repartidor/pedidos/{pedido_id}/retirar", headers=headers_de(repartidor_id))


def detalle(cliente: TestClient, pedido_id: int) -> dict:
    respuesta = cliente.get(f"/operario/pedidos/{pedido_id}", headers=HEADERS_OPERARIO)
    assert respuesta.status_code == 200
    return respuesta.json()


# --- Criterio de aceptación 1: en curso -----------------------------------------------------


def test_en_curso_muestra_datos_codigo_y_estados(cliente: TestClient, db: Session) -> None:
    repartidor = repartidor_activo(cliente, db)
    pedido = registrar_pedido(cliente)
    retirar(cliente, pedido["id"], repartidor)

    cuerpo = detalle(cliente, pedido["id"])

    assert {k: cuerpo[k] for k in DATOS_PEDIDO} == DATOS_PEDIDO
    assert cuerpo["codigo_seguimiento"] == pedido["codigo_seguimiento"]
    assert cuerpo["estado"] == "en_camino"
    assert cuerpo["repartidor"]["id"] == repartidor
    assert [c["estado"] for c in cuerpo["historial"]] == ["registrado", "repartidor_asignado", "en_camino"]
    assert cuerpo["foto_url"] is None
    assert cuerpo["motivo_fallo"] is None


def test_el_historial_dice_quien_y_por_que(cliente: TestClient, db: Session) -> None:
    repartidor = repartidor_activo(cliente, db)
    pedido = registrar_pedido(cliente)
    cliente.post(f"/operario/pedidos/{pedido['id']}/cancelar", headers=HEADERS_OPERARIO)

    historial = detalle(cliente, pedido["id"])["historial"]

    assert historial[0]["repartidor"] is None  # al registrarlo no tenía repartidor
    assert historial[1]["repartidor"]["id"] == repartidor
    assert historial[1]["detalle"] == "Asignación automática"
    assert historial[2]["estado"] == "cancelado"
    assert historial[2]["detalle"] == "Cancelado por el operario"


def test_pedido_sin_repartidor(cliente: TestClient) -> None:
    pedido = registrar_pedido(cliente)  # nadie activo

    cuerpo = detalle(cliente, pedido["id"])

    assert cuerpo["estado"] == "registrado"
    assert cuerpo["repartidor"] is None


# --- Criterio de aceptación 2: entregado ----------------------------------------------------


def test_entregado_muestra_la_foto_y_el_dni(cliente: TestClient, db: Session) -> None:
    repartidor = repartidor_activo(cliente, db)
    pedido = registrar_pedido(cliente)
    retirar(cliente, pedido["id"], repartidor)
    cliente.post(
        f"/repartidor/pedidos/{pedido['id']}/confirmar-entrega",
        files={"foto": ("e.jpg", FOTO_JPG, "image/jpeg")},
        data={"dni": "28111222"},
        headers=headers_de(repartidor),
    )

    cuerpo = detalle(cliente, pedido["id"])

    assert cuerpo["estado"] == "entregado"
    assert cuerpo["receptor_dni"] == "28111222"
    assert cuerpo["foto_url"] == f"/operario/pedidos/{pedido['id']}/foto"
    foto = cliente.get(cuerpo["foto_url"], headers=HEADERS_OPERARIO)
    assert foto.status_code == 200
    assert foto.content == FOTO_JPG


# --- Criterio de aceptación 3: entrega fallida ----------------------------------------------


def test_entrega_fallida_muestra_el_motivo(cliente: TestClient, db: Session) -> None:
    repartidor = repartidor_activo(cliente, db)
    pedido = registrar_pedido(cliente)
    retirar(cliente, pedido["id"], repartidor)
    cliente.post(
        f"/repartidor/pedidos/{pedido['id']}/entrega-fallida",
        json={"motivo": "Dirección incorrecta"},
        headers=headers_de(repartidor),
    )

    cuerpo = detalle(cliente, pedido["id"])

    assert cuerpo["estado"] == "entrega_fallida"
    assert cuerpo["motivo_fallo"] == "Dirección incorrecta"
    assert cuerpo["foto_url"] is None


# --- Otros casos y permisos -----------------------------------------------------------------


def test_pedido_inexistente(cliente: TestClient) -> None:
    assert cliente.get("/operario/pedidos/999999", headers=HEADERS_OPERARIO).status_code == 404


def test_foto_de_un_pedido_sin_foto(cliente: TestClient) -> None:
    pedido = registrar_pedido(cliente)

    respuesta = cliente.get(f"/operario/pedidos/{pedido['id']}/foto", headers=HEADERS_OPERARIO)

    assert respuesta.status_code == 404


def test_un_repartidor_no_puede_ver_el_detalle_ni_la_foto(cliente: TestClient, db: Session) -> None:
    repartidor = repartidor_activo(cliente, db)
    pedido = registrar_pedido(cliente)

    assert cliente.get(f"/operario/pedidos/{pedido['id']}", headers=headers_de(repartidor)).status_code == 403
    assert cliente.get(f"/operario/pedidos/{pedido['id']}/foto", headers=headers_de(repartidor)).status_code == 403


def test_sin_sesion_no_puede_consultar(cliente: TestClient) -> None:
    assert cliente.get("/operario/pedidos/1").status_code == 401
    assert cliente.get("/operario/pedidos/1/foto").status_code == 401
