from collections.abc import Sequence
from datetime import datetime, time
from uuid import UUID

from bugalu.compartido.errores import DatosInvalidos, NoEncontrado
from bugalu.modulos.asesorias.aplicacion.permisos import exigir_gestion
from bugalu.modulos.asesorias.dominio.disponibilidad import validar_horarios_nuevos
from bugalu.modulos.asesorias.dominio.modelos import Horario
from bugalu.modulos.asesorias.dominio.puertos import RepositorioAsesorias
from bugalu.modulos.reservas.dominio.disponibilidad import (
    LIMA,
    Tramo,
    lunes_de_semana_iso,
    sugerir_semana,
)


async def _exigir_perfil_y_gestion(
    repo: RepositorioAsesorias, id_actor: UUID, id_profesional: UUID
) -> None:
    if await repo.obtener_profesional(id_profesional) is None:
        raise NoEncontrado("No existe el profesional.")
    await exigir_gestion(repo, id_actor, id_profesional)


class SugerirHorarios:
    def __init__(self, repo: RepositorioAsesorias) -> None:
        self._repo = repo

    async def ejecutar(self, id_actor: UUID, id_profesional: UUID, semana: str) -> list[Tramo]:
        await _exigir_perfil_y_gestion(self._repo, id_actor, id_profesional)
        try:
            lunes = lunes_de_semana_iso(semana)
        except ValueError:
            raise DatosInvalidos("La semana no existe.", {"campo": "semana"}) from None
        previos = await self._repo.horarios_antes_de(
            id_profesional, datetime.combine(lunes, time(), LIMA)
        )
        return sugerir_semana([Tramo(h.inicio, h.fin) for h in previos], lunes)


class PublicarHorarios:
    def __init__(self, repo: RepositorioAsesorias) -> None:
        self._repo = repo

    async def ejecutar(
        self, id_actor: UUID, id_profesional: UUID, tramos: Sequence[Tramo], ahora: datetime
    ) -> list[Horario]:
        await _exigir_perfil_y_gestion(self._repo, id_actor, id_profesional)
        validar_horarios_nuevos(tramos, ahora)
        return await self._repo.insertar_horarios(id_profesional, tramos)


class RetirarHorario:
    def __init__(self, repo: RepositorioAsesorias) -> None:
        self._repo = repo

    async def ejecutar(self, id_actor: UUID, id_profesional: UUID, id_horario: UUID) -> None:
        await _exigir_perfil_y_gestion(self._repo, id_actor, id_profesional)
        if await self._repo.obtener_horario(id_profesional, id_horario) is None:
            raise NoEncontrado("No existe el horario.")
        await self._repo.retirar_horario(
            id_horario
        )  # la base cuenta las vivas: HorarioConAsesorias
