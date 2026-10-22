"""Crea la cuenta del operario. Se corre una vez por base de datos, al poner en marcha el sistema.

Uso (desde backend/):
    uv run python -m repartos.scripts.crear_operario
"""

from getpass import getpass

from repartos.core.security import hashear_contrasena
from repartos.db.session import SessionLocal
from repartos.repositories import operarios


def main() -> None:
    usuario = input("Usuario del operario: ").strip()
    # getpass: la contraseña no se muestra en pantalla mientras se escribe.
    contrasena = getpass("Contraseña: ")
    if contrasena != getpass("Repetir contraseña: "):
        print("Las contraseñas no coinciden. No se creó el operario.")
        return

    with SessionLocal() as db:
        if operarios.buscar_por_usuario(db, usuario) is not None:
            print(f"Ya existe un operario con el usuario '{usuario}'.")
            return
        operario_id = operarios.insertar(db, usuario, hashear_contrasena(contrasena))
        db.commit()

    print(f"Operario '{usuario}' creado (id {operario_id}).")


if __name__ == "__main__":
    main()
