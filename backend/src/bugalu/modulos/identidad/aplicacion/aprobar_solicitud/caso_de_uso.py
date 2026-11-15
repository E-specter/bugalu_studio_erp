from uuid import UUID

from bugalu.compartido.errores import Conflicto, NoEncontrado
from bugalu.modulos.identidad.aplicacion.permisos import exigir_administrador
from bugalu.modulos.identidad.dominio.puertos import RepositorioSolicitudes, RepositorioUsuarios
from bugalu.modulos.identidad.dominio.reglas import validar_resolucion
from bugalu.modulos.identidad.dominio.solicitud import EstadoSolicitud, Solicitud
from bugalu.modulos.identidad.dominio.usuario import Rol


class AprobarSolicitud:
    """Marca la solicitud y asigna el rol; el router los envuelve en una sola transaccion."""

    def __init__(self, usuarios: RepositorioUsuarios, solicitudes: RepositorioSolicitudes) -> None:
        self._usuarios = usuarios
        self._solicitudes = solicitudes

    async def ejecutar(
        self, id_actor: UUID, id_solicitud: UUID, rol: Rol, especialidad: str
    ) -> Solicitud:
        await exigir_administrador(self._usuarios, id_actor)
        solicitud = await self._solicitudes.obtener(id_solicitud)
        if solicitud is None:
            raise NoEncontrado("No existe la solicitud.")
        validar_resolucion(solicitud)
        resuelta = await self._solicitudes.resolver(
            id_solicitud, EstadoSolicitud.APROBADA, id_actor, None
        )
        if resuelta is None:  # otro administrador la resolvio entre la lectura y el update
            raise Conflicto("La solicitud ya fue resuelta.")
        await self._usuarios.asignar_rol(solicitud.id_usuario, rol, especialidad)
        return resuelta
