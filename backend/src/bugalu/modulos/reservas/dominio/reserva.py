"""Reglas de una reserva de sala (RN-02, RN-12, RN-13, RN-17, RN-18): funciones puras."""

from collections.abc import Sequence
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Protocol

from bugalu.compartido.errores import (
    AnticipacionExcesiva,
    AnticipacionInsuficiente,
    DuracionInvalida,
    FueraDeFranja,
)
from bugalu.modulos.reservas.dominio.disponibilidad import LIMA, PASO, Limites

MAXIMA_DURACION = timedelta(hours=8)


def exigir_duracion(inicio: datetime, fin: datetime) -> None:
    """Instantes con zona, en multiplos de 30 min, y duracion de 30 min a 8 h (RN-12)."""
    if inicio.tzinfo is None or fin.tzinfo is None:
        raise DuracionInvalida(
            "El inicio y el fin deben incluir la zona horaria.", {"campo": "fin"}
        )
    desde = inicio.astimezone(LIMA)
    duracion = fin - inicio
    if (
        desde.minute % 30
        or desde.second
        or desde.microsecond
        or duracion % PASO
        or not PASO <= duracion <= MAXIMA_DURACION
    ):
        raise DuracionInvalida(
            "La reserva empieza en media hora exacta y dura de 30 minutos a 8 horas, "
            "en múltiplos de 30 minutos.",
            {"campo": "fin"},
        )


def exigir_anticipacion(inicio: datetime, limites: Limites) -> None:
    if inicio < limites.desde:
        raise AnticipacionInsuficiente("La reserva necesita más anticipación.", {"campo": "inicio"})
    if inicio > limites.hasta:
        raise AnticipacionExcesiva("La reserva es con demasiada anticipación.", {"campo": "inicio"})


class _Intervalo(Protocol):
    @property
    def inicio(self) -> datetime: ...

    @property
    def fin(self) -> datetime: ...


def franja_que_contiene[T: _Intervalo](inicio: datetime, fin: datetime, franjas: Sequence[T]) -> T:
    """La franja que contiene [inicio, fin) (el fin ya incluye el buffer de RN-02)."""
    for franja in franjas:
        if franja.inicio <= inicio and fin <= franja.fin:
            return franja
    raise FueraDeFranja(
        "El tramo, con su margen de 30 minutos, no cabe en un horario publicado.",
        {"campo": "inicio"},
    )


def calcular_vence_pago(ahora: datetime, inicio: datetime, dias: int, horas: int) -> datetime:
    """RN-18: lo mas tarde entre inicio - `dias` y ahora + `horas`; nunca despues del inicio."""
    return min(inicio, max(inicio - timedelta(days=dias), ahora + timedelta(hours=horas)))


def cuotas_de(total: Decimal, anticipo: Decimal) -> list[tuple[str, Decimal]]:
    """RN-13: `al_reservar` es el anticipo de la simulacion y `al_terminar` el resto."""
    return [("al_reservar", anticipo), ("al_terminar", total - anticipo)]
