from datetime import datetime
from uuid import UUID

from bugalu.modulos.reservas.dominio.modelos import VistaCancelacion as Vista
from bugalu.modulos.reservas.dominio.puertos import RepositorioReservas


class VistaCancelacion:
    """RF-18 CA-02: nivel, retencion y credito de cancelar ahora (o en `aviso_en`)."""

    def __init__(self, reservas: RepositorioReservas) -> None:
        self._reservas = reservas

    async def ejecutar(self, id_reserva: UUID, aviso_en: datetime | None = None) -> Vista:
        return await self._reservas.vista_cancelacion(id_reserva, aviso_en)
