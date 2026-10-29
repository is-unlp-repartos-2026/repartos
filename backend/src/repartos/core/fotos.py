"""Guardar y borrar las fotos de las entregas (HU-20) en el disco.

Dos reglas de seguridad para archivos que manda un usuario:
1. El tipo se averigua mirando los primeros bytes del archivo ("número mágico"), no el nombre ni el
   tipo que dice el celular: esos los puede inventar cualquiera (por ejemplo, un .html con extensión .jpg).
2. El nombre lo inventa el servidor (uuid). Nunca se usa el nombre que mandó el usuario: uno como
   "../../src/repartos/main.py" escribiría fuera de la carpeta (ataque "path traversal").
"""

import uuid

from repartos.core.config import settings


def extension_de_imagen(contenido: bytes) -> str | None:
    """Devuelve "jpg", "png" o "webp" según los primeros bytes, o None si no es una de esas imágenes."""
    if contenido.startswith(b"\xff\xd8\xff"):
        return "jpg"
    if contenido.startswith(b"\x89PNG\r\n\x1a\n"):
        return "png"
    if contenido[:4] == b"RIFF" and contenido[8:12] == b"WEBP":
        return "webp"
    return None


def guardar(contenido: bytes, extension: str) -> str:
    """Guarda la foto con un nombre aleatorio y devuelve ese nombre (lo que se guarda en la base)."""
    settings.carpeta_fotos.mkdir(parents=True, exist_ok=True)
    nombre = f"{uuid.uuid4().hex}.{extension}"
    (settings.carpeta_fotos / nombre).write_bytes(contenido)
    return nombre


def borrar(nombre: str) -> None:
    (settings.carpeta_fotos / nombre).unlink(missing_ok=True)
