"""Reglas de una reserva de sala (RN-02, RN-12, RN-13, RN-17, RN-18): funciones puras."""

from collections.abc import Iterable, Sequence
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Protocol

from bugalu.compartido.errores import (
    AnticipacionExcesiva,
    AnticipacionInsuficiente,
    AutorizacionMenorPendiente,
    DuracionInvalida,
    FueraDeFranja,
    PerfilIncompleto,
    ReaceptacionRequerida,
    TextoDesactualizado,
)
from bugalu.modulos.reservas.dominio.disponibilidad import LIMA, PASO, Limites
from bugalu.modulos.reservas.dominio.modelos import PagoCuota, RequisitosReserva

MAXIMA_DURACION = timedelta(hours=8)


def exigir_requisitos(requisitos: RequisitosReserva, version_condiciones: str) -> None:
    """RF-17: registro al dia, perfil completo, no menor (etapa A) y condiciones vigentes."""
    if requisitos.pendientes:
        raise ReaceptacionRequerida(
            "Acepta los textos pendientes para reservar.", {"textos": list(requisitos.pendientes)}
        )
    if requisitos.campos_faltantes:
        raise PerfilIncompleto(
            "Completa tus datos para reservar.", {"campos": list(requisitos.campos_faltantes)}
        )
    if requisitos.es_menor:
        raise AutorizacionMenorPendiente(
            "Una persona menor de edad reserva con la autorizacion de su tutor."
        )
    vigente = requisitos.condiciones_vigentes
    if vigente is None or vigente["version"] != version_condiciones:
        raise TextoDesactualizado(
            f"La version {version_condiciones} de las condiciones no es la vigente.",
            {"vigente": vigente},
        )


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


def cuotas_de(total: Decimal, anticipo: Decimal) -> list[tuple[str, Decimal]]:
    """RN-13: `al_reservar` es el anticipo de la simulacion y `al_terminar` el resto."""
    return [("al_reservar", anticipo), ("al_terminar", total - anticipo)]


def estado_de_cuota(estado_base: str, pagos: Iterable[PagoCuota]) -> str:
    """`pendiente` | `en_validacion` | `pagada` (ADR-010): un pago en validacion pasa a la cuota."""
    if estado_base == "pagada":
        return "pagada"
    return (
        "en_validacion" if any(p.estado == "pendiente_validacion" for p in pagos) else "pendiente"
    )


def cuota_pagable(estado_cuota: str, hito: str, estado_reserva: str) -> bool:
    """CA-02: pendiente, reserva no cancelada y `al_terminar` solo desde que se confirma."""
    if estado_cuota != "pendiente" or estado_reserva == "cancelada":
        return False
    return hito != "al_terminar" or estado_reserva in ("confirmada", "en_curso", "finalizada")
