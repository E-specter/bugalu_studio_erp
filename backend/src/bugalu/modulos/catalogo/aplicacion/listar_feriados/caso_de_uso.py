from bugalu.modulos.catalogo.dominio.precio import Feriado
from bugalu.modulos.catalogo.dominio.puertos import RepositorioCatalogo


class ListarFeriados:
    def __init__(self, catalogo: RepositorioCatalogo) -> None:
        self._catalogo = catalogo

    async def ejecutar(self, anio: int | None) -> list[Feriado]:
        return await self._catalogo.listar_feriados(anio)
