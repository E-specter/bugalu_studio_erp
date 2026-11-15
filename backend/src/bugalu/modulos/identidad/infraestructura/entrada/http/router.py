from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, Request

from bugalu.compartido.autenticacion import obtener_claims
from bugalu.compartido.base_datos import transaccion_con_identidad
from bugalu.compartido.esquemas import RespuestaError
from bugalu.modulos.identidad.aplicacion.actualizar_perfil.caso_de_uso import ActualizarPerfil
from bugalu.modulos.identidad.aplicacion.actualizar_usuario.caso_de_uso import ActualizarUsuario
from bugalu.modulos.identidad.aplicacion.aprobar_solicitud.caso_de_uso import AprobarSolicitud
from bugalu.modulos.identidad.aplicacion.crear_solicitud.caso_de_uso import CrearSolicitud
from bugalu.modulos.identidad.aplicacion.listar_solicitudes.caso_de_uso import ListarSolicitudes
from bugalu.modulos.identidad.aplicacion.listar_usuarios.caso_de_uso import ListarUsuarios
from bugalu.modulos.identidad.aplicacion.obtener_mi_solicitud.caso_de_uso import (
    ObtenerMiSolicitud,
)
from bugalu.modulos.identidad.aplicacion.obtener_perfil.caso_de_uso import ObtenerPerfil
from bugalu.modulos.identidad.aplicacion.rechazar_solicitud.caso_de_uso import RechazarSolicitud
from bugalu.modulos.identidad.aplicacion.verificar_correo.caso_de_uso import VerificarCorreo
from bugalu.modulos.identidad.dominio.solicitud import EstadoSolicitud
from bugalu.modulos.identidad.dominio.usuario import Rol
from bugalu.modulos.identidad.infraestructura.entrada.http.esquemas import (
    Aprobacion,
    CambiosPerfil,
    CambiosUsuario,
    NuevaSolicitud,
    Perfil,
    Rechazo,
    Solicitud,
)
from bugalu.modulos.identidad.infraestructura.salida.repositorio_postgres import (
    RepositorioPostgres,
)
from bugalu.modulos.identidad.infraestructura.salida.repositorio_solicitudes_postgres import (
    RepositorioSolicitudesPostgres,
)

router = APIRouter(tags=["identidad"])

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
    return {
        c: {"model": RespuestaError, "description": _DESCRIPCION[c]} for c in (*codigos, 401, 503)
    }


def _yo(claims: dict[str, Any]) -> UUID:
    return UUID(claims["sub"])


@router.get(
    "/perfil",
    response_model=Perfil,
    summary="Perfil del usuario autenticado",
    responses=_respuestas(404),
)
async def obtener_perfil(request: Request, claims: Claims) -> Perfil:
    async with transaccion_con_identidad(request.app.state.pool, claims) as conexion:
        usuario = await ObtenerPerfil(RepositorioPostgres(conexion)).ejecutar(_yo(claims))
    return Perfil.desde_dominio(usuario, claims.get("email"))


@router.patch(
    "/perfil",
    response_model=Perfil,
    summary="Cambia nombre, telefono y (el cliente) nombre artistico",
    responses=_respuestas(404, 422),
)
async def actualizar_perfil(request: Request, claims: Claims, cuerpo: CambiosPerfil) -> Perfil:
    async with transaccion_con_identidad(request.app.state.pool, claims) as conexion:
        usuario = await ActualizarPerfil(RepositorioPostgres(conexion)).ejecutar(
            _yo(claims), cuerpo.model_dump(exclude_unset=True)
        )
    return Perfil.desde_dominio(usuario, claims.get("email"))


@router.post(
    "/perfil/verificar-correo",
    response_model=Perfil,
    summary="Registra la verificacion del correo (sesion abierta por enlace o Google)",
    responses=_respuestas(404, 409),
)
async def verificar_correo(request: Request, claims: Claims) -> Perfil:
    async with transaccion_con_identidad(request.app.state.pool, claims) as conexion:
        usuario = await VerificarCorreo(RepositorioPostgres(conexion)).ejecutar(_yo(claims))
    return Perfil.desde_dominio(usuario, claims.get("email"))


@router.post(
    "/solicitudes-acceso",
    response_model=Solicitud,
    status_code=201,
    summary="Solicita acceso al panel interno",
    responses=_respuestas(409, 422),
)
async def crear_solicitud(request: Request, claims: Claims, cuerpo: NuevaSolicitud) -> Solicitud:
    async with transaccion_con_identidad(request.app.state.pool, claims) as conexion:
        solicitud = await CrearSolicitud(
            RepositorioPostgres(conexion), RepositorioSolicitudesPostgres(conexion)
        ).ejecutar(_yo(claims), cuerpo.especialidad, cuerpo.mensaje)
    return Solicitud.desde_dominio(solicitud)


@router.get(
    "/solicitudes-acceso/mia",
    response_model=Solicitud,
    summary="Ultima solicitud de acceso del usuario",
    responses=_respuestas(404),
)
async def obtener_mi_solicitud(request: Request, claims: Claims) -> Solicitud:
    async with transaccion_con_identidad(request.app.state.pool, claims) as conexion:
        solicitud = await ObtenerMiSolicitud(RepositorioSolicitudesPostgres(conexion)).ejecutar(
            _yo(claims)
        )
    return Solicitud.desde_dominio(solicitud)


@router.get(
    "/solicitudes-acceso",
    response_model=list[Solicitud],
    summary="Solicitudes de acceso (administrador)",
    responses=_respuestas(403, 422),
)
async def listar_solicitudes(
    request: Request, claims: Claims, estado: EstadoSolicitud | None = None
) -> list[Solicitud]:
    async with transaccion_con_identidad(request.app.state.pool, claims) as conexion:
        solicitudes = await ListarSolicitudes(
            RepositorioPostgres(conexion), RepositorioSolicitudesPostgres(conexion)
        ).ejecutar(_yo(claims), estado)
    return [Solicitud.desde_dominio(s) for s in solicitudes]


@router.post(
    "/solicitudes-acceso/{id_solicitud}/aprobar",
    response_model=Solicitud,
    summary="Aprueba una solicitud y asigna rol y especialidad",
    responses=_respuestas(403, 404, 409, 422),
)
async def aprobar_solicitud(
    request: Request, claims: Claims, id_solicitud: UUID, cuerpo: Aprobacion
) -> Solicitud:
    async with transaccion_con_identidad(request.app.state.pool, claims) as conexion:
        solicitud = await AprobarSolicitud(
            RepositorioPostgres(conexion), RepositorioSolicitudesPostgres(conexion)
        ).ejecutar(_yo(claims), id_solicitud, Rol(cuerpo.rol), cuerpo.especialidad)
    return Solicitud.desde_dominio(solicitud)


@router.post(
    "/solicitudes-acceso/{id_solicitud}/rechazar",
    response_model=Solicitud,
    summary="Rechaza una solicitud con motivo",
    responses=_respuestas(403, 404, 409, 422),
)
async def rechazar_solicitud(
    request: Request, claims: Claims, id_solicitud: UUID, cuerpo: Rechazo
) -> Solicitud:
    async with transaccion_con_identidad(request.app.state.pool, claims) as conexion:
        solicitud = await RechazarSolicitud(
            RepositorioPostgres(conexion), RepositorioSolicitudesPostgres(conexion)
        ).ejecutar(_yo(claims), id_solicitud, cuerpo.motivo)
    return Solicitud.desde_dominio(solicitud)


@router.get(
    "/usuarios",
    response_model=list[Perfil],
    summary="Usuarios, opcionalmente por rol (administrador)",
    responses=_respuestas(403, 422),
)
async def listar_usuarios(request: Request, claims: Claims, rol: Rol | None = None) -> list[Perfil]:
    async with transaccion_con_identidad(request.app.state.pool, claims) as conexion:
        usuarios = await ListarUsuarios(RepositorioPostgres(conexion)).ejecutar(_yo(claims), rol)
    return [Perfil.desde_dominio(u) for u in usuarios]


@router.patch(
    "/usuarios/{id_usuario}",
    response_model=Perfil,
    summary="Cambia rol y especialidad de un usuario (administrador)",
    responses=_respuestas(403, 404, 409, 422),
)
async def actualizar_usuario(
    request: Request, claims: Claims, id_usuario: UUID, cuerpo: CambiosUsuario
) -> Perfil:
    async with transaccion_con_identidad(request.app.state.pool, claims) as conexion:
        usuario = await ActualizarUsuario(RepositorioPostgres(conexion)).ejecutar(
            _yo(claims), id_usuario, cuerpo.model_dump(exclude_unset=True)
        )
    return Perfil.desde_dominio(usuario)
