from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, Request

from bugalu.compartido.autenticacion import obtener_claims
from bugalu.compartido.base_datos import transaccion_con_identidad
from bugalu.compartido.esquemas import RespuestaError
from bugalu.modulos.identidad.aplicacion.obtener_perfil.caso_de_uso import ObtenerPerfil
from bugalu.modulos.identidad.infraestructura.entrada.http.esquemas import PerfilRespuesta
from bugalu.modulos.identidad.infraestructura.salida.repositorio_postgres import (
    RepositorioPostgres,
)

router = APIRouter(tags=["identidad"])


@router.get(
    "/perfil",
    response_model=PerfilRespuesta,
    summary="Perfil del usuario autenticado",
    responses={
        401: {"model": RespuestaError, "description": "Token ausente, invalido o caducado"},
        404: {"model": RespuestaError, "description": "El usuario no tiene perfil"},
    },
)
async def obtener_perfil(
    request: Request, claims: Annotated[dict[str, Any], Depends(obtener_claims)]
) -> PerfilRespuesta:
    async with transaccion_con_identidad(request.app.state.pool, claims) as conexion:
        usuario = await ObtenerPerfil(RepositorioPostgres(conexion)).ejecutar(UUID(claims["sub"]))
    return PerfilRespuesta.desde_dominio(usuario)
