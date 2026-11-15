from uuid import UUID

from bugalu.modulos.identidad.aplicacion.obtener_perfil.caso_de_uso import PerfilNoEncontrado
from bugalu.modulos.identidad.dominio.puertos import RepositorioSolicitudes, RepositorioUsuarios
from bugalu.modulos.identidad.dominio.reglas import validar_solicitud_nueva
from bugalu.modulos.identidad.dominio.solicitud import Solicitud


class CrearSolicitud:
    def __init__(self, usuarios: RepositorioUsuarios, solicitudes: RepositorioSolicitudes) -> None:
        self._usuarios = usuarios
        self._solicitudes = solicitudes

    async def ejecutar(self, id_usuario: UUID, especialidad: str, mensaje: str | None) -> Solicitud:
        usuario = await self._usuarios.obtener_por_id(id_usuario)
        if usuario is None:
            raise PerfilNoEncontrado
        validar_solicitud_nueva(usuario)
        return await self._solicitudes.crear(id_usuario, especialidad, mensaje)
