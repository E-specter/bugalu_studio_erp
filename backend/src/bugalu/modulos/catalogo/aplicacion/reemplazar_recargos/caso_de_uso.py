from bugalu.modulos.catalogo.aplicacion.permisos import exigir_administrador
from bugalu.modulos.catalogo.dominio.precio import Recargos
from bugalu.modulos.catalogo.dominio.puertos import RepositorioCatalogo


class ReemplazarRecargos:
    def __init__(self, catalogo: RepositorioCatalogo) -> None:
        self._catalogo = catalogo

    async def ejecutar(self, recargos: Recargos) -> Recargos:
        await exigir_administrador(self._catalogo)
        await self._catalogo.guardar_recargos(recargos)
        return await self._catalogo.obtener_recargos()  # lo guardado, con la escala de la base
