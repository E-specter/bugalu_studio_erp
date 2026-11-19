from datetime import UTC, datetime
from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request

from bugalu.compartido.autenticacion import obtener_claims
from bugalu.compartido.base_datos import transaccion_con_identidad
from bugalu.compartido.esquemas import RespuestaError
from bugalu.modulos.asesorias.aplicacion.agendar.caso_de_uso import AgendarAsesoria
from bugalu.modulos.asesorias.aplicacion.consultar.caso_de_uso import (
    ListarAsesorias,
    ListarMisAsesorias,
    ObtenerAsesoria,
)
from bugalu.modulos.asesorias.aplicacion.encuentro.caso_de_uso import CambiarEncuentro
from bugalu.modulos.asesorias.infraestructura.entrada.http import esquemas_agenda as e
from bugalu.modulos.asesorias.infraestructura.salida.repositorio_agenda_postgres import (
    RepositorioAgendaPostgres,
)
from bugalu.modulos.reservas.infraestructura.entrada.http.esquemas import Instante

router = APIRouter(tags=["asesorias"])

Claims = Annotated[dict[str, Any], Depends(obtener_claims)]
_DESCRIPCION = {
    401: "Token ausente, invalido o caducado",
    403: "Sin permiso para esta operacion",
    404: "No encontrado",
    409: "Conflicto con el estado actual",
    422: "Datos invalidos",
    503: "Autenticacion o base de datos no disponible",
}


def _respuestas(*codigos: int) -> dict[int | str, dict[str, Any]]:
    return {c: {"model": RespuestaError, "description": _DESCRIPCION[c]} for c in (*codigos, 503)}


def _pool(request: Request) -> Any:
    return request.app.state.pool


@router.post(
    "/asesorias",
    response_model=e.Asesoria,
    response_model_exclude_none=True,
    status_code=201,
    summary="Agenda una asesoria (pre_reservada, una cuota); no es para el profesional",
    responses=_respuestas(401, 403, 404, 409, 422),
)
async def agendar(request: Request, claims: Claims, cuerpo: e.NuevaAsesoria) -> e.Asesoria:
    async with transaccion_con_identidad(_pool(request), claims) as conexion:
        creada = await AgendarAsesoria(RepositorioAgendaPostgres(conexion)).ejecutar(
            UUID(str(claims["sub"])),
            cuerpo.id_profesional,
            cuerpo.inicio,
            cuerpo.duracion,
            cuerpo.modalidad,
            cuerpo.version_condiciones,
            datetime.now(UTC),
        )
    return e.Asesoria.desde_dominio(creada)


@router.get(
    "/asesorias/mias",
    response_model=list[e.AsesoriaResumen],
    response_model_exclude_none=True,
    summary="Mis asesorias (cualquier cuenta que no sea profesional)",
    responses=_respuestas(401, 403),
)
async def mias(request: Request, claims: Claims) -> list[e.AsesoriaResumen]:
    async with transaccion_con_identidad(_pool(request), claims) as conexion:
        lista = await ListarMisAsesorias(RepositorioAgendaPostgres(conexion)).ejecutar()
    ahora = datetime.now(UTC)
    return [e.AsesoriaResumen.desde_dominio(a, ahora) for a in lista]


@router.get(
    "/asesorias",
    response_model=list[e.AsesoriaResumen],
    response_model_exclude_none=True,
    summary="Asesorias del profesional (solo las suyas) o de todos (administrador)",
    responses=_respuestas(401, 403, 422),
)
async def listar(
    request: Request,
    claims: Claims,
    estado: str | None = None,
    desde: Annotated[Instante | None, Query()] = None,
    hasta: Annotated[Instante | None, Query()] = None,
    id_profesional: UUID | None = None,
    por_cerrar: bool = False,
) -> list[e.AsesoriaResumen]:
    ahora = datetime.now(UTC)
    async with transaccion_con_identidad(_pool(request), claims) as conexion:
        lista = await ListarAsesorias(RepositorioAgendaPostgres(conexion)).ejecutar(
            estado, desde, hasta, id_profesional, por_cerrar, ahora
        )
    return [e.AsesoriaResumen.desde_dominio(a, ahora) for a in lista]


@router.get(
    "/asesorias/{id_asesoria}",
    response_model=e.Asesoria,
    response_model_exclude_none=True,
    summary="Una asesoria: su dueno, su profesional o el administrador",
    responses=_respuestas(401, 404),
)
async def obtener(request: Request, claims: Claims, id_asesoria: UUID) -> e.Asesoria:
    async with transaccion_con_identidad(_pool(request), claims) as conexion:
        a = await ObtenerAsesoria(RepositorioAgendaPostgres(conexion)).ejecutar(
            UUID(str(claims["sub"])), id_asesoria
        )
    return e.Asesoria.desde_dominio(a)


@router.patch(
    "/asesorias/{id_asesoria}/encuentro",
    response_model=e.Asesoria,
    response_model_exclude_none=True,
    summary="Modalidad, lugar o enlace de Meet (su profesional o el administrador)",
    responses=_respuestas(401, 403, 404, 409, 422),
)
async def cambiar_encuentro(
    request: Request, claims: Claims, id_asesoria: UUID, cuerpo: e.CambiosEncuentro
) -> e.Asesoria:
    async with transaccion_con_identidad(_pool(request), claims) as conexion:
        a = await CambiarEncuentro(RepositorioAgendaPostgres(conexion)).ejecutar(
            UUID(str(claims["sub"])), id_asesoria, cuerpo.cambios()
        )
    return e.Asesoria.desde_dominio(a)
