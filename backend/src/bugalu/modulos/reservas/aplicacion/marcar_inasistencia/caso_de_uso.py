from uuid import UUID

from bugalu.modulos.reservas.aplicacion.obtener_reserva.caso_de_uso import ObtenerReserva
from bugalu.modulos.reservas.dominio.modelos import Reserva
from bugalu.modulos.reservas.dominio.puertos import RepositorioReservas


class MarcarInasistencia:
    """RF-18 CA-11: personal o administrador, desde inicio + tolerancia hasta el fin."""

    def __init__(self, reservas: RepositorioReservas) -> None:
        self._reservas = reservas

    async def ejecutar(self, id_reserva: UUID) -> Reserva:
        await self._reservas.marcar_inasistencia(id_reserva)
        return await ObtenerReserva(self._reservas).ejecutar(id_reserva)
