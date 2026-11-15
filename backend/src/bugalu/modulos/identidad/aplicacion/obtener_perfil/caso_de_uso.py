from uuid import UUID

from bugalu.compartido.errores import NoEncontrado
from bugalu.modulos.identidad.dominio.puertos import RepositorioUsuarios
from bugalu.modulos.identidad.dominio.usuario import Usuario


class PerfilNoEncontrado(NoEncontrado):
    codigo = "perfil_no_encontrado"

    def __init__(self) -> None:
        super().__init__("No existe el perfil del usuario.")


class ObtenerPerfil:
    def __init__(self, repositorio: RepositorioUsuarios) -> None:
        self._repositorio = repositorio

    async def ejecutar(self, id_usuario: UUID) -> Usuario:
        usuario = await self._repositorio.obtener_por_id(id_usuario)
        if usuario is None:
            raise PerfilNoEncontrado
        return usuario
