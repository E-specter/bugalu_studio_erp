"""JWT de Supabase Auth (ADR-005). El stack local firma con ES256 y publica la clave en JWKS."""

from collections.abc import Callable
from functools import lru_cache
from typing import Annotated, Any

import jwt
from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt import PyJWKClient

from bugalu.compartido.configuracion import Configuracion, obtener_configuracion
from bugalu.compartido.errores import AutenticacionNoDisponible, NoAutenticado

ResolutorClave = Callable[[str], Any]
ALGORITMOS = ["ES256"]  # lo unico que firma el stack local; ni HS256 ni otro tipo de clave

_esquema = HTTPBearer(auto_error=False)


@lru_cache
def _cliente_jwks(url: str) -> PyJWKClient:
    return PyJWKClient(url, cache_keys=True)


def obtener_resolutor_clave(
    configuracion: Annotated[Configuracion, Depends(obtener_configuracion)],
) -> ResolutorClave:
    cliente = _cliente_jwks(configuracion.url_jwks)
    return lambda token: cliente.get_signing_key_from_jwt(token).key


def obtener_claims(
    credenciales: Annotated[HTTPAuthorizationCredentials | None, Depends(_esquema)],
    resolutor: Annotated[ResolutorClave, Depends(obtener_resolutor_clave)],
    configuracion: Annotated[Configuracion, Depends(obtener_configuracion)],
) -> dict[str, Any]:
    if credenciales is None:
        raise NoAutenticado("Falta el token de acceso.")
    try:
        return jwt.decode(
            credenciales.credentials,
            resolutor(credenciales.credentials),
            algorithms=ALGORITMOS,
            audience="authenticated",
            issuer=configuracion.emisor_jwt,
            options={"require": ["exp", "sub"]},
        )
    except jwt.PyJWKClientConnectionError as error:
        raise AutenticacionNoDisponible("No se pudo verificar el token ahora.") from error
    except jwt.PyJWTError as error:
        raise NoAutenticado("Token invalido o caducado.") from error
