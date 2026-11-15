from uuid import UUID

from bugalu.modulos.identidad.aplicacion.obtener_perfil.caso_de_uso import PerfilNoEncontrado
from bugalu.modulos.identidad.dominio.puertos import RepositorioUsuarios
from bugalu.modulos.identidad.dominio.usuario import Usuario


class VerificarCorreo:
    def __init__(self, usuarios: RepositorioUsuarios) -> None:
        self._usuarios = usuarios

    async def ejecutar(self, id_usuario: UUID) -> Usuario:
        if not await self._usuarios.marcar_correo_verificado(id_usuario):
            raise PerfilNoEncontrado
        usuario = await self._usuarios.obtener_por_id(id_usuario)
        if usuario is None:
            raise PerfilNoEncontrado
        return usuario
