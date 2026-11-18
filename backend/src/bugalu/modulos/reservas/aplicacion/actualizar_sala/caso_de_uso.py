from datetime import date
from uuid import UUID

from bugalu.compartido.errores import NoEncontrado
from bugalu.modulos.reservas.aplicacion.permisos import exigir_administrador
from bugalu.modulos.reservas.dominio.modelos import Sala
from bugalu.modulos.reservas.dominio.puertos import RepositorioReservas
from bugalu.modulos.reservas.dominio.sala import exigir_itse_vigente


class ActualizarSala:
    def __init__(self, reservas: RepositorioReservas) -> None:
        self._reservas = reservas

    async def ejecutar(
        self, id_sala: UUID, aforo: int, certificado: str, vence: date, hoy: date
    ) -> Sala:
        await exigir_administrador(self._reservas)
        exigir_itse_vigente(vence, hoy)
        sala = await self._reservas.actualizar_itse_sala(id_sala, aforo, certificado, vence)
        if sala is None:
            raise NoEncontrado("No existe la sala.")
        return sala
