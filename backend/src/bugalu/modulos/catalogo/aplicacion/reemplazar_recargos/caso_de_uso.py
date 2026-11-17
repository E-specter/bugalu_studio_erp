from bugalu.modulos.catalogo.aplicacion.permisos import exigir_administrador
from bugalu.modulos.catalogo.dominio import cambios_sensibles as sensibles
from bugalu.modulos.catalogo.dominio.precio import Recargos
from bugalu.modulos.catalogo.dominio.puertos import RepositorioCatalogo


class ReemplazarRecargos:
    def __init__(self, catalogo: RepositorioCatalogo) -> None:
        self._catalogo = catalogo

    async def ejecutar(self, recargos: Recargos) -> Recargos:
        await exigir_administrador(self._catalogo)
        sensibles.exigir_confirmacion(
            "recargos",
            sensibles.valores_recargos(await self._catalogo.obtener_recargos()),
            sensibles.valores_recargos(recargos),
        )
        # Sin 428 no cambia ningun campo sensible: no hay nada que escribir.
        return await self._catalogo.obtener_recargos()
