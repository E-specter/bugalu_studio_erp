from uuid import UUID

from bugalu.compartido.errores import SinPermiso
from bugalu.modulos.pagos.aplicacion.obtener_pago.caso_de_uso import pago_visible
from bugalu.modulos.pagos.dominio.modelos import Pago
from bugalu.modulos.pagos.dominio.puertos import RepositorioPagos


async def _exigir_administrador(pagos: RepositorioPagos) -> None:
    if not await pagos.es_administrador():
        raise SinPermiso("Solo el administrador valida pagos.")


class ListarPagos:
    def __init__(self, pagos: RepositorioPagos) -> None:
        self._pagos = pagos

    async def ejecutar(self, estado: str) -> list[Pago]:
        await _exigir_administrador(self._pagos)
        return await self._pagos.listar_pagos(estado)


class AprobarPago:
    def __init__(self, pagos: RepositorioPagos) -> None:
        self._pagos = pagos

    async def ejecutar(self, id_pago: UUID) -> Pago:
        await self._pagos.aprobar_pago(id_pago)
        return await pago_visible(self._pagos, id_pago)


class RechazarPago:
    def __init__(self, pagos: RepositorioPagos) -> None:
        self._pagos = pagos

    async def ejecutar(self, id_pago: UUID, motivo: str) -> Pago:
        await self._pagos.rechazar_pago(id_pago, motivo)
        return await pago_visible(self._pagos, id_pago)
