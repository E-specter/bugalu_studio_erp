from collections.abc import Mapping
from uuid import UUID

from bugalu.modulos.identidad.aplicacion.obtener_perfil.caso_de_uso import PerfilNoEncontrado
from bugalu.modulos.identidad.dominio.puertos import RepositorioUsuarios
from bugalu.modulos.identidad.dominio.reglas import validar_cambios_de_perfil
from bugalu.modulos.identidad.dominio.usuario import Usuario


class ActualizarPerfil:
    def __init__(self, usuarios: RepositorioUsuarios) -> None:
        self._usuarios = usuarios

    async def ejecutar(self, id_usuario: UUID, cambios: Mapping[str, str | None]) -> Usuario:
        usuario = await self._usuarios.obtener_por_id(id_usuario)
        if usuario is None:
            raise PerfilNoEncontrado
        validar_cambios_de_perfil(usuario, cambios)
        if not cambios:
            return usuario
        return await self._usuarios.actualizar_perfil(id_usuario, cambios)
