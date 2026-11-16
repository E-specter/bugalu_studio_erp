from bugalu.modulos.catalogo.aplicacion.permisos import exigir_administrador
from bugalu.modulos.catalogo.dominio.precio import Feriado
from bugalu.modulos.catalogo.dominio.puertos import RepositorioCatalogo


class AgregarFeriado:
    def __init__(self, catalogo: RepositorioCatalogo) -> None:
        self._catalogo = catalogo

    async def ejecutar(self, feriado: Feriado) -> Feriado:
        await exigir_administrador(self._catalogo)
        await self._catalogo.agregar_feriado(feriado)
        return feriado
