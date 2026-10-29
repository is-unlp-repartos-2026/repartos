"""Seguridad: contraseñas, códigos de acceso y tokens de sesión (JWT).

Cuatro herramientas:
1. Contraseñas: se guarda solo su hash; para verificar, se hashea lo que escribió el usuario y se compara.
2. Códigos de acceso del repartidor: los genera el sistema; también se guarda solo su hash.
3. Tokens: al iniciar sesión se fabrica un token firmado; en cada request se verifica.
4. Dependencias para proteger endpoints: un endpoint que necesite al operario logueado pide
   Depends(obtener_id_operario_actual) y, si el token falta o no es válido, FastAPI responde 401.
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
# 2. Códigos de acceso del repartidor
# --------------------------------------------------------------------------------------------

# Sin 0/O ni 1/I/L: el repartidor lo tipea en el celular y no tiene que confundirse.
_ALFABETO_CODIGO = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"
LARGO_CODIGO_ACCESO = 8  # 31^8 ≈ 850 mil millones de códigos posibles


def generar_codigo_acceso() -> str:
    """Código aleatorio para el repartidor. `secrets` (no `random`): es impredecible, apto para seguridad."""
    return "".join(secrets.choice(_ALFABETO_CODIGO) for _ in range(LARGO_CODIGO_ACCESO))


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


def obtener_id_operario_actual(
    credenciales: Annotated[HTTPAuthorizationCredentials | None, Depends(_esquema_bearer)],
) -> int:
    """Dependencia: devuelve el id del operario logueado o corta la request con 401."""
    if credenciales is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Falta iniciar sesión")
    datos = _leer_token(credenciales.credentials)
    if datos.get("rol") != "operario":  # p. ej., un repartidor intentando usar un endpoint del operario
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Acción solo para el operario")
    return int(datos["sub"])


# Atajo para usar en los routers: `operario_id: OperarioActual`
OperarioActual = Annotated[int, Depends(obtener_id_operario_actual)]
