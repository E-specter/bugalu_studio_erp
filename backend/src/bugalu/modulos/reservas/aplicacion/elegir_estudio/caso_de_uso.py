from uuid import UUID

from bugalu.modulos.reservas.aplicacion.obtener_reserva.caso_de_uso import ObtenerReserva
from bugalu.modulos.reservas.dominio.modelos import Reserva
from bugalu.modulos.reservas.dominio.puertos import RepositorioReservas


class ElegirDevolucionDelEstudio:
    """RF-18 CA-13: tras una cancelacion del estudio, la devolucion integra de lo pagado."""

    def __init__(self, reservas: RepositorioReservas) -> None:
        self._reservas = reservas

    async def ejecutar(self, id_reserva: UUID) -> Reserva:
        await self._reservas.elegir_estudio_devolucion(id_reserva)
        return await ObtenerReserva(self._reservas).ejecutar(id_reserva)
