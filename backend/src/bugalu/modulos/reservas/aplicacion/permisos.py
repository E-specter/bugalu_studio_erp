from bugalu.compartido.errores import SinPermiso
from bugalu.modulos.reservas.dominio.puertos import RepositorioReservas


async def exigir_administrador(reservas: RepositorioReservas) -> None:
    if not await reservas.es_administrador():
        raise SinPermiso("Solo un administrador puede hacer esto.")
