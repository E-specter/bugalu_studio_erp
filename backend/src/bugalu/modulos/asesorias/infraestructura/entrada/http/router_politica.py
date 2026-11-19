"""Politica de RF-18 en `/reservas/{id}/...`: acepta una reserva de sala o una asesoria.

Vive en `asesorias` porque este modulo depende de `reservas` y no al reves; para la sala usa
los mismos casos de uso de `reservas`, sin cambios. El tipo lo decide `tipo_de_reserva`.
"""

from datetime import UTC, datetime
from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from bugalu.compartido.autenticacion import obtener_claims
from bugalu.compartido.base_datos import transaccion_con_identidad
from bugalu.compartido.esquemas import RespuestaError
from bugalu.compartido.roles import SOLO_CLIENTES
from bugalu.modulos.asesorias.aplicacion.politica.caso_de_uso import (
    AplicarExcepcionAsesoria,
    CancelarAsesoria,
    ElegirDevolucionAsesoria,
    MarcarInasistenciaAsesoria,
    ReprogramarAsesoria,
    SimularReprogramacionAsesoria,
    VistaCancelacionAsesoria,
)
from bugalu.modulos.asesorias.infraestructura.entrada.http import esquemas_agenda as e
from bugalu.modulos.asesorias.infraestructura.salida.repositorio_agenda_postgres import (
    RepositorioAgendaPostgres,
)
from bugalu.modulos.reservas.aplicacion.aplicar_excepcion.caso_de_uso import AplicarExcepcion
from bugalu.modulos.reservas.aplicacion.cancelar_reserva.caso_de_uso import CancelarReserva
from bugalu.modulos.reservas.aplicacion.elegir_estudio.caso_de_uso import (
    ElegirDevolucionDelEstudio,
)
from bugalu.modulos.reservas.aplicacion.marcar_inasistencia.caso_de_uso import MarcarInasistencia
from bugalu.modulos.reservas.aplicacion.reprogramar_reserva.caso_de_uso import (
    ReprogramarReserva,
    SimularReprogramacion,
)
from bugalu.modulos.reservas.aplicacion.vista_cancelacion.caso_de_uso import (
    VistaCancelacion as VistaCancelacionCaso,
)
from bugalu.modulos.reservas.infraestructura.entrada.http.esquemas import (
    Cancelacion,
    EleccionEstudio,
    Instante,
    NuevaExcepcion,
    NuevoHorario,
    Reprogramacion,
    Reserva,
    VistaCancelacion,
    VistaReprogramacion,
)
from bugalu.modulos.reservas.infraestructura.salida.cotizador_catalogo import CotizadorCatalogo
from bugalu.modulos.reservas.infraestructura.salida.repositorio_postgres import (
    RepositorioReservasPostgres,
)

router = APIRouter(tags=["reservas", "asesorias"])

Claims = Annotated[dict[str, Any], Depends(obtener_claims)]
_DESCRIPCION = {
    401: "Token ausente, invalido o caducado",
    403: "Sin permiso para esta operacion o recurso",
    404: "No encontrado",
    409: "Conflicto con el estado actual",
    422: "Datos invalidos",
    503: "Servicio de autenticacion o base de datos no disponible",
}


def _respuestas(*codigos: int) -> dict[int | str, dict[str, Any]]:
    return {c: {"model": RespuestaError, "description": _DESCRIPCION[c]} for c in (*codigos, 503)}


def _pool(request: Request) -> Any:
    return request.app.state.pool


def _sub(claims: dict[str, Any]) -> UUID:
    return UUID(str(claims["sub"]))


def _reserva(r: Any) -> JSONResponse:
    return JSONResponse(jsonable_encoder(Reserva.desde_dominio(r), exclude_unset=True))


def _asesoria(a: Any) -> JSONResponse:
    return JSONResponse(jsonable_encoder(e.Asesoria.desde_dominio(a), exclude_none=True))


def _json(modelo: BaseModel) -> JSONResponse:
    return JSONResponse(jsonable_encoder(modelo))


async def _es_asesoria(repo: RepositorioAgendaPostgres, id_reserva: UUID) -> bool:
    return await repo.tipo_de_reserva(id_reserva) == "asesoria"


@router.get(
    "/reservas/{id_reserva}/cancelacion",
    dependencies=SOLO_CLIENTES,
    response_model=VistaCancelacion,
    summary="Vista previa de la cancelacion (sala o asesoria): nivel, retencion y credito",
    responses=_respuestas(401, 403, 404, 409, 422),
)
async def vista_cancelacion(
    request: Request,
    claims: Claims,
    id_reserva: UUID,
    aviso_en: Annotated[Instante | None, Query()] = None,
) -> JSONResponse:
    async with transaccion_con_identidad(_pool(request), claims) as conexion:
        agenda = RepositorioAgendaPostgres(conexion)
        if await _es_asesoria(agenda, id_reserva):
            vista = await VistaCancelacionAsesoria(agenda).ejecutar(id_reserva, aviso_en)
        else:
            vista = await VistaCancelacionCaso(RepositorioReservasPostgres(conexion)).ejecutar(
                id_reserva, aviso_en
            )
    return _json(VistaCancelacion.desde_dominio(vista))


@router.post(
    "/reservas/{id_reserva}/cancelar",
    dependencies=SOLO_CLIENTES,
    response_model=Reserva | e.Asesoria,
    summary="Cancela con la politica de niveles (RF-18); en una asesoria responde `Asesoria`",
    responses=_respuestas(401, 403, 404, 409, 422),
)
async def cancelar(
    request: Request, claims: Claims, id_reserva: UUID, cuerpo: Cancelacion | None = None
) -> JSONResponse:
    cuerpo = cuerpo or Cancelacion()
    async with transaccion_con_identidad(_pool(request), claims) as conexion:
        agenda = RepositorioAgendaPostgres(conexion)
        if await _es_asesoria(agenda, id_reserva):
            a = await CancelarAsesoria(agenda).ejecutar(
                _sub(claims), id_reserva, cuerpo.nota, cuerpo.nivel_esperado, cuerpo.por,
                cuerpo.aviso_en,
            )  # fmt: skip
            return _asesoria(a)
        r = await CancelarReserva(RepositorioReservasPostgres(conexion)).ejecutar(
            id_reserva, cuerpo.nota, cuerpo.nivel_esperado, cuerpo.por, cuerpo.aviso_en
        )
    return _reserva(r)


@router.post(
    "/reservas/{id_reserva}/inasistencia",
    response_model=Reserva | e.Asesoria,
    summary="Marca la inasistencia: el personal (sala), o el profesional de la asesoria o el "
    "administrador, desde la tolerancia",
    responses=_respuestas(401, 403, 404, 409),
)
async def marcar_inasistencia(request: Request, claims: Claims, id_reserva: UUID) -> JSONResponse:
    async with transaccion_con_identidad(_pool(request), claims) as conexion:
        agenda = RepositorioAgendaPostgres(conexion)
        if await _es_asesoria(agenda, id_reserva):
            return _asesoria(
                await MarcarInasistenciaAsesoria(agenda).ejecutar(_sub(claims), id_reserva)
            )
        r = await MarcarInasistencia(RepositorioReservasPostgres(conexion)).ejecutar(id_reserva)
    return _reserva(r)


@router.post(
    "/reservas/{id_reserva}/excepcion",
    response_model=Reserva | e.Asesoria,
    summary="Trata como nivel 1 una cancelacion de nivel 2 o 3, o una inasistencia (administrador)",
    responses=_respuestas(401, 403, 404, 409, 422),
)
async def aplicar_excepcion(
    request: Request, claims: Claims, id_reserva: UUID, cuerpo: NuevaExcepcion
) -> JSONResponse:
    async with transaccion_con_identidad(_pool(request), claims) as conexion:
        agenda = RepositorioAgendaPostgres(conexion)
        if await _es_asesoria(agenda, id_reserva):
            return _asesoria(
                await AplicarExcepcionAsesoria(agenda).ejecutar(
                    _sub(claims), id_reserva, cuerpo.motivo
                )
            )
        r = await AplicarExcepcion(RepositorioReservasPostgres(conexion)).ejecutar(
            id_reserva, cuerpo.motivo
        )
    return _reserva(r)


@router.post(
    "/reservas/{id_reserva}/reprogramar/simular",
    dependencies=SOLO_CLIENTES,
    response_model=VistaReprogramacion | e.VistaReprogramacionAsesoria,
    summary="Vista previa de reprogramar (sala o asesoria); sin cambiar nada",
    responses=_respuestas(401, 403, 404, 409, 422),
)
async def simular_reprogramacion(
    request: Request, claims: Claims, id_reserva: UUID, cuerpo: NuevoHorario
) -> JSONResponse:
    ahora = datetime.now(UTC)
    async with transaccion_con_identidad(_pool(request), claims) as conexion:
        agenda = RepositorioAgendaPostgres(conexion)
        if await _es_asesoria(agenda, id_reserva):
            v = await SimularReprogramacionAsesoria(agenda).ejecutar(
                id_reserva, cuerpo.inicio, ahora
            )
            return _json(
                e.VistaReprogramacionAsesoria(
                    **{**vars(v), "precio": e.PrecioAsesoria.model_validate(v.precio)}
                )
            )
        vista = await SimularReprogramacion(
            RepositorioReservasPostgres(conexion), CotizadorCatalogo(conexion)
        ).ejecutar(id_reserva, cuerpo.inicio, ahora)
    return _json(VistaReprogramacion.desde_dominio(vista))


@router.post(
    "/reservas/{id_reserva}/reprogramar",
    dependencies=SOLO_CLIENTES,
    response_model=Reserva | e.Asesoria,
    summary="Reprograma con la politica de niveles (RF-18); una asesoria, con el mismo profesional",
    responses=_respuestas(401, 403, 404, 409, 422),
)
async def reprogramar(
    request: Request, claims: Claims, id_reserva: UUID, cuerpo: Reprogramacion
) -> JSONResponse:
    ahora = datetime.now(UTC)
    async with transaccion_con_identidad(_pool(request), claims) as conexion:
        agenda = RepositorioAgendaPostgres(conexion)
        if await _es_asesoria(agenda, id_reserva):
            return _asesoria(
                await ReprogramarAsesoria(agenda).ejecutar(
                    _sub(claims),
                    id_reserva,
                    cuerpo.inicio,
                    cuerpo.nivel_esperado,
                    cuerpo.total_esperado,
                    ahora,
                )  # fmt: skip
            )
        r = await ReprogramarReserva(
            RepositorioReservasPostgres(conexion), CotizadorCatalogo(conexion)
        ).ejecutar(id_reserva, cuerpo.inicio, cuerpo.nivel_esperado, cuerpo.total_esperado, ahora)
    return _reserva(r)


@router.post(
    "/reservas/{id_reserva}/eleccion-estudio",
    dependencies=SOLO_CLIENTES,
    response_model=Reserva | e.Asesoria,
    summary="Tras una cancelacion del estudio, elige la devolucion integra (dueno o administrador)",
    responses=_respuestas(401, 403, 404, 409, 422),
)
async def elegir_devolucion_del_estudio(
    request: Request, claims: Claims, id_reserva: UUID, cuerpo: EleccionEstudio
) -> JSONResponse:
    async with transaccion_con_identidad(_pool(request), claims) as conexion:
        agenda = RepositorioAgendaPostgres(conexion)
        if await _es_asesoria(agenda, id_reserva):
            return _asesoria(
                await ElegirDevolucionAsesoria(agenda).ejecutar(_sub(claims), id_reserva)
            )
        r = await ElegirDevolucionDelEstudio(RepositorioReservasPostgres(conexion)).ejecutar(
            id_reserva
        )
    return _reserva(r)
