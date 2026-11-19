from collections.abc import Mapping
from typing import Any
from uuid import UUID

from bugalu.compartido.errores import NoEncontrado, SinPermiso
from bugalu.modulos.asesorias.aplicacion.consultar.caso_de_uso import ObtenerAsesoria
from bugalu.modulos.asesorias.dominio import agenda
from bugalu.modulos.asesorias.dominio.asesoria import Asesoria, RepositorioAgenda


class CambiarEncuentro:
    def __init__(self, repo: RepositorioAgenda) -> None:
        self._repo = repo

    async def ejecutar(
        self, id_actor: UUID, id_asesoria: UUID, cambios: Mapping[str, Any]
    ) -> Asesoria:
        repo = self._repo
        actual = await repo.obtener_asesoria(id_asesoria)
        if actual is None:
            raise NoEncontrado("No existe la asesoria.")
        if actual.profesional.id != id_actor and not await repo.es_administrador():
            raise SinPermiso("Solo su profesional o un administrador cambia el encuentro.")
        modalidad, lugar, enlace = agenda.combinar_encuentro(
            (actual.modalidad, actual.lugar, actual.enlace), cambios
        )
        await repo.cambiar_encuentro(id_asesoria, modalidad, lugar, enlace)  # estado y fin: la base
        return await ObtenerAsesoria(repo).ejecutar(id_actor, id_asesoria)
