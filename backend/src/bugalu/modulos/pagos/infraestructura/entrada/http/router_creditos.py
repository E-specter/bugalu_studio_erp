from typing import Annotated, Any, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request

from bugalu.compartido.autenticacion import obtener_claims
from bugalu.compartido.base_datos import transaccion_con_identidad
from bugalu.compartido.errores import NoAutenticado
from bugalu.compartido.esquemas import RespuestaError
from bugalu.modulos.pagos.aplicacion.creditos.caso_de_uso import (
    AplicarCredito,
    DecidirDevolucion,
    ListarCreditos,
    ListarDevoluciones,
    MarcarDevolucionRealizada,
    ObtenerDevolucion,
    SolicitarDevolucion,
)
from bugalu.modulos.pagos.infraestructura.entrada.http.esquemas_creditos import (
    AplicacionCredito,
    Credito,
    DecisionDevolucion,
    NotaRealizada,
    SolicitudDevolucion,
)
from bugalu.modulos.pagos.infraestructura.salida.repositorio_creditos_postgres import (
    RepositorioCreditosPostgres,
)
from bugalu.modulos.reservas.infraestructura.entrada.http.esquemas import Devolucion, Reserva
from bugalu.modulos.reservas.infraestructura.salida.repositorio_postgres import (
    RepositorioReservasPostgres,
)

router = APIRouter(tags=["creditos"])

Claims = Annotated[dict[str, Any], Depends(obtener_claims)]

_DESCRIPCION = {
    401: "Token ausente, invalido o caducado",
    403: "Sin permiso para esta operacion o recurso",
    404: "No encontrado",
    409: "Conflicto con el estado actual",
    422: "Datos invalidos",
    503: "Autenticacion o base de datos no disponible",
}


def _respuestas(*codigos: int) -> dict[int | str, dict[str, Any]]:
    return {c: {"model": RespuestaError, "description": _DESCRIPCION[c]} for c in (*codigos, 503)}


def _pool(request: Request) -> Any:
    return request.app.state.pool


def _usuario(claims: dict[str, Any]) -> UUID:
    try:
        return UUID(str(claims["sub"]))
    except KeyError, ValueError:
        raise NoAutenticado("Sesion invalida.") from None


@router.get(
    "/creditos",
    response_model=list[Credito],
    response_model_exclude_unset=True,
    summary="Mis creditos; el administrador los de `id_cliente`",
    responses=_respuestas(401, 403, 422),
)
async def listar_creditos(
    request: Request, claims: Claims, id_cliente: Annotated[UUID | None, Query()] = None
) -> list[Credito]:
    async with transaccion_con_identidad(_pool(request), claims) as conexion:
        lista = await ListarCreditos(RepositorioCreditosPostgres(conexion)).ejecutar(
            _usuario(claims), id_cliente
        )
    return [Credito.desde_dominio(c) for c in lista]


@router.post(
    "/cuotas/{id_cuota}/credito",
    response_model=Reserva,
    response_model_exclude_unset=True,
    summary="Aplica credito propio a una cuota, al momento y sin validacion (dueno)",
    responses=_respuestas(401, 403, 404, 409, 422),
)
async def aplicar_credito(
    request: Request, claims: Claims, id_cuota: UUID, cuerpo: AplicacionCredito
) -> Reserva:
    async with transaccion_con_identidad(_pool(request), claims) as conexion:
        reserva = await AplicarCredito(
            RepositorioCreditosPostgres(conexion), RepositorioReservasPostgres(conexion)
        ).ejecutar(id_cuota, cuerpo.monto, cuerpo.id_credito)
    return Reserva.desde_dominio(reserva)


@router.post(
    "/creditos/{id_credito}/devolucion",
    response_model=Devolucion,
    response_model_exclude_unset=True,
    status_code=201,
    summary="Pide la devolucion de un credito de nivel 1 o de excepcion (dueno)",
    responses=_respuestas(401, 403, 404, 409, 422),
)
async def solicitar_devolucion(
    request: Request, claims: Claims, id_credito: UUID, cuerpo: SolicitudDevolucion
) -> Devolucion:
    async with transaccion_con_identidad(_pool(request), claims) as conexion:
        devolucion = await SolicitarDevolucion(RepositorioCreditosPostgres(conexion)).ejecutar(
            id_credito, cuerpo.motivo
        )
    return Devolucion.desde_dominio(devolucion)


@router.get(
    "/devoluciones",
    response_model=list[Devolucion],
    response_model_exclude_unset=True,
    summary="Devoluciones por estado, por defecto las pendientes (administrador)",
    responses=_respuestas(401, 403, 422),
)
async def listar_devoluciones(
    request: Request,
    claims: Claims,
    estado: Literal["pendiente", "aprobada", "rechazada", "realizada"] = "pendiente",
) -> list[Devolucion]:
    async with transaccion_con_identidad(_pool(request), claims) as conexion:
        lista = await ListarDevoluciones(RepositorioCreditosPostgres(conexion)).ejecutar(estado)
    return [Devolucion.desde_dominio(d) for d in lista]


@router.get(
    "/devoluciones/{id_devolucion}",
    response_model=Devolucion,
    response_model_exclude_unset=True,
    summary="Una devolucion: el administrador o su dueno",
    responses=_respuestas(401, 403, 404, 422),
)
async def obtener_devolucion(request: Request, claims: Claims, id_devolucion: UUID) -> Devolucion:
    async with transaccion_con_identidad(_pool(request), claims) as conexion:
        devolucion = await ObtenerDevolucion(RepositorioCreditosPostgres(conexion)).ejecutar(
            id_devolucion
        )
    return Devolucion.desde_dominio(devolucion)


@router.post(
    "/devoluciones/{id_devolucion}/decidir",
    response_model=Devolucion,
    response_model_exclude_unset=True,
    summary="Decide total, parcial o rechazo (administrador)",
    responses=_respuestas(401, 403, 404, 409, 422),
)
async def decidir_devolucion(
    request: Request, claims: Claims, id_devolucion: UUID, cuerpo: DecisionDevolucion
) -> Devolucion:
    async with transaccion_con_identidad(_pool(request), claims) as conexion:
        devolucion = await DecidirDevolucion(RepositorioCreditosPostgres(conexion)).ejecutar(
            id_devolucion, cuerpo.decision, cuerpo.monto, cuerpo.motivo
        )
    return Devolucion.desde_dominio(devolucion)


@router.post(
    "/devoluciones/{id_devolucion}/realizada",
    response_model=Devolucion,
    response_model_exclude_unset=True,
    summary="Marca la devolucion aprobada como realizada, con su nota (administrador)",
    responses=_respuestas(401, 403, 404, 409, 422),
)
async def marcar_realizada(
    request: Request, claims: Claims, id_devolucion: UUID, cuerpo: NotaRealizada
) -> Devolucion:
    async with transaccion_con_identidad(_pool(request), claims) as conexion:
        devolucion = await MarcarDevolucionRealizada(
            RepositorioCreditosPostgres(conexion)
        ).ejecutar(id_devolucion, cuerpo.nota)
    return Devolucion.desde_dominio(devolucion)
