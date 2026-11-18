from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import UTC, date, datetime
from functools import partial
from typing import Annotated, Any, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, Path, Request, Response, UploadFile
from pydantic import BaseModel, ValidationError

from bugalu.compartido.autenticacion import (
    obtener_claims,
    obtener_claims_o_visitante,
    obtener_token,
)
from bugalu.compartido.base_datos import transaccion_con_identidad, transaccion_publica
from bugalu.compartido.configuracion import obtener_configuracion
from bugalu.compartido.errores import DatosInvalidos, DemasiadosAdjuntos
from bugalu.compartido.esquemas import RespuestaError
from bugalu.modulos.reclamaciones.aplicacion.consultar.caso_de_uso import (
    ExportarHojas,
    ListarHojas,
    ListarMisHojas,
    ObtenerHoja,
    UrlAdjunto,
)
from bugalu.modulos.reclamaciones.aplicacion.registrar.caso_de_uso import (
    RegistrarHoja,
    TranscribirHoja,
)
from bugalu.modulos.reclamaciones.aplicacion.responder.caso_de_uso import ResponderHoja
from bugalu.modulos.reclamaciones.dominio.adjuntos import LIMITE_BYTES, MAXIMO
from bugalu.modulos.reclamaciones.infraestructura.entrada.http.esquemas import (
    AdjuntoFirmado,
    HojaResumenSalida,
    HojaSalida,
    NuevaHojaEntrada,
    NuevaTranscripcionEntrada,
    RespuestaEntrada,
)
from bugalu.modulos.reclamaciones.infraestructura.salida.almacen_storage import AlmacenStorage
from bugalu.modulos.reclamaciones.infraestructura.salida.repositorio_postgres import (
    RepositorioHojasPostgres,
)

router = APIRouter(tags=["reclamaciones"])

Claims = Annotated[dict[str, Any], Depends(obtener_claims)]
ClaimsOVisitante = Annotated[dict[str, Any] | None, Depends(obtener_claims_o_visitante)]
Token = Annotated[str, Depends(obtener_token)]
IdHoja = Annotated[UUID, Path()]

_DESCRIPCION = {
    401: "Token ausente, invalido o caducado",
    403: "Sin permiso para esta operacion",
    404: "No encontrado",
    409: "Conflicto con el estado actual",
    413: "Un adjunto pesa mas de 5 MB",
    422: "Datos invalidos",
    429: "Demasiadas hojas desde esta IP en la ultima hora",
    503: "Autenticacion, base de datos o almacenamiento no disponible",
}


def _respuestas(*codigos: int) -> dict[int | str, dict[str, Any]]:
    return {c: {"model": RespuestaError, "description": _DESCRIPCION[c]} for c in (*codigos, 503)}


def _solicitante(claims: dict[str, Any] | None) -> UUID | None:
    return UUID(str(claims["sub"])) if claims else None


def _pool(request: Request) -> Any:
    return request.app.state.pool


@asynccontextmanager
async def _repositorio(
    pool: Any, claims: dict[str, Any] | None
) -> AsyncIterator[RepositorioHojasPostgres]:
    """Una transaccion (con la identidad de los claims, o `anon`) que cierra con commit al salir."""
    contexto = transaccion_con_identidad(pool, claims) if claims else transaccion_publica(pool)
    async with contexto as conexion:
        yield RepositorioHojasPostgres(conexion)


@asynccontextmanager
async def _repositorio_api(pool: Any) -> AsyncIterator[RepositorioHojasPostgres]:
    """Rol `bugalu_api` directo, sin `set local role`: el unico que ejecuta `avisar_hoja`."""
    async with pool.connection() as conexion, conexion.transaction():
        yield RepositorioHojasPostgres(conexion)


def _almacen(token_administrador: str | None = None) -> AlmacenStorage:
    c = obtener_configuracion()
    return AlmacenStorage(c.url_supabase, c.clave_publicable_supabase, token_administrador)


def _entrada[T: BaseModel](modelo: type[T], datos: str) -> T:
    try:
        return modelo.model_validate_json(datos)
    except ValidationError as error:
        campos = list(
            dict.fromkeys(".".join(str(p) for p in e["loc"]) or "datos" for e in error.errors())
        )
        raise DatosInvalidos(
            f"Datos invalidos: {', '.join(campos)}.", {"campo": campos[0]}
        ) from None


async def _leer(adjuntos: list[UploadFile]) -> list[tuple[str, bytes]]:
    if len(adjuntos) > MAXIMO:  # antes de leer ningun archivo
        raise DemasiadosAdjuntos("Se admiten hasta 3 adjuntos.")
    return [(a.filename or "", await a.read(LIMITE_BYTES + 1)) for a in adjuntos]


@router.post(
    "/reclamaciones",
    response_model=HojaSalida,
    status_code=201,
    summary="Registra una hoja de reclamacion (publico; con sesion la vincula a la cuenta)",
    responses=_respuestas(409, 413, 422, 429),
)
async def registrar_hoja(
    request: Request,
    response: Response,
    claims: ClaimsOVisitante,
    datos: Annotated[str, Form()],
    adjuntos: Annotated[list[UploadFile], File()] = [],  # noqa: B006
) -> HojaSalida:
    entrada = _entrada(NuevaHojaEntrada, datos)
    archivos = await _leer(adjuntos)
    ip = request.client.host if request.client else None
    solicitante = _solicitante(claims)
    pool = _pool(request)
    registro = await RegistrarHoja(
        partial(_repositorio, pool, claims),
        partial(_repositorio, pool, None),
        partial(_repositorio_api, pool),
        _almacen(),
    ).ejecutar(
        entrada.a_dominio(entrada.tipo),
        entrada.confirmado,
        entrada.campo_trampa,
        archivos,
        ip,
        entrada.clave_envio,
        solicitante,
    )
    if not registro.creada:
        response.status_code = 200  # reintento con la misma clave: la hoja ya registrada
    return HojaSalida.desde_dominio(registro.hoja, solicitante, registro.no_guardados)


@router.post(
    "/reclamaciones/transcripcion",
    response_model=HojaSalida,
    status_code=201,
    summary="Transcribe una hoja del libro fisico de respaldo (administrador)",
    responses=_respuestas(401, 403, 409, 413, 422),
)
async def transcribir_hoja(
    request: Request,
    claims: Claims,
    datos: Annotated[str, Form()],
    adjuntos: Annotated[list[UploadFile], File()] = [],  # noqa: B006
) -> HojaSalida:
    entrada = _entrada(NuevaTranscripcionEntrada, datos)
    archivos = await _leer(adjuntos)
    pool = _pool(request)
    registro = await TranscribirHoja(
        partial(_repositorio, pool, claims),
        partial(_repositorio, pool, None),
        partial(_repositorio_api, pool),
        _almacen(),
    ).ejecutar(
        entrada.a_dominio(entrada.tipo),
        entrada.confirmado,
        archivos,
        entrada.fecha_original,
        entrada.numero_hoja_fisica,
    )
    return HojaSalida.desde_dominio(registro.hoja, _solicitante(claims), registro.no_guardados)


@router.get(
    "/reclamaciones/mias",
    response_model=list[HojaResumenSalida],
    summary="Mis hojas de reclamacion",
    responses=_respuestas(401),
)
async def mis_hojas(request: Request, claims: Claims) -> list[HojaResumenSalida]:
    async with transaccion_con_identidad(_pool(request), claims) as conexion:
        hojas = await ListarMisHojas(RepositorioHojasPostgres(conexion)).ejecutar()
    return [HojaResumenSalida.desde_dominio(h) for h in hojas]


@router.get(
    "/reclamaciones/exportar",
    response_class=Response,
    responses={
        200: {"content": {"text/csv": {}}, "description": "CSV con todas las columnas"},
        **_respuestas(401, 403, 422),
    },
    summary="Exporta las hojas de un rango de fechas en CSV (administrador)",
)
async def exportar(request: Request, claims: Claims, desde: date, hasta: date) -> Response:
    async with transaccion_con_identidad(_pool(request), claims) as conexion:
        texto = await ExportarHojas(RepositorioHojasPostgres(conexion)).ejecutar(desde, hasta)
    return Response(
        texto,
        media_type="text/csv; charset=utf-8",
        headers={
            "Content-Disposition": f'attachment; filename="reclamaciones-{desde}-{hasta}.csv"'
        },
    )


@router.get(
    "/reclamaciones",
    response_model=list[HojaResumenSalida],
    summary="Bandeja del Administrador: pendientes primero por plazo (administrador)",
    responses=_respuestas(401, 403, 422),
)
async def bandeja(
    request: Request,
    claims: Claims,
    estado: Literal["pendiente", "respondida"] | None = None,
    desde: date | None = None,
    hasta: date | None = None,
) -> list[HojaResumenSalida]:
    async with transaccion_con_identidad(_pool(request), claims) as conexion:
        hojas = await ListarHojas(RepositorioHojasPostgres(conexion)).ejecutar(estado, desde, hasta)
    return [HojaResumenSalida.desde_dominio(h) for h in hojas]


@router.get(
    "/reclamaciones/{id_hoja}",
    response_model=HojaSalida,
    summary="Una hoja (dueno o administrador; la ajena es 404)",
    responses=_respuestas(401, 404, 422),
)
async def obtener_hoja(request: Request, claims: Claims, id_hoja: IdHoja) -> HojaSalida:
    async with transaccion_con_identidad(_pool(request), claims) as conexion:
        hoja = await ObtenerHoja(RepositorioHojasPostgres(conexion)).ejecutar(id_hoja)
    return HojaSalida.desde_dominio(hoja, _solicitante(claims))


@router.post(
    "/reclamaciones/{id_hoja}/respuesta",
    response_model=HojaSalida,
    summary="Responde la hoja, una sola vez (administrador)",
    responses=_respuestas(401, 403, 404, 409, 422),
)
async def responder_hoja(
    request: Request, claims: Claims, id_hoja: IdHoja, cuerpo: RespuestaEntrada
) -> HojaSalida:
    async with transaccion_con_identidad(_pool(request), claims) as conexion:
        hoja = await ResponderHoja(RepositorioHojasPostgres(conexion)).ejecutar(
            id_hoja, cuerpo.texto, cuerpo.referencia_carta, cuerpo.enviada_en
        )
    return HojaSalida.desde_dominio(hoja, _solicitante(claims))


@router.get(
    "/reclamaciones/{id_hoja}/adjuntos/{n}",
    response_model=AdjuntoFirmado,
    summary="URL firmada de pocos minutos de un adjunto (administrador)",
    responses=_respuestas(401, 403, 404, 422),
)
async def url_adjunto(
    request: Request,
    claims: Claims,
    token: Token,
    id_hoja: IdHoja,
    n: Annotated[int, Path(ge=1, le=MAXIMO)],
) -> AdjuntoFirmado:
    async with transaccion_con_identidad(_pool(request), claims) as conexion:
        url, expira = await UrlAdjunto(
            RepositorioHojasPostgres(conexion), _almacen(token)
        ).ejecutar(id_hoja, n, datetime.now(UTC))
    return AdjuntoFirmado(url=url, expira_en=expira)
