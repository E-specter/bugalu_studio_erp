from bugalu.compartido.errores import SinPermiso
from bugalu.modulos.catalogo.dominio.puertos import RepositorioCatalogo


async def exigir_administrador(catalogo: RepositorioCatalogo) -> None:
    if not await catalogo.es_administrador():
        raise SinPermiso("Solo un administrador puede hacer esto.")
