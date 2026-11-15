from uuid import UUID

from bugalu.modulos.identidad.aplicacion.permisos import exigir_administrador
from bugalu.modulos.identidad.dominio.puertos import RepositorioSolicitudes, RepositorioUsuarios
from bugalu.modulos.identidad.dominio.solicitud import EstadoSolicitud, Solicitud


class ListarSolicitudes:
    def __init__(self, usuarios: RepositorioUsuarios, solicitudes: RepositorioSolicitudes) -> None:
        self._usuarios = usuarios
        self._solicitudes = solicitudes

    async def ejecutar(self, id_actor: UUID, estado: EstadoSolicitud | None) -> list[Solicitud]:
        await exigir_administrador(self._usuarios, id_actor)
        return await self._solicitudes.listar(estado)
