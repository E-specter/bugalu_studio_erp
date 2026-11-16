from bugalu.modulos.reservas.dominio.modelos import Reserva
from bugalu.modulos.reservas.dominio.puertos import RepositorioReservas


class ListarMisReservas:
    def __init__(self, reservas: RepositorioReservas) -> None:
        self._reservas = reservas

    async def ejecutar(self) -> list[Reserva]:
        return await self._reservas.listar_mias()
