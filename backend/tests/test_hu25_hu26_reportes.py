"""HU-25 · Consultar métricas de la operación  y  HU-26 · Consultar rendimiento de repartidores.

Criterios de aceptación HU-25:
  1. Muestra las 4 métricas del período.
  2. El tiempo promedio de entrega coincide con el de los pedidos del período.
Criterios de aceptación HU-26:
  1. Listado del período.
  2. Ordenar por entregas realizadas.

Escenario (todo el 10/3/2026, hora de Argentina), armado para poder hacer las cuentas a mano:

  Pedido  Repartidor  Registrado  Retirado  Final
  P1      Ana         10:00       10:20     Entregado 11:00   → entrega en 60 min (retiro → entrega: 40)
  P2      Ana         10:30       11:10     Entregado 11:40   → entrega en 70 min (retiro → entrega: 30)
  P3      Ana         11:30       11:45     Fallido   12:00
  P4      Beto        12:00       12:10     Fallido   12:30
  P5      -           12:30       -         Cancelado
  Fuera   Ana         11/3 10:00  -         Entregado (no es del período)

  Registros: 10:00, 10:30, 11:30, 12:00, 12:30 → entre pedidos: (12:30 − 10:00) / 4 = 37,5 min
  Entregas de Ana: 11:00 y 11:40 → entre entregas: 40 min
  Promedio de entrega: (60 + 70) / 2 = 65 min · Fallidas: 2 de 4 terminados = 50 %
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
FOTO_JPG = b"\xff\xd8\xff\xe0" + b"0" * 100
PERIODO = {"desde": "2026-03-10", "hasta": "2026-03-10"}
_numeros = count(1)


@pytest.fixture(autouse=True)
def carpeta_fotos(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setattr(settings, "carpeta_fotos", tmp_path)
    return tmp_path


def headers_de(repartidor_id: int) -> dict[str, str]:
    return {"Authorization": f"Bearer {crear_token(repartidor_id, rol='repartidor', minutos=30)}"}


def repartidor(cliente: TestClient, db: Session, nombre: str, activo: bool = True) -> int:
    n = next(_numeros)
    repartidor_id = repartidores.insertar(
        db,
        nombre=nombre,
        dni=f"{64000000 + n}",
        correo=f"reportes{n}@mail.com",
        peso_max_kg=20,
        alto_max_cm=50,
        ancho_max_cm=50,
        largo_max_cm=50,
        codigo_acceso_hash=hashear_codigo_acceso(f"RPT{n}"),
    )["id"]
    if activo:
        cliente.post("/repartidor/jornada/comenzar", headers=headers_de(repartidor_id))
    return repartidor_id


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


def entregar(cliente: TestClient, pedido_id: int, repartidor_id: int) -> None:
    cliente.post(f"/repartidor/pedidos/{pedido_id}/retirar", headers=headers_de(repartidor_id))
    cliente.post(
        f"/repartidor/pedidos/{pedido_id}/confirmar-entrega",
        files={"foto": ("entrega.jpg", FOTO_JPG, "image/jpeg")},
        data={"dni": DNI_RECEPTOR},
        headers=headers_de(repartidor_id),
    )


def fallar(cliente: TestClient, pedido_id: int, repartidor_id: int) -> None:
    cliente.post(f"/repartidor/pedidos/{pedido_id}/retirar", headers=headers_de(repartidor_id))
    cliente.post(
        f"/repartidor/pedidos/{pedido_id}/entrega-fallida",
        json={"motivo": "Destinatario ausente"},
        headers=headers_de(repartidor_id),
    )


def fijar_horas(db: Session, pedido_id: int, horas: dict[str, str], dia: str = "2026-03-10") -> None:
    """Pone la hora de cada cambio del historial del pedido (hora de Argentina)."""
    for estado, hora in horas.items():
        db.execute(
            text(
                "UPDATE cambios_estado SET fecha_hora = CAST(:fecha_hora AS TIMESTAMPTZ) "
                "WHERE pedido_id = :id AND estado = :estado"
            ),
            {"fecha_hora": f"{dia} {hora}-03", "id": pedido_id, "estado": estado},
        )


@pytest.fixture
def escenario(cliente: TestClient, db: Session) -> dict[str, int]:
    """Arma el escenario del docstring y devuelve los ids de los repartidores."""
    ana = repartidor(cliente, db, "Ana")
    p1, p2, p3 = registrar_pedido(cliente), registrar_pedido(cliente), registrar_pedido(cliente)
    fuera = registrar_pedido(cliente)
    beto = repartidor(cliente, db, "Beto")  # nunca recibió un pedido: el próximo es para él
    p4 = registrar_pedido(cliente)
    entregar(cliente, p1, ana)
    entregar(cliente, p2, ana)
    fallar(cliente, p3, ana)
    fallar(cliente, p4, beto)
    entregar(cliente, fuera, ana)
    # Terminan la jornada después de entregar (si no, sus pedidos se reasignarían).
    cliente.post("/repartidor/jornada/terminar", headers=headers_de(ana))
    cliente.post("/repartidor/jornada/terminar", headers=headers_de(beto))
    p5 = registrar_pedido(cliente)  # nadie activo: queda registrado
    cliente.post(f"/operario/pedidos/{p5}/cancelar", headers=HEADERS_OPERARIO)
    carla = repartidor(cliente, db, "Carla", activo=False)  # sin entregas

    asignado = "repartidor_asignado"
    fijar_horas(db, p1, {"registrado": "10:00", asignado: "10:00", "en_camino": "10:20", "entregado": "11:00"})
    fijar_horas(db, p2, {"registrado": "10:30", asignado: "10:30", "en_camino": "11:10", "entregado": "11:40"})
    fijar_horas(db, p3, {"registrado": "11:30", asignado: "11:30", "en_camino": "11:45", "entrega_fallida": "12:00"})
    fijar_horas(db, p4, {"registrado": "12:00", asignado: "12:00", "en_camino": "12:10", "entrega_fallida": "12:30"})
    fijar_horas(db, p5, {"registrado": "12:30", "cancelado": "12:40"})
    fijar_horas(
        db, fuera, {"registrado": "10:00", asignado: "10:00", "en_camino": "10:05", "entregado": "10:10"}, dia="2026-03-11"
    )
    return {"ana": ana, "beto": beto, "carla": carla}


# --- HU-25 · Criterio 1: las 4 métricas del período -----------------------------------------


def test_metricas_del_periodo(cliente: TestClient, escenario: dict) -> None:
    respuesta = cliente.get("/operario/metricas", params=PERIODO, headers=HEADERS_OPERARIO)

    assert respuesta.status_code == 200
    m = respuesta.json()
    assert m["desde"] == m["hasta"] == "2026-03-10"
    assert m["total_pedidos"] == 5
    assert m["pedidos_por_estado"] == {
        "registrado": 0,
        "repartidor_asignado": 0,
        "en_camino": 0,
        "entregado": 2,
        "entrega_fallida": 2,
        "cancelado": 1,
    }
    assert m["minutos_entre_pedidos"] == pytest.approx(37.5)
    assert m["minutos_entre_entregas"] == pytest.approx(40)
    assert m["porcentaje_entregas_fallidas"] == pytest.approx(50)


# --- HU-25 · Criterio 2: el promedio de entrega coincide con los pedidos del período --------


def test_promedio_de_entrega_es_el_de_los_pedidos_del_periodo(cliente: TestClient, escenario: dict) -> None:
    m = cliente.get("/operario/metricas", params=PERIODO, headers=HEADERS_OPERARIO).json()

    # (60 + 70) / 2. El pedido del 11/3 (entregado en 10 min) no entra: si entrara, daría 46,7.
    assert m["minutos_promedio_entrega"] == pytest.approx(65)


def test_periodo_sin_pedidos(cliente: TestClient) -> None:
    m = cliente.get("/operario/metricas", params={"desde": "2020-01-01", "hasta": "2020-01-31"}, headers=HEADERS_OPERARIO).json()

    assert m["total_pedidos"] == 0
    assert set(m["pedidos_por_estado"].values()) == {0}
    assert m["minutos_entre_pedidos"] is None
    assert m["minutos_entre_entregas"] is None
    assert m["minutos_promedio_entrega"] is None
    assert m["porcentaje_entregas_fallidas"] is None


def test_metricas_por_defecto_es_el_mes_en_curso(cliente: TestClient) -> None:
    m = cliente.get("/operario/metricas", headers=HEADERS_OPERARIO).json()

    assert m["desde"].endswith("-01")
    assert m["desde"][:7] == m["hasta"][:7]


# --- HU-26 · Criterios 1 y 2: listado del período, ordenado por entregas realizadas ---------


def test_rendimiento_del_periodo_ordenado_por_entregas(cliente: TestClient, escenario: dict) -> None:
    respuesta = cliente.get("/operario/rendimiento", params=PERIODO, headers=HEADERS_OPERARIO)

    assert respuesta.status_code == 200
    filas = respuesta.json()
    assert [f["nombre"] for f in filas] == ["Ana", "Beto", "Carla"]
    ana, beto, carla = filas
    assert (ana["entregas_realizadas"], ana["entregas_fallidas"]) == (2, 1)
    assert ana["minutos_promedio_entrega"] == pytest.approx(35)  # retiro → entrega: (40 + 30) / 2
    assert (beto["entregas_realizadas"], beto["entregas_fallidas"]) == (0, 1)
    assert beto["minutos_promedio_entrega"] is None
    assert (carla["entregas_realizadas"], carla["entregas_fallidas"]) == (0, 0)


def test_rendimiento_no_cuenta_pedidos_de_otro_periodo(cliente: TestClient, escenario: dict) -> None:
    filas = cliente.get(
        "/operario/rendimiento", params={"desde": "2026-03-11", "hasta": "2026-03-11"}, headers=HEADERS_OPERARIO
    ).json()

    ana = next(f for f in filas if f["nombre"] == "Ana")
    assert (ana["entregas_realizadas"], ana["entregas_fallidas"]) == (1, 0)


# --- Reglas comunes -------------------------------------------------------------------------


@pytest.mark.parametrize("ruta", ["/operario/metricas", "/operario/rendimiento"])
def test_desde_posterior_a_hasta_no_se_permite(cliente: TestClient, ruta: str) -> None:
    respuesta = cliente.get(ruta, params={"desde": "2026-03-12", "hasta": "2026-03-10"}, headers=HEADERS_OPERARIO)

    assert respuesta.status_code == 422


@pytest.mark.parametrize("ruta", ["/operario/metricas", "/operario/rendimiento"])
def test_sin_sesion_de_operario_no_se_puede(cliente: TestClient, db: Session, ruta: str) -> None:
    repartidor_id = repartidor(cliente, db, "Ana")

    assert cliente.get(ruta).status_code == 401
    assert cliente.get(ruta, headers=headers_de(repartidor_id)).status_code == 403
