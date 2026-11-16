from bugalu.modulos.catalogo.dominio.precio import Especialista
from bugalu.modulos.catalogo.dominio.puertos import RepositorioCatalogo


class ListarEspecialistas:
    def __init__(self, catalogo: RepositorioCatalogo) -> None:
        self._catalogo = catalogo

    async def ejecutar(self) -> list[Especialista]:
        return await self._catalogo.listar_especialistas()
