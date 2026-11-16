from collections.abc import Sequence
from uuid import UUID

from bugalu.compartido.errores import NoEncontrado
from bugalu.modulos.reservas.aplicacion.permisos import exigir_administrador
from bugalu.modulos.reservas.dominio.disponibilidad import Tramo
from bugalu.modulos.reservas.dominio.modelos import Franja
from bugalu.modulos.reservas.dominio.puertos import RepositorioReservas


class PublicarFranjas:
    def __init__(self, reservas: RepositorioReservas) -> None:
        self._reservas = reservas

    async def ejecutar(self, id_sala: UUID, tramos: Sequence[Tramo]) -> list[Franja]:
        await exigir_administrador(self._reservas)
        if not await self._reservas.existe_sala(id_sala):
            raise NoEncontrado("No existe la sala.")
        return await self._reservas.insertar_franjas(id_sala, tramos)
