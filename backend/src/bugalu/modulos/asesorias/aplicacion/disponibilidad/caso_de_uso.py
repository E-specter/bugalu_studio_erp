from dataclasses import dataclass
from datetime import date, datetime, timedelta
from uuid import UUID

from bugalu.compartido.errores import NoEncontrado, RangoInvalido
from bugalu.modulos.asesorias.dominio.disponibilidad import minutos_libres_por_dia
from bugalu.modulos.asesorias.dominio.modelos import Duracion, Horario, Ocupado
from bugalu.modulos.asesorias.dominio.precios import duraciones
from bugalu.modulos.asesorias.dominio.puertos import RepositorioAsesorias
from bugalu.modulos.reservas.dominio.disponibilidad import (
    MAXIMO_DIAS,
    Limites,
    Tramo,
    calcular_limites,
)


@dataclass(frozen=True)
class DiaLibre:
    fecha: date
    minutos: int


@dataclass(frozen=True)
class Disponibilidad:
    limites: Limites
    horarios: list[Horario]
    ocupados: list[Ocupado]
    dias: list[DiaLibre]
    duraciones: list[Duracion]


class ConsultarDisponibilidadProfesional:
    def __init__(self, repo: RepositorioAsesorias) -> None:
        self._repo = repo

    async def ejecutar(
        self, id_profesional: UUID, desde: datetime, hasta: datetime, ahora: datetime
    ) -> Disponibilidad:
        # shortcut: `excluir_asesoria` (reprogramar) llega en la etapa B, con las asesorias.
        if not timedelta(0) < hasta - desde <= timedelta(days=MAXIMO_DIAS):
            raise RangoInvalido(
                f"El rango debe durar de 1 a {MAXIMO_DIAS} dias.", {"campo": "hasta"}
            )
        profesional = await self._repo.obtener_profesional(id_profesional)
        if profesional is None:
            raise NoEncontrado("No existe el profesional.")
        minima, maxima = await self._repo.limites_reserva()
        limites = calcular_limites(ahora, minima, maxima)
        horarios = await self._repo.listar_horarios(id_profesional, desde, hasta)
        ocupados = await self._repo.ocupados_en(id_profesional, desde, hasta)
        dias = minutos_libres_por_dia(
            desde, hasta, [Tramo(h.inicio, h.fin) for h in horarios], ocupados, limites
        )
        return Disponibilidad(
            limites,
            horarios,
            ocupados,
            [DiaLibre(f, m) for f, m in dias.items()],
            duraciones(profesional.precios, await self._repo.obtener_impuestos()),
        )
