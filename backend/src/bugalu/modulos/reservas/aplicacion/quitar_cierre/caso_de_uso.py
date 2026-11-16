from uuid import UUID

from bugalu.compartido.errores import NoEncontrado
from bugalu.modulos.reservas.aplicacion.permisos import exigir_administrador
from bugalu.modulos.reservas.dominio.puertos import RepositorioReservas


class QuitarCierre:
    def __init__(self, reservas: RepositorioReservas) -> None:
        self._reservas = reservas

    async def ejecutar(self, id_cierre: UUID) -> None:
        await exigir_administrador(self._reservas)
        if await self._reservas.obtener_cierre(id_cierre) is None:
            raise NoEncontrado("No existe el cierre.")
        await self._reservas.eliminar_cierre(id_cierre)
