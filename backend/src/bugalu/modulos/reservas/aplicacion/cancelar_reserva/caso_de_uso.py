from uuid import UUID

from bugalu.modulos.reservas.aplicacion.obtener_reserva.caso_de_uso import ObtenerReserva
from bugalu.modulos.reservas.dominio.modelos import Reserva
from bugalu.modulos.reservas.dominio.puertos import RepositorioReservas


class CancelarReserva:
    """RN-20 y D-11 v1: el dueno sin pagos; el administrador tambien, con nota si hay pagos."""

    def __init__(self, reservas: RepositorioReservas) -> None:
        self._reservas = reservas

    async def ejecutar(self, id_reserva: UUID, nota: str | None = None) -> Reserva:
        await self._reservas.cancelar_reserva(id_reserva, nota)
        return await ObtenerReserva(self._reservas).ejecutar(id_reserva)
