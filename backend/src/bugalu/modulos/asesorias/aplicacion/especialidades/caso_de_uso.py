from collections.abc import Mapping
from typing import Any
from uuid import UUID

from bugalu.compartido.errores import NoEncontrado
from bugalu.modulos.asesorias.aplicacion.permisos import exigir_administrador
from bugalu.modulos.asesorias.dominio.modelos import Especialidad
from bugalu.modulos.asesorias.dominio.puertos import RepositorioAsesorias


class ListarEspecialidades:
    def __init__(self, repo: RepositorioAsesorias) -> None:
        self._repo = repo

    async def ejecutar(self, todas: bool) -> list[Especialidad]:
        if todas:
            await exigir_administrador(self._repo)
        return await self._repo.listar_especialidades(todas)


class CrearEspecialidad:
    def __init__(self, repo: RepositorioAsesorias) -> None:
        self._repo = repo

    async def ejecutar(self, nombre: str) -> Especialidad:
        await exigir_administrador(self._repo)
        return await self._repo.crear_especialidad(nombre)


class ActualizarEspecialidad:
    def __init__(self, repo: RepositorioAsesorias) -> None:
        self._repo = repo

    async def ejecutar(self, id_especialidad: UUID, cambios: Mapping[str, Any]) -> Especialidad:
        await exigir_administrador(self._repo)
        actualizada = await self._repo.actualizar_especialidad(id_especialidad, cambios)
        if actualizada is None:
            raise NoEncontrado("No existe la especialidad.")
        return actualizada
