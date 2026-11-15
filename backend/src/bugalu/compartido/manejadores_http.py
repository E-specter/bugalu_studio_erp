"""Formato unico de error HTTP: {"error": {"codigo": str, "mensaje": str}}."""

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from bugalu.compartido.errores import ErrorDeNegocio


def respuesta_de_error(estado: int, codigo: str, mensaje: str) -> JSONResponse:
    return JSONResponse(
        {"error": {"codigo": codigo, "mensaje": mensaje}},
        status_code=estado,
        headers={"WWW-Authenticate": "Bearer"} if estado == 401 else None,
    )


def registrar_manejadores(app: FastAPI) -> None:
    @app.exception_handler(ErrorDeNegocio)
    async def _(_: Request, error: ErrorDeNegocio) -> JSONResponse:
        return respuesta_de_error(error.estado_http, error.codigo, error.mensaje)
