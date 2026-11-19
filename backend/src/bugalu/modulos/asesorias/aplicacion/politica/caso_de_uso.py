"""Politica de RF-18 para asesorias (RF-15 CA-10, CA-11): la base calcula; aqui se orquesta."""

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from bugalu.compartido.errores import HorarioNoDisponible, NivelCambiado, PrecioCambiado
from bugalu.modulos.asesorias.aplicacion.consultar.caso_de_uso import ObtenerAsesoria
from bugalu.modulos.asesorias.dominio import agenda
from bugalu.modulos.asesorias.dominio.asesoria import Asesoria, ContextoAsesoria, RepositorioAgenda
from bugalu.modulos.reservas.dominio import reserva as reglas
from bugalu.modulos.reservas.dominio.disponibilidad import calcular_limites
from bugalu.modulos.reservas.dominio.modelos import VistaCancelacion, VistaReprogramacion


class VistaCancelacionAsesoria:
    def __init__(self, repo: RepositorioAgenda) -> None:
        self._repo = repo

    async def ejecutar(self, id_asesoria: UUID, aviso_en: datetime | None) -> VistaCancelacion:
        return await self._repo.vista_cancelacion(id_asesoria, aviso_en)


class CancelarAsesoria:
    def __init__(self, repo: RepositorioAgenda) -> None:
        self._repo = repo

    async def ejecutar(  # noqa: PLR0913
        self,
        id_actor: UUID,
        id_asesoria: UUID,
        nota: str | None,
        nivel_esperado: int | None,
        por: str | None,
        aviso_en: datetime | None,
    ) -> Asesoria:
        await self._repo.cancelar(id_asesoria, nota, nivel_esperado, por, aviso_en)
        return await ObtenerAsesoria(self._repo).ejecutar(id_actor, id_asesoria)


class MarcarInasistenciaAsesoria:
    """Su profesional o el administrador, desde inicio + tolerancia, sin limite posterior."""

    def __init__(self, repo: RepositorioAgenda) -> None:
        self._repo = repo

    async def ejecutar(self, id_actor: UUID, id_asesoria: UUID) -> Asesoria:
        await self._repo.marcar_inasistencia(id_asesoria)
        return await ObtenerAsesoria(self._repo).ejecutar(id_actor, id_asesoria)


class AplicarExcepcionAsesoria:
    def __init__(self, repo: RepositorioAgenda) -> None:
        self._repo = repo

    async def ejecutar(self, id_actor: UUID, id_asesoria: UUID, motivo: str) -> Asesoria:
        await self._repo.aplicar_excepcion(id_asesoria, motivo)
        return await ObtenerAsesoria(self._repo).ejecutar(id_actor, id_asesoria)


class ElegirDevolucionAsesoria:
    def __init__(self, repo: RepositorioAgenda) -> None:
        self._repo = repo

    async def ejecutar(self, id_actor: UUID, id_asesoria: UUID) -> Asesoria:
        await self._repo.elegir_devolucion_del_estudio(id_asesoria)
        return await ObtenerAsesoria(self._repo).ejecutar(id_actor, id_asesoria)


async def _planificar(
    repo: RepositorioAgenda, id_asesoria: UUID, inicio: datetime, ahora: datetime
) -> ContextoAsesoria:
    """Mismo profesional y duracion: horario publicado, anticipacion y tramo libre sin la propia."""
    contexto = await repo.contexto_asesoria(id_asesoria)  # permisos y elegibilidad
    fin = inicio + (contexto.fin - contexto.inicio)
    reglas.exigir_duracion(inicio, fin)
    minima, maxima = await repo.limites_reserva()
    reglas.exigir_anticipacion(inicio, calcular_limites(ahora, minima, maxima))
    agenda.bloque_que_contiene(
        inicio, fin, await repo.listar_horarios(contexto.id_profesional, inicio, fin)
    )
    if await repo.ocupada_excluyendo(contexto.id_profesional, inicio, fin, id_asesoria):
        raise HorarioNoDisponible("Ese horario ya no esta disponible.")
    return contexto


class SimularReprogramacionAsesoria:
    def __init__(self, repo: RepositorioAgenda) -> None:
        self._repo = repo

    async def ejecutar(
        self, id_asesoria: UUID, inicio: datetime, ahora: datetime
    ) -> VistaReprogramacion:
        c = await _planificar(self._repo, id_asesoria, inicio, ahora)
        return await self._repo.vista_reprogramacion(id_asesoria, inicio, c.total, c.precio)


class ReprogramarAsesoria:
    def __init__(self, repo: RepositorioAgenda) -> None:
        self._repo = repo

    async def ejecutar(  # noqa: PLR0913
        self,
        id_actor: UUID,
        id_asesoria: UUID,
        inicio: datetime,
        nivel_esperado: int | None,
        total_esperado: Decimal | None,
        ahora: datetime,
    ) -> Asesoria:
        c = await _planificar(self._repo, id_asesoria, inicio, ahora)
        try:
            await self._repo.reprogramar(
                id_asesoria, inicio, nivel_esperado, total_esperado, c.precio, c.total
            )
        except (NivelCambiado, PrecioCambiado) as cambio:
            raise type(cambio)(
                cambio.mensaje, {**(cambio.detalles or {}), "precio": c.precio}
            ) from None
        return await ObtenerAsesoria(self._repo).ejecutar(id_actor, id_asesoria)
