from collections.abc import Mapping

from bugalu.modulos.reservas.aplicacion.permisos import exigir_administrador
from bugalu.modulos.reservas.dominio.puertos import RepositorioReservas


class ActualizarParametros:
    def __init__(self, reservas: RepositorioReservas) -> None:
        self._reservas = reservas

    async def ejecutar(self, cambios: Mapping[str, int]) -> dict[str, int]:
        await exigir_administrador(self._reservas)
        if cambios:
            await self._reservas.guardar_parametros(cambios)
        return await self._reservas.obtener_parametros()
