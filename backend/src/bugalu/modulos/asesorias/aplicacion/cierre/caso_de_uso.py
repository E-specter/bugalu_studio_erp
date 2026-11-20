from uuid import UUID

from bugalu.modulos.asesorias.aplicacion.consultar.caso_de_uso import ObtenerAsesoria
from bugalu.modulos.asesorias.dominio.asesoria import Asesoria, Constancia, RepositorioAgenda


class MarcarRealizada:
    """CA-12: su profesional o el administrador; ventana, estado y permisos los decide la base."""

    def __init__(self, repo: RepositorioAgenda) -> None:
        self._repo = repo

    async def ejecutar(self, id_actor: UUID, id_asesoria: UUID) -> Asesoria:
        await self._repo.marcar_realizada(id_asesoria)
        return await ObtenerAsesoria(self._repo).ejecutar(id_actor, id_asesoria)


class GuardarNotas:
    """CA-13: notas internas (0 a 5000 caracteres, validadas en el esquema); vacio las borra."""

    def __init__(self, repo: RepositorioAgenda) -> None:
        self._repo = repo

    async def ejecutar(self, id_actor: UUID, id_asesoria: UUID, texto: str) -> Asesoria:
        await self._repo.guardar_notas(id_asesoria, texto)
        return await ObtenerAsesoria(self._repo).ejecutar(id_actor, id_asesoria)


class ObtenerConstancia:
    def __init__(self, repo: RepositorioAgenda) -> None:
        self._repo = repo

    async def ejecutar(self, id_asesoria: UUID) -> Constancia:
        return await self._repo.obtener_constancia(id_asesoria)
