"""Formato unico de error HTTP: {"error": {"codigo": str, "mensaje": str, "detalles"?: dict}}."""

from collections.abc import Mapping
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from psycopg import DataError, OperationalError  # incluye PoolTimeout
from starlette.exceptions import HTTPException as StarletteHTTPException

from bugalu.compartido.errores import ErrorDeNegocio

_HTTP = {
    404: ("no_encontrado", "Recurso no encontrado."),
    405: ("metodo_no_permitido", "Metodo no permitido."),
}


def respuesta_de_error(
    estado: int,
    codigo: str,
    mensaje: str,
    cabeceras: Mapping[str, str] | None = None,
    detalles: dict[str, Any] | None = None,
) -> JSONResponse:
    cabeceras = dict(cabeceras or {})
    if estado == 401:
        cabeceras["WWW-Authenticate"] = "Bearer"
    error: dict[str, Any] = {"codigo": codigo, "mensaje": mensaje}
    if detalles:
        error["detalles"] = detalles
    return JSONResponse(
        {"error": error},
        status_code=estado,
        headers=cabeceras or None,
    )


def registrar_manejadores(app: FastAPI) -> None:
    @app.exception_handler(ErrorDeNegocio)
    async def _(_: Request, error: ErrorDeNegocio) -> JSONResponse:
        return respuesta_de_error(
            error.estado_http, error.codigo, error.mensaje, detalles=error.detalles
        )

    @app.exception_handler(StarletteHTTPException)
    async def _http(_: Request, error: StarletteHTTPException) -> JSONResponse:
        codigo, mensaje = _HTTP.get(error.status_code, ("error_http", str(error.detail)))
        return respuesta_de_error(
            error.status_code, codigo, mensaje, error.headers
        )  # `Allow` en 405

    @app.exception_handler(RequestValidationError)
    async def _validacion(_: Request, error: RequestValidationError) -> JSONResponse:
        # Solo el nombre de los campos: sin valores recibidos ni mensajes internos de pydantic.
        campos = dict.fromkeys(
            ".".join(str(p) for p in e["loc"][1:]) or "cuerpo" for e in error.errors()
        )
        return respuesta_de_error(
            422,
            "datos_invalidos",
            f"Datos invalidos: {', '.join(campos)}.",
            detalles={"campo": next(iter(campos))},
        )

    @app.exception_handler(OperationalError)
    async def _base_caida(_: Request, __: OperationalError) -> JSONResponse:
        return respuesta_de_error(
            503, "base_de_datos_no_disponible", "No se pudo acceder a los datos ahora."
        )

    @app.exception_handler(DataError)
    async def _dato_invalido(_: Request, __: DataError) -> JSONResponse:
        # Defensa en profundidad: lo que la validacion de entrada no atajo, sin detalles de la base.
        return respuesta_de_error(422, "datos_invalidos", "Datos invalidos.")
