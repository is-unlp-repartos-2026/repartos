"""HU-10 · Listar repartidores.

Criterios de aceptación:
  1. Lista todos (nombre, DNI, carga habilitada, habilitado/deshabilitado, activo/inactivo).
  2. Filtro por deshabilitados.
Además: nunca muestra el código de acceso y solo el operario puede ver la lista.
"""

from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.orm import Session

from repartos.core.security import crear_token, hashear_codigo_acceso
from repartos.repositories import repartidores

URL = "/operario/repartidores"
HEADERS_OPERARIO = {"Authorization": f"Bearer {crear_token(1, rol='operario', minutos=30)}"}


def crear_repartidor(db: Session, nombre: str, dni: str, *, habilitado: bool = True, activo: bool = False) -> int:
    repartidor_id = repartidores.insertar(
        db,
        nombre=nombre,
        dni=dni,
        correo=f"{dni}@mail.com",
        peso_max_kg=20,
        alto_max_cm=50,
        ancho_max_cm=40,
        largo_max_cm=60,
        codigo_acceso_hash=hashear_codigo_acceso(f"C{dni}"),
    )["id"]
    db.execute(
        text("UPDATE repartidores SET habilitado = :habilitado, activo = :activo WHERE id = :id"),
        {"habilitado": habilitado, "activo": activo, "id": repartidor_id},
    )
    return repartidor_id


def listar(cliente: TestClient, **filtros) -> list[dict]:
    respuesta = cliente.get(URL, params=filtros, headers=HEADERS_OPERARIO)
    assert respuesta.status_code == 200
    return respuesta.json()


# --- Criterio de aceptación 1: lista todos --------------------------------------------------


def test_lista_todos_con_sus_datos(cliente: TestClient, db: Session) -> None:
    crear_repartidor(db, "Bruno", "30000002", activo=True)
    crear_repartidor(db, "Ana", "30000001", habilitado=False)

    lista = listar(cliente)

    assert [r["nombre"] for r in lista] == ["Ana", "Bruno"]  # por nombre
    ana = lista[0]
    assert ana["dni"] == "30000001"
    assert (ana["peso_max_kg"], ana["alto_max_cm"], ana["ancho_max_cm"], ana["largo_max_cm"]) == (20, 50, 40, 60)
    assert (ana["habilitado"], ana["activo"]) == (False, False)
    assert (lista[1]["habilitado"], lista[1]["activo"]) == (True, True)


def test_nunca_muestra_el_codigo_de_acceso(cliente: TestClient, db: Session) -> None:
    crear_repartidor(db, "Ana", "30000001")

    repartidor = listar(cliente)[0]

    assert not any("codigo" in campo for campo in repartidor)


def test_sin_repartidores(cliente: TestClient) -> None:
    assert listar(cliente) == []


# --- Criterio de aceptación 2: filtro por deshabilitados ------------------------------------


def test_filtro_por_deshabilitados(cliente: TestClient, db: Session) -> None:
    crear_repartidor(db, "Ana", "30000001", habilitado=False)
    crear_repartidor(db, "Bruno", "30000002")

    assert [r["nombre"] for r in listar(cliente, habilitado="false")] == ["Ana"]
    assert [r["nombre"] for r in listar(cliente, habilitado="true")] == ["Bruno"]


def test_filtro_invalido(cliente: TestClient) -> None:
    respuesta = cliente.get(URL, params={"habilitado": "quizas"}, headers=HEADERS_OPERARIO)

    assert respuesta.status_code == 422


# --- Permisos -------------------------------------------------------------------------------


def test_un_repartidor_no_ve_la_lista(cliente: TestClient) -> None:
    headers = {"Authorization": f"Bearer {crear_token(1, rol='repartidor', minutos=30)}"}

    assert cliente.get(URL, headers=headers).status_code == 403


def test_sin_sesion_no_ve_la_lista(cliente: TestClient) -> None:
    assert cliente.get(URL).status_code == 401
