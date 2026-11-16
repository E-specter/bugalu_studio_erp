from datetime import date
from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request, Response

from bugalu.compartido.autenticacion import obtener_claims
from bugalu.compartido.base_datos import transaccion_con_identidad, transaccion_publica
from bugalu.compartido.esquemas import RespuestaError
from bugalu.modulos.catalogo.aplicacion.actualizar_especialista.caso_de_uso import (
    ActualizarEspecialista,
)
from bugalu.modulos.catalogo.aplicacion.actualizar_servicio.caso_de_uso import ActualizarServicio
from bugalu.modulos.catalogo.aplicacion.agregar_feriado.caso_de_uso import AgregarFeriado
from bugalu.modulos.catalogo.aplicacion.eliminar_feriado.caso_de_uso import EliminarFeriado
from bugalu.modulos.catalogo.aplicacion.listar_especialistas.caso_de_uso import (
    ListarEspecialistas,
)
from bugalu.modulos.catalogo.aplicacion.listar_feriados.caso_de_uso import ListarFeriados
from bugalu.modulos.catalogo.aplicacion.listar_servicios.caso_de_uso import ListarServicios
from bugalu.modulos.catalogo.aplicacion.obtener_recargos.caso_de_uso import ObtenerRecargos
from bugalu.modulos.catalogo.aplicacion.reemplazar_recargos.caso_de_uso import ReemplazarRecargos
from bugalu.modulos.catalogo.aplicacion.simular_precio.caso_de_uso import SimularPrecio
from bugalu.modulos.catalogo.dominio import precio
from bugalu.modulos.catalogo.infraestructura.entrada.http.esquemas import (
    CambiosEspecialista,
    CambiosServicio,
    Especialista,
    Feriado,
    NuevaSimulacion,
    NuevoFeriado,
    Recargos,
    Servicio,
    Simulacion,
)
from bugalu.modulos.catalogo.infraestructura.salida.repositorio_postgres import (
    RepositorioCatalogoPostgres,
)

router = APIRouter(tags=["catalogo"])

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


def _respuestas_admin(*codigos: int) -> dict[int | str, dict[str, Any]]:
    return _respuestas(401, 403, *codigos)


def _pool(request: Request) -> Any:
    return request.app.state.pool


@router.get(
    "/servicios",
    response_model=list[Servicio],
    summary="Catalogo de servicios con su tarifa (publico)",
    responses=_respuestas(),
)
async def listar_servicios(request: Request) -> list[Servicio]:
    async with transaccion_publica(_pool(request)) as conexion:
        servicios = await ListarServicios(RepositorioCatalogoPostgres(conexion)).ejecutar()
    return [Servicio.desde_dominio(s) for s in servicios]


@router.patch(
    "/servicios/{id_servicio}",
    response_model=Servicio,
    summary="Edita tarifa, monto fijo, estado y especialistas por defecto (administrador)",
    responses=_respuestas_admin(404, 422),
)
async def actualizar_servicio(
    request: Request, claims: Claims, id_servicio: UUID, cuerpo: CambiosServicio
) -> Servicio:
    async with transaccion_con_identidad(_pool(request), claims) as conexion:
        servicio = await ActualizarServicio(RepositorioCatalogoPostgres(conexion)).ejecutar(
            id_servicio, cuerpo.model_dump(exclude_unset=True)
        )
    return Servicio.desde_dominio(servicio)


@router.get(
    "/especialistas",
    response_model=list[Especialista],
    summary="Especialistas con su tarifa (publico)",
    responses=_respuestas(),
)
async def listar_especialistas(request: Request) -> list[Especialista]:
    async with transaccion_publica(_pool(request)) as conexion:
        especialistas = await ListarEspecialistas(RepositorioCatalogoPostgres(conexion)).ejecutar()
    return [Especialista.desde_dominio(e) for e in especialistas]


@router.patch(
    "/especialistas/{id_especialista}",
    response_model=Especialista,
    summary="Edita montos, unidad y estado de un especialista (administrador)",
    responses=_respuestas_admin(404, 422),
)
async def actualizar_especialista(
    request: Request, claims: Claims, id_especialista: UUID, cuerpo: CambiosEspecialista
) -> Especialista:
    async with transaccion_con_identidad(_pool(request), claims) as conexion:
        especialista = await ActualizarEspecialista(RepositorioCatalogoPostgres(conexion)).ejecutar(
            id_especialista, cuerpo.model_dump(exclude_unset=True)
        )
    return Especialista.desde_dominio(especialista)


@router.get(
    "/recargos",
    response_model=Recargos,
    summary="Recargos por horario (publico)",
    responses=_respuestas(),
)
async def obtener_recargos(request: Request) -> Recargos:
    async with transaccion_publica(_pool(request)) as conexion:
        recargos = await ObtenerRecargos(RepositorioCatalogoPostgres(conexion)).ejecutar()
    return Recargos.desde_dominio(recargos)


@router.put(
    "/recargos",
    response_model=Recargos,
    summary="Reemplaza los recargos por horario (administrador)",
    responses=_respuestas_admin(422),
)
async def reemplazar_recargos(request: Request, claims: Claims, cuerpo: Recargos) -> Recargos:
    async with transaccion_con_identidad(_pool(request), claims) as conexion:
        recargos = await ReemplazarRecargos(RepositorioCatalogoPostgres(conexion)).ejecutar(
            cuerpo.a_dominio()
        )
    return Recargos.desde_dominio(recargos)


@router.get(
    "/feriados",
    response_model=list[Feriado],
    summary="Feriados, opcionalmente de un anio (publico)",
    responses=_respuestas(422),
)
async def listar_feriados(
    request: Request, anio: Annotated[int | None, Query(ge=2000, le=2100)] = None
) -> list[Feriado]:
    async with transaccion_publica(_pool(request)) as conexion:
        feriados = await ListarFeriados(RepositorioCatalogoPostgres(conexion)).ejecutar(anio)
    return [Feriado(fecha=f.fecha, nombre=f.nombre) for f in feriados]


@router.post(
    "/feriados",
    response_model=Feriado,
    status_code=201,
    summary="Agrega un feriado (administrador)",
    responses=_respuestas_admin(409, 422),
)
async def agregar_feriado(request: Request, claims: Claims, cuerpo: NuevoFeriado) -> Feriado:
    async with transaccion_con_identidad(_pool(request), claims) as conexion:
        feriado = await AgregarFeriado(RepositorioCatalogoPostgres(conexion)).ejecutar(
            precio.Feriado(cuerpo.fecha, cuerpo.nombre)
        )
    return Feriado(fecha=feriado.fecha, nombre=feriado.nombre)


@router.delete(
    "/feriados/{fecha}",
    status_code=204,
    summary="Quita un feriado (administrador)",
    responses=_respuestas_admin(404, 422),
)
async def eliminar_feriado(request: Request, claims: Claims, fecha: date) -> Response:
    async with transaccion_con_identidad(_pool(request), claims) as conexion:
        await EliminarFeriado(RepositorioCatalogoPostgres(conexion)).ejecutar(fecha)
    return Response(status_code=204)


@router.post(
    "/simulaciones",
    response_model=Simulacion,
    summary="Simula el precio de un tramo (publico, no vinculante)",
    responses=_respuestas(422),
)
async def simular_precio(request: Request, cuerpo: NuevaSimulacion) -> Simulacion:
    async with transaccion_publica(_pool(request)) as conexion:
        simulacion = await SimularPrecio(RepositorioCatalogoPostgres(conexion)).ejecutar(
            cuerpo.id_sala, cuerpo.id_servicio, cuerpo.inicio, cuerpo.fin, cuerpo.especialistas
        )
    return Simulacion.desde_dominio(simulacion)
