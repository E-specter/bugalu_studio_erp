from bugalu.modulos.catalogo.dominio.precio import Servicio
from bugalu.modulos.catalogo.dominio.puertos import RepositorioCatalogo


class ListarServicios:
    def __init__(self, catalogo: RepositorioCatalogo) -> None:
        self._catalogo = catalogo

    async def ejecutar(self) -> list[Servicio]:
        return await self._catalogo.listar_servicios()
