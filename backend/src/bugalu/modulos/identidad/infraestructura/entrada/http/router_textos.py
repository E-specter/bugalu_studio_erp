from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, Request, Response

from bugalu.compartido.autenticacion import obtener_claims
from bugalu.compartido.base_datos import transaccion_con_identidad, transaccion_publica
from bugalu.compartido.esquemas import RespuestaError
from bugalu.modulos.identidad.aplicacion.textos_legales import (
    AceptarTextos,
    ListarAceptacionesDeUsuario,
    ListarMisAceptaciones,
    ListarTextos,
    ObtenerTexto,
    PublicarTexto,
    RetirarTexto,
)
from bugalu.modulos.identidad.infraestructura.entrada.http.esquemas_textos import (
    Aceptacion,
    NuevaAceptacion,
    NuevoTexto,
    TextoLegal,
    TextoResumen,
)
from bugalu.modulos.identidad.infraestructura.salida.repositorio_postgres import (
    RepositorioPostgres,
)
from bugalu.modulos.identidad.infraestructura.salida.repositorio_textos_postgres import (
    RepositorioTextosPostgres,
)

router = APIRouter(tags=["textos-legales"])

Claims = Annotated[dict[str, Any], Depends(obtener_claims)]

_DESCRIPCION = {
    401: "Token ausente, invalido o caducado",
    403: "Se requiere el rol administrador",
    404: "No encontrado",
    409: "Conflicto con el estado actual",
    422: "Datos invalidos",
    503: "Servicio de autenticacion o base de datos no disponible",
}


def _respuestas(*codigos: int) -> dict[int | str, dict[str, Any]]:
    return {c: {"model": RespuestaError, "description": _DESCRIPCION[c]} for c in (*codigos, 503)}


def _yo(claims: dict[str, Any]) -> UUID:
    return UUID(claims["sub"])


@router.get(
    "/textos-legales",
    response_model=list[TextoResumen],
    summary="Textos legales vigentes y programados (publico)",
    responses=_respuestas(),
)
async def listar_textos(request: Request) -> list[TextoResumen]:
    async with transaccion_publica(request.app.state.pool) as conexion:
        textos = await ListarTextos(RepositorioTextosPostgres(conexion)).ejecutar()
    return [TextoResumen.desde_dominio(t) for t in textos]


@router.post(
    "/textos-legales",
    response_model=TextoLegal,
    status_code=201,
    summary="Publica una version de un texto legal (administrador)",
    responses=_respuestas(401, 403, 409, 422),
)
async def publicar_texto(request: Request, claims: Claims, cuerpo: NuevoTexto) -> TextoLegal:
    async with transaccion_con_identidad(request.app.state.pool, claims) as conexion:
        texto = await PublicarTexto(
            RepositorioPostgres(conexion), RepositorioTextosPostgres(conexion)
        ).ejecutar(
            _yo(claims),
            cuerpo.tipo,
            cuerpo.version,
            cuerpo.tipo_cambio,
            cuerpo.contenido,
            cuerpo.resumenes,
            cuerpo.resumen_cambios,
            cuerpo.vigente_desde,
        )
    return TextoLegal.desde_dominio(texto)


@router.get(
    "/textos-legales/{tipo}/versiones/{version}",
    response_model=TextoLegal,
    summary="Una version exacta de un texto legal, con su HTML saneado (publico)",
    responses=_respuestas(404),
)
async def obtener_texto(request: Request, tipo: str, version: str) -> TextoLegal:
    async with transaccion_publica(request.app.state.pool) as conexion:
        texto = await ObtenerTexto(RepositorioTextosPostgres(conexion)).ejecutar(tipo, version)
    return TextoLegal.desde_dominio(texto)


@router.delete(
    "/textos-legales/{tipo}/versiones/{version}",
    status_code=204,
    summary="Retira una version programada que aun no esta vigente (administrador)",
    responses=_respuestas(401, 403, 404, 409),
)
async def retirar_texto(request: Request, claims: Claims, tipo: str, version: str) -> Response:
    async with transaccion_con_identidad(request.app.state.pool, claims) as conexion:
        await RetirarTexto(
            RepositorioPostgres(conexion), RepositorioTextosPostgres(conexion)
        ).ejecutar(_yo(claims), tipo, version)
    return Response(status_code=204)


@router.post(
    "/aceptaciones",
    response_model=list[Aceptacion],
    status_code=201,
    summary="Registra la aceptacion de la version vigente de los textos del registro",
    responses=_respuestas(401, 409, 422),
)
async def aceptar_textos(
    request: Request, claims: Claims, cuerpo: NuevaAceptacion
) -> list[Aceptacion]:
    async with transaccion_con_identidad(request.app.state.pool, claims) as conexion:
        aceptaciones = await AceptarTextos(RepositorioTextosPostgres(conexion)).ejecutar(
            [(t.tipo, t.version) for t in cuerpo.textos]
        )
    return [Aceptacion.desde_dominio(a) for a in aceptaciones]


@router.get(
    "/aceptaciones/mias",
    response_model=list[Aceptacion],
    summary="Lo que aceptó el usuario autenticado, lo mas reciente primero",
    responses=_respuestas(401),
)
async def mis_aceptaciones(request: Request, claims: Claims) -> list[Aceptacion]:
    async with transaccion_con_identidad(request.app.state.pool, claims) as conexion:
        aceptaciones = await ListarMisAceptaciones(RepositorioTextosPostgres(conexion)).ejecutar(
            _yo(claims)
        )
    return [Aceptacion.desde_dominio(a) for a in aceptaciones]


@router.get(
    "/usuarios/{id_usuario}/aceptaciones",
    response_model=list[Aceptacion],
    summary="Aceptaciones de un usuario (administrador)",
    responses=_respuestas(401, 403, 404, 422),
)
async def aceptaciones_de_usuario(
    request: Request, claims: Claims, id_usuario: UUID
) -> list[Aceptacion]:
    async with transaccion_con_identidad(request.app.state.pool, claims) as conexion:
        aceptaciones = await ListarAceptacionesDeUsuario(
            RepositorioPostgres(conexion), RepositorioTextosPostgres(conexion)
        ).ejecutar(_yo(claims), id_usuario)
    return [Aceptacion.desde_dominio(a) for a in aceptaciones]
