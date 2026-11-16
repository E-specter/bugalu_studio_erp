from uuid import UUID

from bugalu.compartido.errores import FranjaConReservas, NoEncontrado
from bugalu.modulos.reservas.aplicacion.permisos import exigir_administrador
from bugalu.modulos.reservas.dominio.puertos import RepositorioReservas


class RetirarFranja:
    def __init__(self, reservas: RepositorioReservas) -> None:
        self._reservas = reservas

    async def ejecutar(self, id_franja: UUID) -> None:
        await exigir_administrador(self._reservas)
        franja = await self._reservas.obtener_franja(id_franja)
        if franja is None:
            raise NoEncontrado("No existe la franja.")
        if await self._reservas.ocupacion(franja.id_sala, franja.inicio, franja.fin):
            raise FranjaConReservas("La franja tiene reservas vigentes.")
        await self._reservas.eliminar_franja(id_franja)
