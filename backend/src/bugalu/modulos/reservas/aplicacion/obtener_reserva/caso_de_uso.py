from uuid import UUID

from bugalu.compartido.errores import NoEncontrado, SinPermiso
from bugalu.modulos.reservas.aplicacion.clientes import con_clientes
from bugalu.modulos.reservas.dominio.modelos import Reserva
from bugalu.modulos.reservas.dominio.puertos import RepositorioReservas


class ObtenerReserva:
    def __init__(self, reservas: RepositorioReservas) -> None:
        self._reservas = reservas

    async def ejecutar(self, id_reserva: UUID) -> Reserva:
        reserva = await self._reservas.obtener_reserva(id_reserva)
        if reserva is None:  # la RLS oculta las ajenas: 403 si existe, 404 si no
            if await self._reservas.existe_reserva(id_reserva):
                raise SinPermiso("Esa reserva no es tuya.")
            raise NoEncontrado("No existe la reserva.")
        return (await con_clientes(self._reservas, [reserva]))[0]
