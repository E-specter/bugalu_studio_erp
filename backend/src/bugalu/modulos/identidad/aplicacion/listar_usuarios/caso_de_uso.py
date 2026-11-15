from uuid import UUID

from bugalu.modulos.identidad.aplicacion.permisos import exigir_administrador
from bugalu.modulos.identidad.dominio.puertos import RepositorioUsuarios
from bugalu.modulos.identidad.dominio.usuario import Rol, Usuario


class ListarUsuarios:
    def __init__(self, usuarios: RepositorioUsuarios) -> None:
        self._usuarios = usuarios

    async def ejecutar(self, id_actor: UUID, rol: Rol | None) -> list[Usuario]:
        await exigir_administrador(self._usuarios, id_actor)
        return await self._usuarios.listar(rol)
