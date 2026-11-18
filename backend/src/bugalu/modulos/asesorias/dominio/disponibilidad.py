"""Disponibilidad de un profesional (CA-05): sin margen entre asesorias; dias en hora de Lima."""

from collections.abc import Iterable, Sequence
from datetime import date, datetime

from bugalu.compartido.errores import DatosInvalidos
from bugalu.modulos.reservas.dominio.disponibilidad import (
    PASO,
    Limites,
    Tramo,
    dia_de_lima,
    dias_del_rango,
)


def minutos_libres_por_dia(
    desde: datetime,
    hasta: datetime,
    horarios: Iterable[Tramo],
    ocupados: Sequence[Tramo],
    limites: Limites,
) -> dict[date, int]:
    """Minutos de bloques publicados que empiezan en [desde, hasta), dentro de la anticipacion
    y sin tocar una asesoria; cada media hora se atribuye al dia de Lima en que empieza."""
    libres = dict.fromkeys(dias_del_rango(desde, hasta), 0)
    for horario in horarios:
        inicio = horario.inicio
        while inicio + PASO <= horario.fin:
            if (
                desde <= inicio < hasta
                and limites.desde <= inicio <= limites.hasta
                and not any(Tramo(inicio, inicio + PASO).solapa(o) for o in ocupados)
            ):
                libres[dia_de_lima(inicio)] += 30
            inicio += PASO
    return libres


def validar_horarios_nuevos(tramos: Sequence[Tramo], ahora: datetime) -> None:
    """Futuros, en multiplos de 30 min y de al menos 30 (el solape lo garantiza la base)."""
    for tramo in tramos:
        en_media_hora = all(
            not v.microsecond and v.timestamp() % 1800 == 0 for v in (tramo.inicio, tramo.fin)
        )
        if tramo.fin <= tramo.inicio or not en_media_hora:
            raise DatosInvalidos(
                "Los bloques van en multiplos de 30 minutos y duran al menos 30.",
                {"campo": "horarios"},
            )
        if tramo.inicio <= ahora:
            raise DatosInvalidos("Los bloques deben ser futuros.", {"campo": "horarios"})
