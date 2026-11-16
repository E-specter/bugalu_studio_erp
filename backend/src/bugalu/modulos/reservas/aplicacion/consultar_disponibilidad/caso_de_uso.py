from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from uuid import UUID

from bugalu.compartido.errores import NoEncontrado, RangoInvalido
from bugalu.modulos.reservas.dominio import disponibilidad as calculo
from bugalu.modulos.reservas.dominio.disponibilidad import MAXIMO_DIAS, Limites, Tramo
from bugalu.modulos.reservas.dominio.modelos import Cierre, Franja, ReservaVisible
from bugalu.modulos.reservas.dominio.puertos import RepositorioReservas

_MARGEN = timedelta(hours=1)  # un tramo en el borde del rango necesita ver 1 h mas alla


@dataclass(frozen=True)
class Ocupado:
    inicio: datetime
    fin: datetime
    propia: bool
    reserva: ReservaVisible | None  # solo para personal y administrador
    cliente: str | None


@dataclass(frozen=True)
class Disponibilidad:
    limites: Limites
    franjas: list[Franja]
    ocupados: list[Ocupado]
    cierres: list[Cierre]
    dias: Mapping[date, int]


class ConsultarDisponibilidad:
    def __init__(self, reservas: RepositorioReservas) -> None:
        self._reservas = reservas

    async def ejecutar(
        self,
        id_sala: UUID,
        desde: datetime,
        hasta: datetime,
        ahora: datetime,
        id_usuario: UUID | None,
    ) -> Disponibilidad:
        if not timedelta(0) < hasta - desde <= timedelta(days=MAXIMO_DIAS):
            raise RangoInvalido(
                f"El rango debe durar de 1 a {MAXIMO_DIAS} dias.", {"campo": "hasta"}
            )
        if not await self._reservas.existe_sala(id_sala):
            raise NoEncontrado("No existe la sala.")
        minima, maxima = await self._reservas.limites_reserva()
        limites = calculo.calcular_limites(ahora, minima, maxima)
        ampliado = hasta + _MARGEN
        franjas = await self._reservas.franjas_en(id_sala, desde, ampliado)
        cierres = await self._reservas.cierres_en(id_sala, desde, ampliado)
        ocupados = await self._reservas.ocupacion(id_sala, desde, ampliado)
        dias = calculo.minutos_libres_por_dia(
            desde,
            hasta,
            [Tramo(f.inicio, f.fin) for f in franjas],
            [Tramo(c.inicio, c.fin) for c in cierres],
            ocupados,
            limites,
        )
        visibles: dict[tuple[datetime, datetime], ReservaVisible] = {}
        nombres: Mapping[UUID, str | None] = {}
        personal = False
        if id_usuario is not None:  # con sesion la RLS deja ver las propias, o todas al personal
            visibles = {
                (r.inicio, r.fin_buffer): r
                for r in await self._reservas.reservas_visibles(id_sala, desde, ampliado)
            }
            personal = await self._reservas.es_personal()
            if personal:
                nombres = await self._reservas.nombres_de_clientes(
                    [r.id_cliente for r in visibles.values()]
                )
        rango = Tramo(desde, hasta)
        resultado = []
        for o in ocupados:
            if not o.solapa(rango):
                continue
            r = visibles.get((o.inicio, o.fin))
            resultado.append(
                Ocupado(
                    o.inicio,
                    o.fin,
                    propia=r is not None and r.id_cliente == id_usuario,
                    reserva=r if personal else None,
                    cliente=nombres.get(r.id_cliente) if r is not None else None,
                )
            )
        return Disponibilidad(
            limites,
            [f for f in franjas if Tramo(f.inicio, f.fin).solapa(rango)],
            resultado,
            [c for c in cierres if Tramo(c.inicio, c.fin).solapa(rango)],
            dias,
        )
