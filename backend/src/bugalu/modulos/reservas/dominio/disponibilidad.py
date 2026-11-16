"""Disponibilidad (RN-12, RN-17): funciones puras; dia y semana en hora de Lima (UTC-5)."""

from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone

LIMA = timezone(timedelta(hours=-5))
PASO = timedelta(minutes=30)
MAXIMO_DIAS = 42


@dataclass(frozen=True)
class Tramo:
    inicio: datetime
    fin: datetime

    def solapa(self, otro: Tramo) -> bool:
        return self.inicio < otro.fin and otro.inicio < self.fin


@dataclass(frozen=True)
class Limites:
    desde: datetime
    hasta: datetime


def calcular_limites(ahora: datetime, minima_horas: int, maxima_semanas: int) -> Limites:
    return Limites(ahora + timedelta(hours=minima_horas), ahora + timedelta(weeks=maxima_semanas))


def dia_de_lima(instante: datetime) -> date:
    return instante.astimezone(LIMA).date()


def dias_del_rango(desde: datetime, hasta: datetime) -> list[date]:
    primero, ultimo = dia_de_lima(desde), dia_de_lima(hasta - timedelta(microseconds=1))
    return [primero + timedelta(days=n) for n in range((ultimo - primero).days + 1)]


def minutos_libres_por_dia(
    desde: datetime,
    hasta: datetime,
    franjas: Iterable[Tramo],
    cierres: Sequence[Tramo],
    ocupados: Sequence[Tramo],
    limites: Limites,
) -> dict[date, int]:
    """Minutos reservables por dia: tramos de 30 min que arrancan en [desde, hasta) y cuyo margen.

    de 30 min detras (el buffer de RN-02) cabe en la franja, sin tocar cierres ni ocupados.
    Un tramo se atribuye al dia de Lima en que empieza.
    """
    libres = dict.fromkeys(dias_del_rango(desde, hasta), 0)
    bloqueos = [*cierres, *ocupados]
    for franja in franjas:
        inicio = franja.inicio
        while inicio + 2 * PASO <= franja.fin:
            propuesto = Tramo(inicio, inicio + 2 * PASO)
            if (
                desde <= inicio < hasta
                and limites.desde <= inicio <= limites.hasta
                and not any(propuesto.solapa(b) for b in bloqueos)
            ):
                libres[dia_de_lima(inicio)] += 30
            inicio += PASO
    return libres


def lunes_de_semana_iso(semana: str) -> date:
    """`AAAA-Www` -> lunes de esa semana ISO; ValueError si no existe."""
    anio, _, numero = semana.partition("-W")
    if not 2000 <= int(anio) <= 2100:
        raise ValueError("Anio fuera de 2000 a 2100.")
    return date.fromisocalendar(int(anio), int(numero), 1)


def _lunes_de(instante: datetime) -> date:
    dia = dia_de_lima(instante)
    return dia - timedelta(days=dia.weekday())


def sugerir_semana(franjas: Iterable[Tramo], lunes: date) -> list[Tramo]:
    """La ultima semana publicada antes de `lunes`, desplazada a esa semana (vacia si no hay)."""
    previas = [f for f in franjas if _lunes_de(f.inicio) < lunes]
    if not previas:
        return []
    ultima = max(_lunes_de(f.inicio) for f in previas)
    desplazo = lunes - ultima
    return sorted(
        (
            Tramo(f.inicio + desplazo, f.fin + desplazo)
            for f in previas
            if _lunes_de(f.inicio) == ultima
        ),
        key=lambda f: f.inicio,
    )
