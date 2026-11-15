from uuid import UUID

from bugalu.compartido.errores import NoEncontrado
from bugalu.modulos.identidad.dominio.puertos import RepositorioSolicitudes
from bugalu.modulos.identidad.dominio.solicitud import Solicitud


class ObtenerMiSolicitud:
    def __init__(self, solicitudes: RepositorioSolicitudes) -> None:
        self._solicitudes = solicitudes

    async def ejecutar(self, id_usuario: UUID) -> Solicitud:
        solicitud = await self._solicitudes.obtener_ultima_de(id_usuario)
        if solicitud is None:
            raise NoEncontrado("No hay una solicitud de acceso.")
        return solicitud
