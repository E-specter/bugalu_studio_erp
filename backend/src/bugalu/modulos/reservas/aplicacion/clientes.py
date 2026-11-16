from collections.abc import Sequence
from dataclasses import replace

from bugalu.modulos.reservas.dominio.modelos import Referencia, Reserva
from bugalu.modulos.reservas.dominio.puertos import RepositorioReservas


async def con_clientes(
    repositorio: RepositorioReservas, reservas: Sequence[Reserva]
) -> list[Reserva]:
    """Personal y administrador ven el cliente de cada reserva; los demas, nunca."""
    if not reservas or not await repositorio.es_personal():
        return list(reservas)
    nombres = await repositorio.nombres_de_clientes(list({r.id_cliente for r in reservas}))
    return [
        replace(r, cliente=Referencia(r.id_cliente, nombres.get(r.id_cliente))) for r in reservas
    ]
