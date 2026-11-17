from datetime import UTC, datetime
from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request, Response

from bugalu.compartido.autenticacion import obtener_claims, obtener_claims_opcionales
from bugalu.compartido.base_datos import transaccion_con_identidad, transaccion_publica
from bugalu.compartido.esquemas import RespuestaError
from bugalu.modulos.catalogo.infraestructura.entrada.http.esquemas import (
    CambiosParametros,
    Parametros,
)
from bugalu.modulos.reservas.aplicacion.actualizar_parametros.caso_de_uso import (
    ActualizarParametros,
)
from bugalu.modulos.reservas.aplicacion.aplicar_excepcion.caso_de_uso import AplicarExcepcion
from bugalu.modulos.reservas.aplicacion.cancelar_reserva.caso_de_uso import CancelarReserva
from bugalu.modulos.reservas.aplicacion.consultar_disponibilidad.caso_de_uso import (
    ConsultarDisponibilidad,
)
from bugalu.modulos.reservas.aplicacion.elegir_estudio.caso_de_uso import (
    ElegirDevolucionDelEstudio,
)
from bugalu.modulos.reservas.aplicacion.listar_mis_reservas.caso_de_uso import ListarMisReservas
from bugalu.modulos.reservas.aplicacion.listar_reservas.caso_de_uso import ListarReservas
from bugalu.modulos.reservas.aplicacion.listar_salas.caso_de_uso import ListarSalas
from bugalu.modulos.reservas.aplicacion.marcar_inasistencia.caso_de_uso import MarcarInasistencia
from bugalu.modulos.reservas.aplicacion.obtener_parametros.caso_de_uso import ObtenerParametros
from bugalu.modulos.reservas.aplicacion.obtener_reserva.caso_de_uso import ObtenerReserva
from bugalu.modulos.reservas.aplicacion.publicar_franjas.caso_de_uso import PublicarFranjas
from bugalu.modulos.reservas.aplicacion.quitar_cierre.caso_de_uso import QuitarCierre
from bugalu.modulos.reservas.aplicacion.registrar_cierre.caso_de_uso import RegistrarCierre
from bugalu.modulos.reservas.aplicacion.registrar_reserva.caso_de_uso import RegistrarReserva
from bugalu.modulos.reservas.aplicacion.reprogramar_reserva.caso_de_uso import (
    ReprogramarReserva,
    SimularReprogramacion,
)
from bugalu.modulos.reservas.aplicacion.retirar_franja.caso_de_uso import RetirarFranja
from bugalu.modulos.reservas.aplicacion.sugerir_franjas.caso_de_uso import SugerirFranjas
from bugalu.modulos.reservas.aplicacion.vista_cancelacion.caso_de_uso import (
    VistaCancelacion as VistaCancelacionCaso,
)
from bugalu.modulos.reservas.dominio.disponibilidad import Tramo as TramoDominio
from bugalu.modulos.reservas.infraestructura.entrada.http.esquemas import (
    Cancelacion,
    Cierre,
    Disponibilidad,
    EleccionEstudio,
    Franja,
    Instante,
    NuevaExcepcion,
    NuevaReserva,
    NuevasFranjas,
    NuevoCierre,
    NuevoHorario,
    Reprogramacion,
    Reserva,
    Sala,
    Tramo,
    VistaCancelacion,
    VistaReprogramacion,
)
from bugalu.modulos.reservas.infraestructura.salida.cotizador_catalogo import CotizadorCatalogo
from bugalu.modulos.reservas.infraestructura.salida.repositorio_postgres import (
    RepositorioReservasPostgres,
)

router = APIRouter(tags=["reservas"])

Claims = Annotated[dict[str, Any], Depends(obtener_claims)]
ClaimsOpcionales = Annotated[dict[str, Any] | None, Depends(obtener_claims_opcionales)]

_DESCRIPCION = {
    401: "Token ausente, invalido o caducado",
    403: "Sin permiso para esta operacion o recurso",
    404: "No encontrado",
    409: "Conflicto con el estado actual",
    422: "Datos invalidos",
    428: "El cambio es sensible: requiere vista previa y confirmacion (RF-20)",
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
    excluir_reserva: Annotated[UUID | None, Query()] = None,
) -> Disponibilidad:
    ahora = datetime.now(UTC)
    if claims is None:
        contexto = transaccion_publica(_pool(request))
    else:
        contexto = transaccion_con_identidad(_pool(request), claims)
    async with contexto as conexion:
        resultado = await ConsultarDisponibilidad(RepositorioReservasPostgres(conexion)).ejecutar(
            sala, desde, hasta, ahora, UUID(str(claims["sub"])) if claims else None, excluir_reserva
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
    responses=_respuestas(401, 403, 422, 428),
)
async def actualizar_parametros(
    request: Request, claims: Claims, cuerpo: CambiosParametros
) -> Parametros:
    async with transaccion_con_identidad(_pool(request), claims) as conexion:
        valores = await ActualizarParametros(RepositorioReservasPostgres(conexion)).ejecutar(
            cuerpo.model_dump(exclude_unset=True)
        )
    return Parametros(**valores)


@router.post(
    "/reservas",
    response_model=Reserva,
    response_model_exclude_unset=True,
    status_code=201,
    summary="Reserva un tramo de la sala; el precio y las cuotas los calcula el sistema (cliente)",
    responses=_respuestas(401, 403, 409, 422),
)
async def registrar_reserva(request: Request, claims: Claims, cuerpo: NuevaReserva) -> Reserva:
    ahora = datetime.now(UTC)
    async with transaccion_con_identidad(_pool(request), claims) as conexion:
        reserva = await RegistrarReserva(
            RepositorioReservasPostgres(conexion), CotizadorCatalogo(conexion)
        ).ejecutar(
            cuerpo.id_sala,
            cuerpo.id_servicio,
            cuerpo.inicio,
            cuerpo.fin,
            cuerpo.especialistas,
            cuerpo.detalle,
            cuerpo.version_condiciones,
            ahora,
        )
    return Reserva.desde_dominio(reserva)


@router.get(
    "/reservas/mias",
    response_model=list[Reserva],
    response_model_exclude_unset=True,
    summary="Mis reservas con estado, precio, cuotas y fecha limite",
    responses=_respuestas(401),
)
async def listar_mis_reservas(request: Request, claims: Claims) -> list[Reserva]:
    async with transaccion_con_identidad(_pool(request), claims) as conexion:
        reservas = await ListarMisReservas(RepositorioReservasPostgres(conexion)).ejecutar()
    return [Reserva.desde_dominio(r) for r in reservas]


@router.get(
    "/reservas",
    response_model=list[Reserva],
    response_model_exclude_unset=True,
    summary="Reservas de un rango de hasta 42 dias con su cliente (personal o administrador)",
    responses=_respuestas(401, 403, 422),
)
async def listar_reservas(
    request: Request,
    claims: Claims,
    desde: Annotated[Instante, Query()],
    hasta: Annotated[Instante, Query()],
) -> list[Reserva]:
    async with transaccion_con_identidad(_pool(request), claims) as conexion:
        reservas = await ListarReservas(RepositorioReservasPostgres(conexion)).ejecutar(
            desde, hasta
        )
    return [Reserva.desde_dominio(r) for r in reservas]


@router.get(
    "/reservas/{id_reserva}",
    response_model=Reserva,
    response_model_exclude_unset=True,
    summary="Una reserva: su dueno, el personal o un administrador",
    responses=_respuestas(401, 403, 404, 422),
)
async def obtener_reserva(request: Request, claims: Claims, id_reserva: UUID) -> Reserva:
    async with transaccion_con_identidad(_pool(request), claims) as conexion:
        reserva = await ObtenerReserva(RepositorioReservasPostgres(conexion)).ejecutar(id_reserva)
    return Reserva.desde_dominio(reserva)


@router.get(
    "/reservas/{id_reserva}/cancelacion",
    response_model=VistaCancelacion,
    summary="Vista previa de la cancelacion: nivel, retencion y credito; sin cambiar nada",
    responses=_respuestas(401, 403, 404, 409, 422),
)
async def vista_cancelacion(
    request: Request,
    claims: Claims,
    id_reserva: UUID,
    aviso_en: Annotated[Instante | None, Query()] = None,
) -> VistaCancelacion:
    async with transaccion_con_identidad(_pool(request), claims) as conexion:
        vista = await VistaCancelacionCaso(RepositorioReservasPostgres(conexion)).ejecutar(
            id_reserva, aviso_en
        )
    return VistaCancelacion.desde_dominio(vista)


@router.post(
    "/reservas/{id_reserva}/cancelar",
    response_model=Reserva,
    response_model_exclude_unset=True,
    summary="Cancela con la politica de niveles (RF-18): el dueno con su nivel esperado; "
    "el administrador por el estudio o en nombre del cliente",
    responses=_respuestas(401, 403, 404, 409, 422),
)
async def cancelar_reserva(
    request: Request, claims: Claims, id_reserva: UUID, cuerpo: Cancelacion | None = None
) -> Reserva:
    cuerpo = cuerpo or Cancelacion()
    async with transaccion_con_identidad(_pool(request), claims) as conexion:
        reserva = await CancelarReserva(RepositorioReservasPostgres(conexion)).ejecutar(
            id_reserva, cuerpo.nota, cuerpo.nivel_esperado, cuerpo.por, cuerpo.aviso_en
        )
    return Reserva.desde_dominio(reserva)


@router.post(
    "/reservas/{id_reserva}/inasistencia",
    response_model=Reserva,
    response_model_exclude_unset=True,
    summary="Marca la inasistencia, desde la tolerancia hasta el fin (personal o administrador)",
    responses=_respuestas(401, 403, 404, 409),
)
async def marcar_inasistencia(request: Request, claims: Claims, id_reserva: UUID) -> Reserva:
    async with transaccion_con_identidad(_pool(request), claims) as conexion:
        reserva = await MarcarInasistencia(RepositorioReservasPostgres(conexion)).ejecutar(
            id_reserva
        )
    return Reserva.desde_dominio(reserva)


@router.post(
    "/reservas/{id_reserva}/excepcion",
    response_model=Reserva,
    response_model_exclude_unset=True,
    summary="Trata como nivel 1 una cancelacion de nivel 2 o 3, o una inasistencia (administrador)",
    responses=_respuestas(401, 403, 404, 409, 422),
)
async def aplicar_excepcion(
    request: Request, claims: Claims, id_reserva: UUID, cuerpo: NuevaExcepcion
) -> Reserva:
    async with transaccion_con_identidad(_pool(request), claims) as conexion:
        reserva = await AplicarExcepcion(RepositorioReservasPostgres(conexion)).ejecutar(
            id_reserva, cuerpo.motivo
        )
    return Reserva.desde_dominio(reserva)


@router.post(
    "/reservas/{id_reserva}/reprogramar/simular",
    response_model=VistaReprogramacion,
    summary="Vista previa de reprogramar: nivel, penalizacion, precio nuevo, saldo y credito; "
    "sin cambiar nada (dueno; administrador tras una cancelacion del estudio)",
    responses=_respuestas(401, 403, 404, 409, 422),
)
async def simular_reprogramacion(
    request: Request, claims: Claims, id_reserva: UUID, cuerpo: NuevoHorario
) -> VistaReprogramacion:
    ahora = datetime.now(UTC)
    async with transaccion_con_identidad(_pool(request), claims) as conexion:
        vista = await SimularReprogramacion(
            RepositorioReservasPostgres(conexion), CotizadorCatalogo(conexion)
        ).ejecutar(id_reserva, cuerpo.inicio, ahora)
    return VistaReprogramacion.desde_dominio(vista)


@router.post(
    "/reservas/{id_reserva}/reprogramar",
    response_model=Reserva,
    response_model_exclude_unset=True,
    summary="Reprograma a otro horario de la misma sala con la politica de niveles (RF-18); "
    "tras una cancelacion del estudio, sin costo (`nivel_esperado: null`)",
    responses=_respuestas(401, 403, 404, 409, 422),
)
async def reprogramar_reserva(
    request: Request, claims: Claims, id_reserva: UUID, cuerpo: Reprogramacion
) -> Reserva:
    ahora = datetime.now(UTC)
    async with transaccion_con_identidad(_pool(request), claims) as conexion:
        reserva = await ReprogramarReserva(
            RepositorioReservasPostgres(conexion), CotizadorCatalogo(conexion)
        ).ejecutar(id_reserva, cuerpo.inicio, cuerpo.nivel_esperado, cuerpo.total_esperado, ahora)
    return Reserva.desde_dominio(reserva)


@router.post(
    "/reservas/{id_reserva}/eleccion-estudio",
    response_model=Reserva,
    response_model_exclude_unset=True,
    summary="Tras una cancelacion del estudio, elige la devolucion integra de lo pagado "
    "(dueno o administrador)",
    responses=_respuestas(401, 403, 404, 409, 422),
)
async def elegir_devolucion_del_estudio(
    request: Request, claims: Claims, id_reserva: UUID, cuerpo: EleccionEstudio
) -> Reserva:
    async with transaccion_con_identidad(_pool(request), claims) as conexion:
        reserva = await ElegirDevolucionDelEstudio(RepositorioReservasPostgres(conexion)).ejecutar(
            id_reserva
        )
    return Reserva.desde_dominio(reserva)
