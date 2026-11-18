"""JWT de Supabase Auth (ADR-005). El stack local firma con ES256 y publica la clave en JWKS."""

from collections.abc import Callable
from functools import lru_cache
from typing import Annotated, Any
from uuid import UUID

import jwt
from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt import PyJWKClient

from bugalu.compartido.configuracion import Configuracion, obtener_configuracion
from bugalu.compartido.errores import AutenticacionNoDisponible, NoAutenticado

ResolutorClave = Callable[[str], Any]
ALGORITMOS = ["ES256"]  # lo unico que firma el stack local; ni HS256 ni otro tipo de clave

# Espera maxima por el JWKS de Auth (PyJWT usa 30 s por defecto: una peticion colgada tanto tiempo)
TIMEOUT_JWKS_SEGUNDOS = 5.0

_esquema = HTTPBearer(auto_error=False)


@lru_cache
def _cliente_jwks(url: str) -> PyJWKClient:
    return PyJWKClient(url, cache_keys=True, timeout=TIMEOUT_JWKS_SEGUNDOS)


def obtener_resolutor_clave(
    configuracion: Annotated[Configuracion, Depends(obtener_configuracion)],
) -> ResolutorClave:
    cliente = _cliente_jwks(configuracion.url_jwks)
    return lambda token: _clave_de(cliente, token)


def _clave_de(cliente: PyJWKClient, token: str) -> Any:
    try:
        cliente.get_signing_keys()  # el JWKS (en cache) debe tener forma de JWKS: si no, falla Auth
    except jwt.PyJWKClientConnectionError:
        raise
    except jwt.PyJWTError as error:
        raise ValueError("El JWKS no tiene forma de JWKS.") from error
    return cliente.get_signing_key_from_jwt(token).key  # un `kid` ausente es del token: 401


def obtener_claims(
    credenciales: Annotated[HTTPAuthorizationCredentials | None, Depends(_esquema)],
    resolutor: Annotated[ResolutorClave, Depends(obtener_resolutor_clave)],
    configuracion: Annotated[Configuracion, Depends(obtener_configuracion)],
) -> dict[str, Any]:
    if credenciales is None:
        raise NoAutenticado("Falta el token de acceso.")
    try:
        clave = resolutor(credenciales.credentials)
    except (jwt.PyJWKClientConnectionError, ValueError) as error:  # ValueError: JWKS no es JWKS
        raise AutenticacionNoDisponible("No se pudo verificar el token ahora.") from error
    except jwt.PyJWTError as error:
        raise NoAutenticado("Token invalido o caducado.") from error
    try:
        claims: dict[str, Any] = jwt.decode(
            credenciales.credentials,
            clave,
            algorithms=ALGORITMOS,
            audience="authenticated",
            issuer=configuracion.emisor_jwt,
            options={"require": ["exp", "sub"]},
        )
        UUID(str(claims["sub"]))  # los routers convierten `sub` a UUID: aqui se valida
    except (jwt.PyJWTError, ValueError) as error:
        raise NoAutenticado("Token invalido o caducado.") from error
    return claims


def obtener_claims_opcionales(
    credenciales: Annotated[HTTPAuthorizationCredentials | None, Depends(_esquema)],
    resolutor: Annotated[ResolutorClave, Depends(obtener_resolutor_clave)],
    configuracion: Annotated[Configuracion, Depends(obtener_configuracion)],
) -> dict[str, Any] | None:
    """Endpoints publicos con mas detalle para quien tiene sesion: sin token es visitante; con un
    token invalido es 401 (nunca se degrada en silencio a visitante)."""
    if credenciales is None:
        return None
    return obtener_claims(credenciales, resolutor, configuracion)


def obtener_claims_o_visitante(
    credenciales: Annotated[HTTPAuthorizationCredentials | None, Depends(_esquema)],
    resolutor: Annotated[ResolutorClave, Depends(obtener_resolutor_clave)],
    configuracion: Annotated[Configuracion, Depends(obtener_configuracion)],
) -> dict[str, Any] | None:
    """Alta publica (RF-16): un token vencido o manipulado se trata como visitante (nunca 401);
    si no se puede verificar por una caida de Auth, sigue siendo 503."""
    try:
        return obtener_claims_opcionales(credenciales, resolutor, configuracion)
    except NoAutenticado:
        return None


def obtener_token(
    _claims: Annotated[dict[str, Any], Depends(obtener_claims)],
    credenciales: Annotated[HTTPAuthorizationCredentials | None, Depends(_esquema)],
) -> str:
    """Token crudo, ya verificado, para reenviarlo a Storage con la identidad del propio usuario."""
    assert credenciales is not None  # obtener_claims ya exigio el token
    return credenciales.credentials
