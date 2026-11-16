from bugalu.modulos.catalogo.dominio.precio import Recargos
from bugalu.modulos.catalogo.dominio.puertos import RepositorioCatalogo


class ObtenerRecargos:
    def __init__(self, catalogo: RepositorioCatalogo) -> None:
        self._catalogo = catalogo

    async def ejecutar(self) -> Recargos:
        return await self._catalogo.obtener_recargos()
