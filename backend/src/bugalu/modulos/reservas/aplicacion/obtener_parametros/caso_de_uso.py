from typing import Any

from bugalu.modulos.reservas.aplicacion.permisos import exigir_administrador
from bugalu.modulos.reservas.dominio.puertos import RepositorioReservas


class ObtenerParametros:
    def __init__(self, reservas: RepositorioReservas) -> None:
        self._reservas = reservas

    async def ejecutar(self) -> dict[str, Any]:
        await exigir_administrador(self._reservas)
        return await self._reservas.obtener_parametros()
