from uuid import UUID

from bugalu.compartido.errores import Conflicto, NoEncontrado
from bugalu.modulos.identidad.aplicacion.permisos import exigir_administrador
from bugalu.modulos.identidad.dominio.puertos import RepositorioSolicitudes, RepositorioUsuarios
from bugalu.modulos.identidad.dominio.reglas import validar_resolucion
from bugalu.modulos.identidad.dominio.solicitud import EstadoSolicitud, Solicitud


class RechazarSolicitud:
    def __init__(self, usuarios: RepositorioUsuarios, solicitudes: RepositorioSolicitudes) -> None:
        self._usuarios = usuarios
        self._solicitudes = solicitudes

    async def ejecutar(self, id_actor: UUID, id_solicitud: UUID, motivo: str) -> Solicitud:
        await exigir_administrador(self._usuarios, id_actor)
        solicitud = await self._solicitudes.obtener(id_solicitud)
        if solicitud is None:
            raise NoEncontrado("No existe la solicitud.")
        validar_resolucion(solicitud)
        resuelta = await self._solicitudes.resolver(
            id_solicitud, EstadoSolicitud.RECHAZADA, id_actor, motivo
        )
        if resuelta is None:
            raise Conflicto("La solicitud ya fue resuelta.")
        return resuelta
