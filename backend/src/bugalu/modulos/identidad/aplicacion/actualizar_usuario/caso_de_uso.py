from collections.abc import Mapping
from typing import Any
from uuid import UUID

from bugalu.compartido.errores import NoEncontrado
from bugalu.modulos.identidad.aplicacion.permisos import exigir_administrador
from bugalu.modulos.identidad.dominio.puertos import RepositorioUsuarios
from bugalu.modulos.identidad.dominio.usuario import Usuario


class ActualizarUsuario:
    """`cambios` trae solo los campos enviados (`rol`, `especialidad`); el resto se conserva."""

    def __init__(self, usuarios: RepositorioUsuarios) -> None:
        self._usuarios = usuarios

    async def ejecutar(
        self, id_actor: UUID, id_usuario: UUID, cambios: Mapping[str, Any]
    ) -> Usuario:
        await exigir_administrador(self._usuarios, id_actor)
        usuario = await self._usuarios.obtener_por_id(id_usuario)
        if usuario is None:
            raise NoEncontrado("No existe el usuario.")
        if not cambios:
            return usuario
        await self._usuarios.asignar_rol(
            id_usuario,
            cambios.get("rol", usuario.rol),
            cambios.get("especialidad", usuario.especialidad),
        )
        actualizado = await self._usuarios.obtener_por_id(id_usuario)
        if actualizado is None:
            raise NoEncontrado("No existe el usuario.")
        return actualizado
