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
from bugalu.modulos.pagos.aplicacion.obtener_captura.caso_de_uso import ObtenerCaptura
from bugalu.modulos.pagos.aplicacion.obtener_pago.caso_de_uso import ObtenerPago
from bugalu.modulos.pagos.aplicacion.registrar_pago.caso_de_uso import RegistrarPago
from bugalu.modulos.pagos.dominio.captura import LIMITE_BYTES
from bugalu.modulos.pagos.infraestructura.entrada.http.esquemas import Captura, Pago
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
    "/pagos/{id_pago}",
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
