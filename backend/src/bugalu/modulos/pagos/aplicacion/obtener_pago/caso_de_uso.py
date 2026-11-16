from uuid import UUID

from bugalu.compartido.errores import NoEncontrado, SinPermiso
from bugalu.modulos.pagos.dominio.modelos import Pago
from bugalu.modulos.pagos.dominio.puertos import RepositorioPagos


async def pago_visible(pagos: RepositorioPagos, id_pago: UUID) -> Pago:
    pago = await pagos.obtener_pago(id_pago)
    if pago is None:  # la RLS oculta los ajenos: 403 si existe, 404 si no
        if await pagos.existe_pago(id_pago):
            raise SinPermiso("Ese pago no es tuyo.")
        raise NoEncontrado("No existe el pago.")
    return pago


class ObtenerPago:
    def __init__(self, pagos: RepositorioPagos) -> None:
        self._pagos = pagos

    async def ejecutar(self, id_pago: UUID) -> Pago:
        return await pago_visible(self._pagos, id_pago)
