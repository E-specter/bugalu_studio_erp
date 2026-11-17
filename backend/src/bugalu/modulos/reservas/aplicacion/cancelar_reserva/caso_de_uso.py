from datetime import datetime
from uuid import UUID

from bugalu.modulos.reservas.aplicacion.obtener_reserva.caso_de_uso import ObtenerReserva
from bugalu.modulos.reservas.dominio.modelos import Reserva
from bugalu.modulos.reservas.dominio.puertos import RepositorioReservas


class CancelarReserva:
    """RF-18 CA-01, CA-03, CA-04: la base calcula el nivel y los montos en una transaccion."""

    def __init__(self, reservas: RepositorioReservas) -> None:
        self._reservas = reservas

    async def ejecutar(
        self,
        id_reserva: UUID,
        nota: str | None = None,
        nivel_esperado: int | None = None,
        por: str | None = None,
        aviso_en: datetime | None = None,
    ) -> Reserva:
        await self._reservas.cancelar_reserva(id_reserva, nota, nivel_esperado, por, aviso_en)
        return await ObtenerReserva(self._reservas).ejecutar(id_reserva)
