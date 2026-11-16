from bugalu.modulos.reservas.dominio.modelos import Sala
from bugalu.modulos.reservas.dominio.puertos import RepositorioReservas


class ListarSalas:
    def __init__(self, reservas: RepositorioReservas) -> None:
        self._reservas = reservas

    async def ejecutar(self) -> list[Sala]:
        return await self._reservas.listar_salas()
