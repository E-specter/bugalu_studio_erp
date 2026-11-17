from bugalu.modulos.catalogo.dominio.precio import ConfiguracionImpuestos
from bugalu.modulos.catalogo.dominio.puertos import RepositorioCatalogo


class ObtenerImpuestos:
    def __init__(self, catalogo: RepositorioCatalogo) -> None:
        self._catalogo = catalogo

    async def ejecutar(self) -> ConfiguracionImpuestos:
        return await self._catalogo.obtener_impuestos()
