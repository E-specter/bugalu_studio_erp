from datetime import datetime, timedelta

from bugalu.compartido.errores import RangoInvalido, SinPermiso
from bugalu.modulos.reservas.aplicacion.clientes import con_clientes
from bugalu.modulos.reservas.dominio.disponibilidad import MAXIMO_DIAS
from bugalu.modulos.reservas.dominio.modelos import Reserva
from bugalu.modulos.reservas.dominio.puertos import RepositorioReservas


class ListarReservas:
    def __init__(self, reservas: RepositorioReservas) -> None:
        self._reservas = reservas

    async def ejecutar(self, desde: datetime, hasta: datetime) -> list[Reserva]:
        if not await self._reservas.es_personal():
            raise SinPermiso("Solo el personal o un administrador lista reservas.")
        if not timedelta(0) < hasta - desde <= timedelta(days=MAXIMO_DIAS):
            raise RangoInvalido(
                f"El rango debe durar de 1 a {MAXIMO_DIAS} dias.", {"campo": "hasta"}
            )
        reservas = await self._reservas.listar_en_rango(desde, hasta)
        return await con_clientes(self._reservas, reservas)
