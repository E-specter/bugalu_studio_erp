import logging
from datetime import UTC, datetime
from decimal import Decimal
from typing import Annotated, Any, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, Request, UploadFile

from bugalu.compartido.autenticacion import obtener_claims, obtener_token
from bugalu.compartido.base_datos import transaccion_con_identidad
from bugalu.compartido.configuracion import obtener_configuracion
from bugalu.compartido.errores import DatosInvalidos
from bugalu.compartido.esquemas import RespuestaError
from bugalu.compartido.roles import SOLO_CLIENTES
from bugalu.modulos.pagos.aplicacion.datos_para_pagar.caso_de_uso import (
    ActualizarContacto,
    ObtenerContacto,
    ObtenerInstrucciones,
    ReemplazarInstrucciones,
)
from bugalu.modulos.pagos.aplicacion.obtener_captura.caso_de_uso import ObtenerCaptura
from bugalu.modulos.pagos.aplicacion.obtener_pago.caso_de_uso import ObtenerPago
from bugalu.modulos.pagos.aplicacion.registrar_pago.caso_de_uso import RegistrarPago
from bugalu.modulos.pagos.aplicacion.validar_pago.caso_de_uso import (
    AprobarPago,
    ListarPagos,
    RechazarPago,
)
from bugalu.modulos.pagos.dominio.captura import LIMITE_BYTES
from bugalu.modulos.pagos.dominio.instrucciones import Instruccion
from bugalu.modulos.pagos.infraestructura.entrada.http.esquemas import (
    Captura,
    Contacto,
    InstruccionEntrada,
    InstruccionPago,
    Pago,
    Rechazo,
)
from bugalu.modulos.pagos.infraestructura.salida.almacen_storage import AlmacenStorage
from bugalu.modulos.pagos.infraestructura.salida.repositorio_postgres import (
    RepositorioPagosPostgres,
)

router = APIRouter(tags=["pagos"])
_registro = logging.getLogger(__name__)

Claims = Annotated[dict[str, Any], Depends(obtener_claims)]
Token = Annotated[str, Depends(obtener_token)]

_DESCRIPCION = {
    401: "Token ausente, invalido o caducado",
    403: "Sin permiso para esta operacion o recurso",
    404: "No encontrado",
    409: "Conflicto con el estado actual",
    413: "La captura pesa mas de 5 MB",
    422: "Datos invalidos",
    503: "Autenticacion, base de datos o almacenamiento no disponible",
}


def _respuestas(*codigos: int) -> dict[int | str, dict[str, Any]]:
    return {c: {"model": RespuestaError, "description": _DESCRIPCION[c]} for c in (*codigos, 503)}


def _pool(request: Request) -> Any:
    return request.app.state.pool


def _almacen(token: str) -> AlmacenStorage:
    configuracion = obtener_configuracion()
    return AlmacenStorage(
        configuracion.url_supabase, configuracion.clave_publicable_supabase, token
    )


@router.post(
    "/pagos",
    dependencies=SOLO_CLIENTES,
    response_model=Pago,
    status_code=201,
    summary="Registra el pago de una cuota propia con su captura (cliente)",
    responses=_respuestas(401, 403, 404, 409, 413, 422),
)
async def registrar_pago(
    request: Request,
    claims: Claims,
    token: Token,
    id_cuota: Annotated[UUID, Form()],
    metodo: Annotated[Literal["transferencia", "yape", "plin", "tarjeta"], Form()],
    monto: Annotated[str, Form(pattern=r"^\d{1,8}(\.\d{1,2})?$")],
    numero_operacion: Annotated[str, Form(pattern=r"^[A-Za-z0-9-]{4,40}$")],
    captura: Annotated[UploadFile, File()],
) -> Pago:
    importe = Decimal(monto)
    if importe <= 0:
        raise DatosInvalidos("El monto debe ser mayor que cero.", {"campo": "monto"})
    contenido = await captura.read(LIMITE_BYTES + 1)  # nunca el archivo entero
    pago = None
    try:
        async with transaccion_con_identidad(_pool(request), claims) as conexion:
            pago = await RegistrarPago(
                RepositorioPagosPostgres(conexion), _almacen(token)
            ).ejecutar(
                UUID(str(claims["sub"])), id_cuota, metodo, importe, numero_operacion, contenido
            )
    except Exception:
        if pago is not None:  # la captura ya esta subida y la confirmacion fallo
            _registro.error("Captura huerfana del pago %s: no se confirmo.", pago.id)
        raise
    return Pago.desde_dominio(pago)


@router.get(
    "/pagos",
    response_model=list[Pago],
    summary="Pagos por estado, por defecto los que esperan validacion (administrador)",
    responses=_respuestas(401, 403, 422),
)
async def listar_pagos(
    request: Request,
    claims: Claims,
    estado: Literal["pendiente_validacion", "aprobado", "rechazado"] = "pendiente_validacion",
) -> list[Pago]:
    async with transaccion_con_identidad(_pool(request), claims) as conexion:
        pagos = await ListarPagos(RepositorioPagosPostgres(conexion)).ejecutar(estado)
    return [Pago.desde_dominio(p) for p in pagos]


@router.get(
    "/pagos/{id_pago}",
    dependencies=SOLO_CLIENTES,
    response_model=Pago,
    summary="Un pago (dueno o administrador)",
    responses=_respuestas(401, 403, 404, 422),
)
async def obtener_pago(request: Request, claims: Claims, id_pago: UUID) -> Pago:
    async with transaccion_con_identidad(_pool(request), claims) as conexion:
        pago = await ObtenerPago(RepositorioPagosPostgres(conexion)).ejecutar(id_pago)
    return Pago.desde_dominio(pago)


@router.get(
    "/pagos/{id_pago}/captura",
    dependencies=SOLO_CLIENTES,
    response_model=Captura,
    summary="URL firmada de pocos minutos de la captura (dueno o administrador)",
    responses=_respuestas(401, 403, 404, 422),
)
async def obtener_captura(request: Request, claims: Claims, token: Token, id_pago: UUID) -> Captura:
    async with transaccion_con_identidad(_pool(request), claims) as conexion:
        captura = await ObtenerCaptura(
            RepositorioPagosPostgres(conexion), _almacen(token)
        ).ejecutar(id_pago, datetime.now(UTC))
    return Captura(url=captura.url, expira_en=captura.expira_en, tipo=captura.tipo)


@router.post(
    "/pagos/{id_pago}/aprobar",
    response_model=Pago,
    summary="Aprueba un pago en validacion (administrador)",
    responses=_respuestas(401, 403, 404, 409, 422),
)
async def aprobar_pago(request: Request, claims: Claims, id_pago: UUID) -> Pago:
    async with transaccion_con_identidad(_pool(request), claims) as conexion:
        pago = await AprobarPago(RepositorioPagosPostgres(conexion)).ejecutar(id_pago)
    return Pago.desde_dominio(pago)


@router.post(
    "/pagos/{id_pago}/rechazar",
    response_model=Pago,
    summary="Rechaza un pago en validacion con su motivo (administrador)",
    responses=_respuestas(401, 403, 404, 409, 422),
)
async def rechazar_pago(request: Request, claims: Claims, id_pago: UUID, cuerpo: Rechazo) -> Pago:
    async with transaccion_con_identidad(_pool(request), claims) as conexion:
        pago = await RechazarPago(RepositorioPagosPostgres(conexion)).ejecutar(
            id_pago, cuerpo.motivo
        )
    return Pago.desde_dominio(pago)


@router.get(
    "/instrucciones-pago",
    response_model=list[InstruccionPago],
    summary="Datos para pagar por metodo (al cliente, solo los activos)",
    responses=_respuestas(401),
)
async def obtener_instrucciones(request: Request, claims: Claims) -> list[InstruccionPago]:
    async with transaccion_con_identidad(_pool(request), claims) as conexion:
        lista = await ObtenerInstrucciones(RepositorioPagosPostgres(conexion)).ejecutar()
    return [InstruccionPago.desde_dominio(i) for i in lista]


@router.put(
    "/instrucciones-pago",
    response_model=list[InstruccionPago],
    summary="Reemplaza los datos para pagar de los cuatro metodos (administrador)",
    responses=_respuestas(401, 403, 422),
)
async def reemplazar_instrucciones(
    request: Request, claims: Claims, cuerpo: list[InstruccionEntrada]
) -> list[InstruccionPago]:
    entradas = [Instruccion(i.metodo, i.texto, i.activo) for i in cuerpo]
    async with transaccion_con_identidad(_pool(request), claims) as conexion:
        lista = await ReemplazarInstrucciones(RepositorioPagosPostgres(conexion)).ejecutar(entradas)
    return [InstruccionPago.desde_dominio(i) for i in lista]


@router.get(
    "/contacto-estudio",
    response_model=Contacto,
    summary="Texto de contacto del estudio",
    responses=_respuestas(401),
)
async def obtener_contacto(request: Request, claims: Claims) -> Contacto:
    async with transaccion_con_identidad(_pool(request), claims) as conexion:
        texto = await ObtenerContacto(RepositorioPagosPostgres(conexion)).ejecutar()
    return Contacto(texto=texto)


@router.put(
    "/contacto-estudio",
    response_model=Contacto,
    summary="Edita el contacto del estudio (administrador)",
    responses=_respuestas(401, 403, 422),
)
async def actualizar_contacto(request: Request, claims: Claims, cuerpo: Contacto) -> Contacto:
    async with transaccion_con_identidad(_pool(request), claims) as conexion:
        texto = await ActualizarContacto(RepositorioPagosPostgres(conexion)).ejecutar(cuerpo.texto)
    return Contacto(texto=texto)
