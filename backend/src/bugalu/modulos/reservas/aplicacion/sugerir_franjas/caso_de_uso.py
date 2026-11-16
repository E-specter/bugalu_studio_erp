from datetime import datetime, time
from uuid import UUID

from bugalu.compartido.errores import DatosInvalidos, NoEncontrado
from bugalu.modulos.reservas.aplicacion.permisos import exigir_administrador
from bugalu.modulos.reservas.dominio.disponibilidad import (
    LIMA,
    Tramo,
    lunes_de_semana_iso,
    sugerir_semana,
)
from bugalu.modulos.reservas.dominio.puertos import RepositorioReservas


class SugerirFranjas:
    def __init__(self, reservas: RepositorioReservas) -> None:
        self._reservas = reservas

    async def ejecutar(self, id_sala: UUID, semana: str) -> list[Tramo]:
        await exigir_administrador(self._reservas)
        try:
            lunes = lunes_de_semana_iso(semana)
        except ValueError:
            raise DatosInvalidos("La semana no existe.", {"campo": "semana"}) from None
        if not await self._reservas.existe_sala(id_sala):
            raise NoEncontrado("No existe la sala.")
        previas = await self._reservas.franjas_antes_de(
            id_sala, datetime.combine(lunes, time(), LIMA)
        )
        return sugerir_semana([Tramo(f.inicio, f.fin) for f in previas], lunes)
