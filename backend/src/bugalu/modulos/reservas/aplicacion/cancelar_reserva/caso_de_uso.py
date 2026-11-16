from uuid import UUID

from bugalu.modulos.reservas.aplicacion.obtener_reserva.caso_de_uso import ObtenerReserva
from bugalu.modulos.reservas.dominio.modelos import Reserva
from bugalu.modulos.reservas.dominio.puertos import RepositorioReservas


class CancelarReserva:
    """RN-20: el dueno sin pagos; el administrador tambien (D-11 abierta). La base decide."""

    def __init__(self, reservas: RepositorioReservas) -> None:
        self._reservas = reservas

    async def ejecutar(self, id_reserva: UUID) -> Reserva:
        await self._reservas.cancelar_reserva(id_reserva)
        return await ObtenerReserva(self._reservas).ejecutar(id_reserva)
