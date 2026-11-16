from datetime import date

from bugalu.compartido.errores import NoEncontrado
from bugalu.modulos.catalogo.aplicacion.permisos import exigir_administrador
from bugalu.modulos.catalogo.dominio.puertos import RepositorioCatalogo


class EliminarFeriado:
    def __init__(self, catalogo: RepositorioCatalogo) -> None:
        self._catalogo = catalogo

    async def ejecutar(self, fecha: date) -> None:
        await exigir_administrador(self._catalogo)
        if not await self._catalogo.eliminar_feriado(fecha):
            raise NoEncontrado("No hay un feriado en esa fecha.")
