from bugalu.modulos.reservas.dominio.modelos import ParametrosDanos
from bugalu.modulos.reservas.dominio.puertos import RepositorioReservas


class ObtenerParametrosDanos:
    """Publico: la pagina de condiciones de uso muestra los dos valores a cualquier visitante."""

    def __init__(self, reservas: RepositorioReservas) -> None:
        self._reservas = reservas

    async def ejecutar(self) -> ParametrosDanos:
        return await self._reservas.obtener_parametros_danos()
