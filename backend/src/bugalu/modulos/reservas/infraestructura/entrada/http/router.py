from datetime import UTC, datetime
from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request, Response

from bugalu.compartido.autenticacion import obtener_claims, obtener_claims_opcionales
from bugalu.compartido.base_datos import transaccion_con_identidad, transaccion_publica
from bugalu.compartido.esquemas import RespuestaError
from bugalu.modulos.reservas.aplicacion.actualizar_parametros.caso_de_uso import (
    ActualizarParametros,
)
from bugalu.modulos.reservas.aplicacion.consultar_disponibilidad.caso_de_uso import (
    ConsultarDisponibilidad,
)
from bugalu.modulos.reservas.aplicacion.listar_salas.caso_de_uso import ListarSalas
from bugalu.modulos.reservas.aplicacion.obtener_parametros.caso_de_uso import ObtenerParametros
from bugalu.modulos.reservas.aplicacion.publicar_franjas.caso_de_uso import PublicarFranjas
from bugalu.modulos.reservas.aplicacion.quitar_cierre.caso_de_uso import QuitarCierre
from bugalu.modulos.reservas.aplicacion.registrar_cierre.caso_de_uso import RegistrarCierre
from bugalu.modulos.reservas.aplicacion.retirar_franja.caso_de_uso import RetirarFranja
from bugalu.modulos.reservas.aplicacion.sugerir_franjas.caso_de_uso import SugerirFranjas
from bugalu.modulos.reservas.dominio.disponibilidad import Tramo as TramoDominio
from bugalu.modulos.reservas.infraestructura.entrada.http.esquemas import (
    CambiosParametros,
    Cierre,
    Disponibilidad,
    Franja,
    Instante,
    NuevasFranjas,
    NuevoCierre,
    Parametros,
    Sala,
    Tramo,
)
from bugalu.modulos.reservas.infraestructura.salida.repositorio_postgres import (
    RepositorioReservasPostgres,
)

router = APIRouter(tags=["reservas"])

Claims = Annotated[dict[str, Any], Depends(obtener_claims)]
ClaimsOpcionales = Annotated[dict[str, Any] | None, Depends(obtener_claims_opcionales)]

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


def _pool(request: Request) -> Any:
    return request.app.state.pool


@router.get(
    "/salas",
    response_model=list[Sala],
    summary="Salas activas (publico)",
    responses=_respuestas(),
)
async def listar_salas(request: Request) -> list[Sala]:
    async with transaccion_publica(_pool(request)) as conexion:
        salas = await ListarSalas(RepositorioReservasPostgres(conexion)).ejecutar()
    return [Sala.desde_dominio(s) for s in salas]


@router.get(
    "/disponibilidad",
    response_model=Disponibilidad,
    response_model_exclude_none=True,
    summary="Franjas, ocupados, cierres y minutos libres de un rango de hasta 42 dias (publico)",
    responses=_respuestas(401, 404, 422),
)
async def consultar_disponibilidad(
    request: Request,
    claims: ClaimsOpcionales,
    sala: UUID,
    desde: Annotated[Instante, Query()],
    hasta: Annotated[Instante, Query()],
) -> Disponibilidad:
    ahora = datetime.now(UTC)
    if claims is None:
        contexto = transaccion_publica(_pool(request))
    else:
        contexto = transaccion_con_identidad(_pool(request), claims)
    async with contexto as conexion:
        resultado = await ConsultarDisponibilidad(RepositorioReservasPostgres(conexion)).ejecutar(
            sala, desde, hasta, ahora, UUID(str(claims["sub"])) if claims else None
        )
    return Disponibilidad.desde_dominio(resultado)


@router.get(
    "/franjas/sugerencia",
    response_model=list[Tramo],
    summary="Plantilla sugerida: la ultima semana publicada desplazada (administrador)",
    responses=_respuestas(401, 403, 404, 422),
)
async def sugerir_franjas(
    request: Request,
    claims: Claims,
    sala: UUID,
    semana: Annotated[str, Query(pattern=r"^\d{4}-W\d{2}$")],
) -> list[Tramo]:
    async with transaccion_con_identidad(_pool(request), claims) as conexion:
        tramos = await SugerirFranjas(RepositorioReservasPostgres(conexion)).ejecutar(sala, semana)
    return [Tramo(inicio=t.inicio, fin=t.fin) for t in tramos]


@router.post(
    "/franjas",
    response_model=list[Franja],
    status_code=201,
    summary="Publica un lote de franjas (administrador)",
    responses=_respuestas(401, 403, 404, 409, 422),
)
async def publicar_franjas(request: Request, claims: Claims, cuerpo: NuevasFranjas) -> list[Franja]:
    async with transaccion_con_identidad(_pool(request), claims) as conexion:
        franjas = await PublicarFranjas(RepositorioReservasPostgres(conexion)).ejecutar(
            cuerpo.id_sala, [TramoDominio(f.inicio, f.fin) for f in cuerpo.franjas]
        )
    return [Franja(id=f.id, id_sala=f.id_sala, inicio=f.inicio, fin=f.fin) for f in franjas]


@router.delete(
    "/franjas/{id_franja}",
    status_code=204,
    summary="Retira una franja sin reservas vigentes (administrador)",
    responses=_respuestas(401, 403, 404, 409, 422),
)
async def retirar_franja(request: Request, claims: Claims, id_franja: UUID) -> Response:
    async with transaccion_con_identidad(_pool(request), claims) as conexion:
        await RetirarFranja(RepositorioReservasPostgres(conexion)).ejecutar(id_franja)
    return Response(status_code=204)


@router.post(
    "/cierres",
    response_model=Cierre,
    status_code=201,
    summary="Cierra un dia u horas de la sala (administrador)",
    responses=_respuestas(401, 403, 404, 409, 422),
)
async def registrar_cierre(request: Request, claims: Claims, cuerpo: NuevoCierre) -> Cierre:
    async with transaccion_con_identidad(_pool(request), claims) as conexion:
        c = await RegistrarCierre(RepositorioReservasPostgres(conexion)).ejecutar(
            cuerpo.id_sala, TramoDominio(cuerpo.inicio, cuerpo.fin), cuerpo.motivo
        )
    return Cierre(id=c.id, id_sala=c.id_sala, inicio=c.inicio, fin=c.fin, motivo=c.motivo)


@router.delete(
    "/cierres/{id_cierre}",
    status_code=204,
    summary="Quita un cierre (administrador)",
    responses=_respuestas(401, 403, 404, 422),
)
async def quitar_cierre(request: Request, claims: Claims, id_cierre: UUID) -> Response:
    async with transaccion_con_identidad(_pool(request), claims) as conexion:
        await QuitarCierre(RepositorioReservasPostgres(conexion)).ejecutar(id_cierre)
    return Response(status_code=204)


@router.get(
    "/parametros",
    response_model=Parametros,
    summary="Parametros de reserva (administrador)",
    responses=_respuestas(401, 403),
)
async def obtener_parametros(request: Request, claims: Claims) -> Parametros:
    async with transaccion_con_identidad(_pool(request), claims) as conexion:
        valores = await ObtenerParametros(RepositorioReservasPostgres(conexion)).ejecutar()
    return Parametros(**valores)


@router.patch(
    "/parametros",
    response_model=Parametros,
    summary="Ajusta parametros de reserva, enteros mayores que 0 (administrador)",
    responses=_respuestas(401, 403, 422),
)
async def actualizar_parametros(
    request: Request, claims: Claims, cuerpo: CambiosParametros
) -> Parametros:
    async with transaccion_con_identidad(_pool(request), claims) as conexion:
        valores = await ActualizarParametros(RepositorioReservasPostgres(conexion)).ejecutar(
            cuerpo.model_dump(exclude_unset=True)
        )
    return Parametros(**valores)
