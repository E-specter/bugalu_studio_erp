"""Agendar una asesoria y su encuentro (CA-06, CA-09): reglas puras."""

import re
from collections.abc import Mapping, Sequence
from datetime import datetime, timedelta
from typing import Any

from bugalu.compartido.errores import DatosInvalidos, EnlaceInvalido, FueraDeHorario
from bugalu.modulos.asesorias.dominio.modelos import Horario
from bugalu.modulos.reservas.dominio.disponibilidad import PASO

# El mismo patron que el `check` de la tabla `asesoria`.
_ENLACE = re.compile(r"https://meet\.google\.com/[A-Za-z0-9/_?=&.%-]{1,200}")
MODALIDADES = ("presencial", "virtual")


def fin_de(inicio: datetime, minutos: int) -> datetime:
    return inicio + timedelta(minutes=minutos)


def exigir_inicio(inicio: datetime) -> None:
    """Con zona y en media hora exacta (los bloques son de a 30 min)."""
    if inicio.tzinfo is None or inicio.microsecond or inicio.timestamp() % PASO.total_seconds():
        raise DatosInvalidos("El inicio va en media hora exacta y con zona.", {"campo": "inicio"})


def bloque_que_contiene(inicio: datetime, fin: datetime, bloques: Sequence[Horario]) -> Horario:
    for b in bloques:
        if b.inicio <= inicio and fin <= b.fin:
            return b
    raise FueraDeHorario(
        "La asesoria completa no cabe en un horario publicado.", {"campo": "inicio"}
    )


def validar_enlace(enlace: str | None) -> str | None:
    if enlace is None or not enlace.strip():
        return None
    enlace = enlace.strip()
    if not _ENLACE.fullmatch(enlace):
        raise EnlaceInvalido("El enlace es de Google Meet (https://meet.google.com/...).")
    return enlace


def validar_lugar(lugar: str | None) -> str | None:
    if lugar is None or not lugar.strip():
        return None
    lugar = lugar.strip()
    if len(lugar) > 300:
        raise DatosInvalidos("El lugar tiene de 1 a 300 caracteres.", {"campo": "lugar"})
    return lugar


def combinar_encuentro(
    actual: tuple[str, str | None, str | None], cambios: Mapping[str, Any]
) -> tuple[str, str | None, str | None]:
    """(modalidad, lugar, enlace) resultante. Cambiar de modalidad borra el dato de la otra;
    el dato que no corresponde a la modalidad resultante se rechaza."""
    modalidad = cambios.get("modalidad", actual[0])
    lugar, enlace = (None, None) if modalidad != actual[0] else (actual[1], actual[2])
    if "lugar" in cambios:
        lugar = validar_lugar(cambios["lugar"])
    if "enlace" in cambios:
        enlace = validar_enlace(cambios["enlace"])
    if modalidad == "virtual" and lugar:
        raise DatosInvalidos("Una asesoria virtual no lleva lugar.", {"campo": "lugar"})
    if modalidad == "presencial" and enlace:
        raise DatosInvalidos("Una asesoria presencial no lleva enlace.", {"campo": "enlace"})
    return modalidad, lugar, enlace


def encuentro_pendiente(modalidad: str, lugar: str | None, enlace: str | None) -> bool:
    return not (enlace if modalidad == "virtual" else lugar)


def por_cerrar(estado: str, fin: datetime, ahora: datetime) -> bool:
    """Confirmada cuyo fin ya paso: nadie la cerro (decision 6)."""
    return estado == "confirmada" and fin <= ahora
