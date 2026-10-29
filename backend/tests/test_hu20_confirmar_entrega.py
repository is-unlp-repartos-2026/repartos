"""HU-20 · Confirmar entrega.

Criterios de aceptación:
  1. Foto + DNI que coincide → "Entregado".
  2. DNI que no coincide → no confirma y avisa.
Además: foto y DNI obligatorios, la foto tiene que ser una imagen de verdad, solo desde "En camino",
"Entregado" es final, solo pedidos propios y solo el repartidor puede confirmar.
"""

from itertools import count
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.orm import Session

from repartos.core.config import settings
from repartos.core.security import crear_token, hashear_codigo_acceso
from repartos.repositories import repartidores

HEADERS_OPERARIO = {"Authorization": f"Bearer {crear_token(1, rol='operario', minutos=30)}"}
DNI_RECEPTOR = "28111222"
# Lo mínimo para que sea un JPG (los primeros bytes de cualquier JPG) más relleno.
FOTO_JPG = b"\xff\xd8\xff\xe0" + b"0" * 100
_numeros = count(1)


@pytest.fixture(autouse=True)
def carpeta_fotos(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Las fotos de los tests van a una carpeta temporal que pytest borra sola."""
    monkeypatch.setattr(settings, "carpeta_fotos", tmp_path)
    return tmp_path


def headers_de(repartidor_id: int) -> dict[str, str]:
    return {"Authorization": f"Bearer {crear_token(repartidor_id, rol='repartidor', minutos=30)}"}


def repartidor_activo(cliente: TestClient, db: Session) -> int:
    n = next(_numeros)
    fila = repartidores.insertar(
        db,
        nombre=f"Repartidor {n}",
        dni=f"{46000000 + n}",
        correo=f"entrega{n}@mail.com",
        peso_max_kg=20,
        alto_max_cm=50,
        ancho_max_cm=50,
        largo_max_cm=50,
        codigo_acceso_hash=hashear_codigo_acceso(f"ENT{n}"),
    )
    cliente.post("/repartidor/jornada/comenzar", headers=headers_de(fila["id"]))
    return fila["id"]


def registrar_pedido(cliente: TestClient) -> int:
    datos = {
        "origen": "Almacén Don Pepe",
        "destino": "Calle 50 nro 456",
        "receptor_nombre": "Ana Gómez",
        "receptor_dni": DNI_RECEPTOR,
        "peso_kg": 5,
        "alto_cm": 30,
        "ancho_cm": 20,
        "largo_cm": 40,
    }
    return cliente.post("/operario/pedidos", json=datos, headers=HEADERS_OPERARIO).json()["id"]


def pedido_en_camino(cliente: TestClient, repartidor_id: int) -> int:
    pedido_id = registrar_pedido(cliente)
    cliente.post(f"/repartidor/pedidos/{pedido_id}/retirar", headers=headers_de(repartidor_id))
    return pedido_id


def confirmar(
    cliente: TestClient, pedido_id: int, repartidor_id: int, *, foto: bytes | None = FOTO_JPG, dni: str | None = DNI_RECEPTOR
):
    archivos = {"foto": ("entrega.jpg", foto, "image/jpeg")} if foto is not None else None
    formulario = {"dni": dni} if dni is not None else None
    return cliente.post(
        f"/repartidor/pedidos/{pedido_id}/confirmar-entrega",
        files=archivos,
        data=formulario,
        headers=headers_de(repartidor_id),
    )


def pedido_en_base(db: Session, pedido_id: int) -> tuple:
    return db.execute(
        text("SELECT estado, foto_entrega FROM pedidos WHERE id = :id"), {"id": pedido_id}
    ).one()


# --- Criterio de aceptación 1: foto + DNI que coincide --------------------------------------


def test_foto_y_dni_correcto_queda_entregado(cliente: TestClient, db: Session, carpeta_fotos: Path) -> None:
    repartidor = repartidor_activo(cliente, db)
    pedido = pedido_en_camino(cliente, repartidor)

    respuesta = confirmar(cliente, pedido, repartidor)

    assert respuesta.status_code == 200
    assert respuesta.json() == {"id": pedido, "estado": "entregado"}
    estado, foto = pedido_en_base(db, pedido)
    assert estado == "entregado"
    # La foto quedó en el disco con un nombre inventado por el servidor (no "entrega.jpg").
    assert foto != "entrega.jpg" and foto.endswith(".jpg")
    assert (carpeta_fotos / foto).read_bytes() == FOTO_JPG


@pytest.mark.parametrize(
    "foto, extension",
    [(b"\x89PNG\r\n\x1a\n" + b"0" * 50, "png"), (b"RIFF\x00\x00\x00\x00WEBP" + b"0" * 50, "webp")],
)
def test_acepta_png_y_webp(cliente: TestClient, db: Session, foto: bytes, extension: str) -> None:
    repartidor = repartidor_activo(cliente, db)
    pedido = pedido_en_camino(cliente, repartidor)

    assert confirmar(cliente, pedido, repartidor, foto=foto).status_code == 200
    assert pedido_en_base(db, pedido)[1].endswith(f".{extension}")


# --- Criterio de aceptación 2: DNI que no coincide ------------------------------------------


def test_dni_que_no_coincide_no_confirma(cliente: TestClient, db: Session, carpeta_fotos: Path) -> None:
    repartidor = repartidor_activo(cliente, db)
    pedido = pedido_en_camino(cliente, repartidor)

    respuesta = confirmar(cliente, pedido, repartidor, dni="99999999")

    assert respuesta.status_code == 409
    assert respuesta.json()["detail"] == "El DNI no coincide con el de quien tiene que recibir el pedido"
    assert pedido_en_base(db, pedido) == ("en_camino", None)
    assert list(carpeta_fotos.iterdir()) == []  # no quedó ninguna foto guardada


# --- Foto y DNI obligatorios y válidos ------------------------------------------------------


@pytest.mark.parametrize(
    "cambio",
    [{"foto": None}, {"dni": None}, {"dni": "28.111.222"}, {"foto": b"<html>no soy una foto</html>"}, {"foto": b""}],
    ids=["sin foto", "sin dni", "dni con puntos", "archivo que no es imagen", "archivo vacio"],
)
def test_sin_foto_o_dni_validos_no_confirma(cliente: TestClient, db: Session, cambio: dict) -> None:
    repartidor = repartidor_activo(cliente, db)
    pedido = pedido_en_camino(cliente, repartidor)

    respuesta = confirmar(cliente, pedido, repartidor, **cambio)

    assert respuesta.status_code == 422
    assert pedido_en_base(db, pedido) == ("en_camino", None)


def test_foto_demasiado_grande(cliente: TestClient, db: Session, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "tamano_max_foto_mb", 1)
    repartidor = repartidor_activo(cliente, db)
    pedido = pedido_en_camino(cliente, repartidor)

    respuesta = confirmar(cliente, pedido, repartidor, foto=FOTO_JPG + b"0" * (1024 * 1024))

    assert respuesta.status_code == 422
    assert pedido_en_base(db, pedido) == ("en_camino", None)


# --- Estados y pertenencia ------------------------------------------------------------------


def test_solo_desde_en_camino(cliente: TestClient, db: Session) -> None:
    repartidor = repartidor_activo(cliente, db)
    asignado = registrar_pedido(cliente)  # todavía no lo retiró

    respuesta = confirmar(cliente, asignado, repartidor)

    assert respuesta.status_code == 409
    assert respuesta.json()["detail"] == "Solo se puede confirmar la entrega de un pedido en camino"


def test_entregado_es_final(cliente: TestClient, db: Session) -> None:
    repartidor = repartidor_activo(cliente, db)
    pedido = pedido_en_camino(cliente, repartidor)
    confirmar(cliente, pedido, repartidor)

    otra_vez = confirmar(cliente, pedido, repartidor)
    fallida = cliente.post(
        f"/repartidor/pedidos/{pedido}/entrega-fallida",
        json={"motivo": "Destinatario ausente"},
        headers=headers_de(repartidor),
    )

    assert otra_vez.status_code == 409
    assert fallida.status_code == 409


def test_no_puede_confirmar_un_pedido_de_otro(cliente: TestClient, db: Session) -> None:
    dueno = repartidor_activo(cliente, db)
    pedido = pedido_en_camino(cliente, dueno)
    otro = repartidor_activo(cliente, db)

    assert confirmar(cliente, pedido, otro).status_code == 404


# --- Permisos -------------------------------------------------------------------------------


def test_el_operario_no_puede_confirmar(cliente: TestClient) -> None:
    respuesta = cliente.post(
        "/repartidor/pedidos/1/confirmar-entrega",
        files={"foto": ("e.jpg", FOTO_JPG, "image/jpeg")},
        data={"dni": DNI_RECEPTOR},
        headers=HEADERS_OPERARIO,
    )
    assert respuesta.status_code == 403


def test_sin_sesion_no_puede_confirmar(cliente: TestClient) -> None:
    respuesta = cliente.post(
        "/repartidor/pedidos/1/confirmar-entrega",
        files={"foto": ("e.jpg", FOTO_JPG, "image/jpeg")},
        data={"dni": DNI_RECEPTOR},
    )
    assert respuesta.status_code == 401
