from uuid import UUID

from bugalu.modulos.reservas.aplicacion.obtener_reserva.caso_de_uso import ObtenerReserva
from bugalu.modulos.reservas.dominio.modelos import Reserva
from bugalu.modulos.reservas.dominio.puertos import RepositorioReservas


class AplicarExcepcion:
    """RF-18 CA-12: el administrador trata un nivel 2 o 3, o una inasistencia, como nivel 1."""

    def __init__(self, reservas: RepositorioReservas) -> None:
        self._reservas = reservas

    async def ejecutar(self, id_reserva: UUID, motivo: str) -> Reserva:
        await self._reservas.aplicar_excepcion(id_reserva, motivo)
        return await ObtenerReserva(self._reservas).ejecutar(id_reserva)
