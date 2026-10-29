"""Seguridad: contraseñas, códigos de acceso y tokens de sesión (JWT).

Cuatro herramientas:
1. Contraseñas: se guarda solo su hash; para verificar, se hashea lo que escribió el usuario y se compara.
2. Códigos aleatorios: el de acceso del repartidor (se guarda solo su hash) y el de seguimiento.
3. Tokens: al iniciar sesión se fabrica un token firmado; en cada request se verifica.
4. Dependencias para proteger endpoints: un endpoint que necesite al operario logueado pide
   Depends(obtener_id_operario_actual) y, si el token falta o no es válido, FastAPI responde 401.
   Lo mismo para el repartidor con Depends(obtener_id_repartidor_actual).
"""

import hashlib
import secrets
from datetime import UTC, datetime, timedelta
from typing import Annotated

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pwdlib import PasswordHash

from repartos.core.config import settings
from repartos.db.session import SesionDB
from repartos.repositories import repartidores

# --------------------------------------------------------------------------------------------
# 1. Contraseñas
# --------------------------------------------------------------------------------------------

# Algoritmo recomendado (Argon2): lento a propósito, para que adivinar contraseñas probando
# millones de combinaciones sea carísimo aunque alguien robe la base.
_hasher = PasswordHash.recommended()


def hashear_contrasena(contrasena: str) -> str:
    """Devuelve el hash que se guarda en la base. Cada llamada da un hash distinto (usa una "sal" aleatoria)."""
    return _hasher.hash(contrasena)


def verificar_contrasena(contrasena: str, hash_guardado: str) -> bool:
    """¿La contraseña escrita corresponde a ese hash? Nunca se "deshashea": se recalcula y se compara."""
    return _hasher.verify(contrasena, hash_guardado)


# --------------------------------------------------------------------------------------------
# 2. Códigos aleatorios: de acceso del repartidor y de seguimiento del pedido
# --------------------------------------------------------------------------------------------

# Sin 0/O ni 1/I/L: se tipean en el celular y no tienen que confundirse.
_ALFABETO_CODIGO = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"
LARGO_CODIGO_ACCESO = 8  # 31^8 ≈ 850 mil millones de códigos posibles
LARGO_CODIGO_SEGUIMIENTO = 8


def _generar_codigo(largo: int) -> str:
    """`secrets` (no `random`): sus resultados son impredecibles, aptos para seguridad."""
    return "".join(secrets.choice(_ALFABETO_CODIGO) for _ in range(largo))


def generar_codigo_acceso() -> str:
    """Código con el que el repartidor ingresa a la app (HU-02)."""
    return _generar_codigo(LARGO_CODIGO_ACCESO)


def generar_codigo_seguimiento() -> str:
    """Código con el que el cliente final consulta su pedido (HU-21).

    Es su único control de acceso: por eso es aleatorio y no un número correlativo (con 1, 2, 3...
    cualquiera podría ver los pedidos de otros probando números).
    """
    return _generar_codigo(LARGO_CODIGO_SEGUIMIENTO)


def hashear_codigo_acceso(codigo: str) -> str:
    """Hash SHA-256 del código (64 caracteres hexadecimales).

    A diferencia de la contraseña, NO se usa Argon2: Argon2 agrega una sal aleatoria y el mismo código
    daría un hash distinto cada vez. Al ingresar (HU-02) el repartidor manda SOLO el código, sin usuario,
    así que hay que poder buscarlo: WHERE codigo_acceso_hash = :hash. Con SHA-256 el mismo código da
    siempre el mismo hash. Es seguro porque el código no lo inventa una persona: es largo y aleatorio.
    """
    return hashlib.sha256(codigo.upper().encode()).hexdigest()


# --------------------------------------------------------------------------------------------
# 3. Tokens (JWT)
# --------------------------------------------------------------------------------------------


def crear_token(id_usuario: int, rol: str, minutos: int) -> str:
    """Fabrica un token firmado que dice quién es (sub), qué rol tiene y hasta cuándo vale (exp)."""
    datos = {
        "sub": str(id_usuario),  # el estándar JWT pide que "sub" sea texto
        "rol": rol,              # "operario" o "repartidor": cada uno solo usa los endpoints de su rol
        "exp": datetime.now(UTC) + timedelta(minutes=minutos),
    }
    return jwt.encode(datos, settings.secret_key, algorithm=settings.algoritmo_token)


def _leer_token(token: str) -> dict:
    """Verifica la firma y el vencimiento. Si algo falla, responde 401 (no autenticado)."""
    try:
        return jwt.decode(token, settings.secret_key, algorithms=[settings.algoritmo_token])
    except jwt.InvalidTokenError:  # firma inválida, token vencido o mal formado
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Sesión inválida o vencida")


# --------------------------------------------------------------------------------------------
# 4. Dependencias para proteger endpoints
# --------------------------------------------------------------------------------------------

# Lee el header "Authorization: Bearer <token>". auto_error=False: si falta, devuelve None y
# respondemos nosotros con 401 (en lugar del 403 que daría FastAPI por defecto).
_esquema_bearer = HTTPBearer(auto_error=False)

REPARTIDOR_DESHABILITADO = "Estás deshabilitado. Consultá con el operario"


def _leer_token_del_rol(credenciales: HTTPAuthorizationCredentials | None, rol: str) -> int:
    """Verifica que haya token, que sea válido y que sea del rol pedido. Devuelve el id del usuario."""
    if credenciales is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Falta iniciar sesión")
    datos = _leer_token(credenciales.credentials)
    if datos.get("rol") != rol:  # p. ej., un repartidor intentando usar un endpoint del operario
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=f"Acción solo para el {rol}")
    return int(datos["sub"])


def obtener_id_operario_actual(
    credenciales: Annotated[HTTPAuthorizationCredentials | None, Depends(_esquema_bearer)],
) -> int:
    """Dependencia: devuelve el id del operario logueado o corta la request con 401/403."""
    return _leer_token_del_rol(credenciales, "operario")


def obtener_id_repartidor_actual(
    credenciales: Annotated[HTTPAuthorizationCredentials | None, Depends(_esquema_bearer)],
    db: SesionDB,
) -> int:
    """Dependencia: devuelve el id del repartidor logueado o corta la request con 401/403.

    Su token dura 30 días, así que en CADA request se revisa en la base que siga habilitado:
    si el operario lo deshabilita (HU-12), pierde el acceso en ese momento y no cuando venza el token.
    """
    repartidor_id = _leer_token_del_rol(credenciales, "repartidor")
    repartidor = repartidores.buscar_por_id(db, repartidor_id)
    if repartidor is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Sesión inválida")
    if not repartidor["habilitado"]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=REPARTIDOR_DESHABILITADO)
    return repartidor_id


# Atajos para usar en los routers: `operario_id: OperarioActual`, `repartidor_id: RepartidorActual`
OperarioActual = Annotated[int, Depends(obtener_id_operario_actual)]
RepartidorActual = Annotated[int, Depends(obtener_id_repartidor_actual)]
