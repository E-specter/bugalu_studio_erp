from datetime import UTC, datetime
from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, File, Query, Request, Response, UploadFile

from bugalu.compartido.autenticacion import obtener_claims, obtener_claims_opcionales, obtener_token
from bugalu.compartido.base_datos import transaccion_con_identidad, transaccion_publica
from bugalu.compartido.configuracion import obtener_configuracion
from bugalu.compartido.errores import NoAutenticado
from bugalu.compartido.esquemas import RespuestaError
from bugalu.modulos.asesorias.aplicacion.disponibilidad.caso_de_uso import (
    ConsultarDisponibilidadProfesional,
)
from bugalu.modulos.asesorias.aplicacion.especialidades.caso_de_uso import (
    ActualizarEspecialidad,
    CrearEspecialidad,
    ListarEspecialidades,
)
from bugalu.modulos.asesorias.aplicacion.foto.caso_de_uso import (
    FotoReemplazada,
    QuitarFoto,
    ReemplazarFoto,
)
from bugalu.modulos.asesorias.aplicacion.horarios.caso_de_uso import (
    PublicarHorarios,
    RetirarHorario,
    SugerirHorarios,
)
from bugalu.modulos.asesorias.aplicacion.perfiles.caso_de_uso import (
    ActualizarProfesional,
    CrearPerfil,
    ListarProfesionales,
    ObtenerProfesional,
)
from bugalu.modulos.asesorias.dominio.foto import LIMITE_BYTES
from bugalu.modulos.asesorias.dominio.modelos import Profesional as ProfesionalDominio
from bugalu.modulos.asesorias.dominio.precios import duraciones
from bugalu.modulos.asesorias.infraestructura.entrada.http import esquemas as e
from bugalu.modulos.asesorias.infraestructura.salida.almacen_storage import AlmacenFotosStorage
from bugalu.modulos.asesorias.infraestructura.salida.repositorio_postgres import (
    RepositorioAsesoriasPostgres,
)
from bugalu.modulos.reservas.dominio.disponibilidad import Tramo as TramoDominio
from bugalu.modulos.reservas.infraestructura.entrada.http.esquemas import Instante

router = APIRouter(tags=["asesorias"])

Claims = Annotated[dict[str, Any], Depends(obtener_claims)]
ClaimsOpcionales = Annotated[dict[str, Any] | None, Depends(obtener_claims_opcionales)]
Token = Annotated[str, Depends(obtener_token)]

_DESCRIPCION = {
    401: "Token ausente, invalido o caducado",
    403: "Sin permiso para esta operacion",
    404: "No encontrado",
    409: "Conflicto con el estado actual",
    413: "La foto pesa mas de 2 MB",
    422: "Datos invalidos",
    428: "El cambio es sensible: requiere vista previa y confirmacion (RF-20)",
    503: "Autenticacion, base de datos o almacenamiento no disponible",
}


def _respuestas(*codigos: int) -> dict[int | str, dict[str, Any]]:
    return {c: {"model": RespuestaError, "description": _DESCRIPCION[c]} for c in (*codigos, 503)}


def _pool(request: Request) -> Any:
    return request.app.state.pool


def _contexto(request: Request, claims: dict[str, Any] | None) -> Any:
    if claims is None:
        return transaccion_publica(_pool(request))
    return transaccion_con_identidad(_pool(request), claims)


def _actor(claims: dict[str, Any] | None) -> UUID | None:
    return UUID(str(claims["sub"])) if claims else None


async def _perfil(conexion: Any, p: ProfesionalDominio, ve_estado: bool) -> e.Profesional:
    repo = RepositorioAsesoriasPostgres(conexion)
    return e.profesional_de(
        p,
        duraciones(p.precios, await repo.obtener_impuestos()),
        obtener_configuracion().url_supabase,
        ve_estado,
    )


# --- especialidades -----------------------------------------------------------------------------


@router.get(
    "/especialidades-asesoria",
    response_model=list[e.Especialidad],
    summary="Especialidades activas (publico); `todas=true`, administrador",
    responses=_respuestas(401, 403),
)
async def listar_especialidades(
    request: Request, claims: ClaimsOpcionales, todas: bool = False
) -> list[e.Especialidad]:
    if todas and claims is None:
        raise NoAutenticado("Falta el token de acceso.")
    async with _contexto(request, claims) as conexion:
        lista = await ListarEspecialidades(RepositorioAsesoriasPostgres(conexion)).ejecutar(todas)
    return [e.Especialidad.desde_dominio(x) for x in lista]


@router.post(
    "/especialidades-asesoria",
    response_model=e.Especialidad,
    status_code=201,
    summary="Crea una especialidad (administrador)",
    responses=_respuestas(401, 403, 409, 422),
)
async def crear_especialidad(
    request: Request, claims: Claims, cuerpo: e.NuevaEspecialidad
) -> e.Especialidad:
    async with transaccion_con_identidad(_pool(request), claims) as conexion:
        nueva = await CrearEspecialidad(RepositorioAsesoriasPostgres(conexion)).ejecutar(
            cuerpo.nombre
        )
    return e.Especialidad.desde_dominio(nueva)


@router.patch(
    "/especialidades-asesoria/{id_especialidad}",
    response_model=e.Especialidad,
    summary="Renombra o desactiva una especialidad (administrador)",
    responses=_respuestas(401, 403, 404, 409, 422),
)
async def actualizar_especialidad(
    request: Request, claims: Claims, id_especialidad: UUID, cuerpo: e.CambiosEspecialidad
) -> e.Especialidad:
    async with transaccion_con_identidad(_pool(request), claims) as conexion:
        actualizada = await ActualizarEspecialidad(RepositorioAsesoriasPostgres(conexion)).ejecutar(
            id_especialidad, cuerpo.model_dump(exclude_unset=True)
        )
    return e.Especialidad.desde_dominio(actualizada)


# --- perfiles -----------------------------------------------------------------------------------


@router.get(
    "/profesionales",
    response_model=list[e.ProfesionalResumen],
    response_model_exclude_none=True,
    summary="Profesionales publicados, por nombre (publico); el administrador ve tambien el resto",
    responses=_respuestas(422),
)
async def listar_profesionales(
    request: Request, claims: ClaimsOpcionales, especialidad: UUID | None = None
) -> list[e.ProfesionalResumen]:
    async with _contexto(request, claims) as conexion:
        repo = RepositorioAsesoriasPostgres(conexion)
        perfiles, ve_estado = await ListarProfesionales(repo).ejecutar(
            especialidad, claims is not None
        )
        impuestos = await repo.obtener_impuestos()
    url = obtener_configuracion().url_supabase
    return [e.resumen_de(p, duraciones(p.precios, impuestos), url, ve_estado) for p in perfiles]


@router.post(
    "/profesionales",
    response_model=e.Profesional,
    response_model_exclude_none=True,
    status_code=201,
    summary="Crea el perfil, inactivo, de un usuario administrador o profesional (administrador)",
    responses=_respuestas(401, 403, 404, 409, 422),
)
async def crear_perfil(request: Request, claims: Claims, cuerpo: e.NuevoPerfil) -> e.Profesional:
    async with transaccion_con_identidad(_pool(request), claims) as conexion:
        perfil = await CrearPerfil(RepositorioAsesoriasPostgres(conexion)).ejecutar(
            cuerpo.id_usuario
        )
        return await _perfil(conexion, perfil, True)


@router.get(
    "/profesionales/{id_profesional}",
    response_model=e.Profesional,
    response_model_exclude_none=True,
    summary="Perfil publico; el propio y el administrador ven tambien el no publicado",
    responses=_respuestas(404),
)
async def obtener_profesional(
    request: Request, claims: ClaimsOpcionales, id_profesional: UUID
) -> e.Profesional:
    async with _contexto(request, claims) as conexion:
        perfil, ve_estado = await ObtenerProfesional(
            RepositorioAsesoriasPostgres(conexion)
        ).ejecutar(id_profesional, _actor(claims))
        return await _perfil(conexion, perfil, ve_estado)


@router.patch(
    "/profesionales/{id_profesional}",
    response_model=e.Profesional,
    response_model_exclude_none=True,
    summary="Edita el perfil (el propio); estado y precios, solo el administrador",
    responses=_respuestas(401, 403, 404, 422, 428),
)
async def actualizar_profesional(
    request: Request, claims: Claims, id_profesional: UUID, cuerpo: e.CambiosProfesional
) -> e.Profesional:
    cambios = cuerpo.model_dump(exclude_unset=True, exclude={"precios", "redes"})
    if cuerpo.precios is not None:
        cambios["precios"] = {
            int(k): v
            for k, v in cuerpo.precios.model_dump(by_alias=True, exclude_unset=True).items()
        }
    if cuerpo.redes is not None:
        cambios["redes"] = [r.model_dump() for r in cuerpo.redes]
    async with transaccion_con_identidad(_pool(request), claims) as conexion:
        perfil = await ActualizarProfesional(RepositorioAsesoriasPostgres(conexion)).ejecutar(
            UUID(str(claims["sub"])), id_profesional, cambios
        )
        return await _perfil(conexion, perfil, True)


# --- foto ---------------------------------------------------------------------------------------


def _almacen(token: str) -> AlmacenFotosStorage:
    configuracion = obtener_configuracion()
    return AlmacenFotosStorage(
        configuracion.url_supabase, configuracion.clave_publicable_supabase, token
    )


@router.put(
    "/profesionales/{id_profesional}/foto",
    response_model=e.Profesional,
    response_model_exclude_none=True,
    summary="Reemplaza la foto: JPG, PNG o WebP de hasta 2 MB, validada por su contenido",
    responses=_respuestas(401, 403, 404, 413, 422),
)
async def reemplazar_foto(
    request: Request,
    claims: Claims,
    token: Token,
    id_profesional: UUID,
    archivo: Annotated[UploadFile, File()],
) -> e.Profesional:
    # shortcut: el multipart se vuelca a disco antes del 413 si no trae Content-Length; el
    # servidor o proxy debe limitar el cuerpo en produccion (como POST /pagos).
    contenido = await archivo.read(LIMITE_BYTES + 1)  # nunca el archivo entero
    caso: ReemplazarFoto | None = None
    reemplazo: FotoReemplazada | None = None
    try:
        async with transaccion_con_identidad(_pool(request), claims) as conexion:
            repo = RepositorioAsesoriasPostgres(conexion)
            caso = ReemplazarFoto(repo, _almacen(token))
            reemplazo = await caso.ejecutar(UUID(str(claims["sub"])), id_profesional, contenido)
            perfil = await repo.obtener_profesional(id_profesional)
            assert perfil is not None  # la acaba de actualizar
            respuesta = await _perfil(conexion, perfil, True)
    except Exception:
        if caso is not None and reemplazo is not None:  # sin commit: la anterior sigue
            await caso.descartar(reemplazo)
        raise
    assert caso is not None and reemplazo is not None
    await caso.confirmar(reemplazo)  # ya confirmada: recien ahora se borra la anterior
    return respuesta


@router.delete(
    "/profesionales/{id_profesional}/foto",
    status_code=204,
    summary="Quita la foto (se muestra el marcador con iniciales)",
    responses=_respuestas(401, 403, 404),
)
async def quitar_foto(
    request: Request, claims: Claims, token: Token, id_profesional: UUID
) -> Response:
    async with transaccion_con_identidad(_pool(request), claims) as conexion:
        await QuitarFoto(RepositorioAsesoriasPostgres(conexion), _almacen(token)).ejecutar(
            UUID(str(claims["sub"])), id_profesional
        )
    return Response(status_code=204)


# --- horarios y disponibilidad ------------------------------------------------------------------


@router.get(
    "/profesionales/{id_profesional}/horarios/sugerencia",
    response_model=list[e.Tramo],
    summary="Plantilla: la ultima semana publicada desplazada a la semana pedida",
    responses=_respuestas(401, 403, 404, 422),
)
async def sugerir_horarios(
    request: Request,
    claims: Claims,
    id_profesional: UUID,
    semana: Annotated[str, Query(pattern=r"^\d{4}-W\d{2}$")],
) -> list[e.Tramo]:
    async with transaccion_con_identidad(_pool(request), claims) as conexion:
        tramos = await SugerirHorarios(RepositorioAsesoriasPostgres(conexion)).ejecutar(
            UUID(str(claims["sub"])), id_profesional, semana
        )
    return [e.Tramo(inicio=t.inicio, fin=t.fin) for t in tramos]


@router.post(
    "/profesionales/{id_profesional}/horarios",
    response_model=list[e.Horario],
    status_code=201,
    summary="Publica un lote de bloques futuros (1 a 200), todo o nada",
    responses=_respuestas(401, 403, 404, 409, 422),
)
async def publicar_horarios(
    request: Request, claims: Claims, id_profesional: UUID, cuerpo: e.NuevosHorarios
) -> list[e.Horario]:
    async with transaccion_con_identidad(_pool(request), claims) as conexion:
        horarios = await PublicarHorarios(RepositorioAsesoriasPostgres(conexion)).ejecutar(
            UUID(str(claims["sub"])),
            id_profesional,
            [TramoDominio(h.inicio, h.fin) for h in cuerpo.horarios],
            datetime.now(UTC),
        )
    return [e.Horario.desde_dominio(h) for h in horarios]


@router.delete(
    "/profesionales/{id_profesional}/horarios/{id_horario}",
    status_code=204,
    summary="Retira un bloque (sin asesorias vivas dentro)",
    responses=_respuestas(401, 403, 404, 409),
)
async def retirar_horario(
    request: Request, claims: Claims, id_profesional: UUID, id_horario: UUID
) -> Response:
    async with transaccion_con_identidad(_pool(request), claims) as conexion:
        await RetirarHorario(RepositorioAsesoriasPostgres(conexion)).ejecutar(
            UUID(str(claims["sub"])), id_profesional, id_horario
        )
    return Response(status_code=204)


@router.get(
    "/profesionales/{id_profesional}/disponibilidad",
    response_model=e.DisponibilidadProfesional,
    summary="Bloques, ocupados, minutos libres por dia y duraciones de un rango de hasta 42 dias",
    responses=_respuestas(404, 422),
)
async def consultar_disponibilidad(
    request: Request,
    claims: ClaimsOpcionales,
    id_profesional: UUID,
    desde: Annotated[Instante, Query()],
    hasta: Annotated[Instante, Query()],
    excluir_asesoria: Annotated[UUID | None, Query()] = None,
) -> e.DisponibilidadProfesional:
    async with _contexto(request, claims) as conexion:
        resultado = await ConsultarDisponibilidadProfesional(
            RepositorioAsesoriasPostgres(conexion)
        ).ejecutar(id_profesional, desde, hasta, datetime.now(UTC), excluir_asesoria)
    return e.DisponibilidadProfesional.desde_dominio(resultado)
