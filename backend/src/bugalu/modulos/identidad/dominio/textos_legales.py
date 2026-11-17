"""Textos legales versionados y aceptaciones (RF-17, CA-01 a CA-04). Solo biblioteca estandar."""

import re
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta
from uuid import UUID

from bugalu.compartido.errores import AvisoInsuficiente, DatosInvalidos, VersionInvalida

TIPOS_PUBLICABLES = (
    "terminos_uso",
    "politica_privacidad",
    "condiciones_contratacion",
    "declaracion_agrupacion",
)
TIPOS_CAMBIO = ("mayor", "menor", "parche")
CONTEXTOS = (
    "registro",
    "reserva",
    "asesoria",
    "pago",
    "menor",
    "promociones",
    "usos_promocionales",
)
# La politica no se "acepta": queda registrada la version mostrada (CA-04).
TIPOS_DEL_REGISTRO = frozenset({"terminos_uso", "politica_privacidad", "declaracion_agrupacion"})
AVISO_MINIMO = timedelta(days=15)
_SEMVER = re.compile(r"^(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)$")


@dataclass(frozen=True)
class TextoLegal:
    tipo: str
    version: str
    tipo_cambio: str
    contenido: str
    resumenes: dict[str, str]
    resumen_cambios: str | None
    vigente_desde: datetime
    publicado_en: datetime
    programada: bool


@dataclass(frozen=True)
class Aceptacion:
    id: UUID
    tipo: str
    version: str
    contexto: str
    id_operacion: UUID | None
    aceptada_en: datetime
    retirada_en: datetime | None
    aceptante: dict[str, str] | None


def _partes(version: str) -> tuple[int, int, int]:
    encontrada = _SEMVER.fullmatch(version)
    if encontrada is None:
        raise VersionInvalida("La version debe ser semantica: mayor.menor.parche.")
    mayor, menor, parche = (int(p) for p in encontrada.groups())
    return mayor, menor, parche


def validar_publicacion(
    version: str,
    tipo_cambio: str,
    vigente_desde: datetime | None,
    ultima: str | None,
    ahora: datetime,
) -> datetime | None:
    """CA-02: el `vigente_desde` efectivo (None = al publicarse, reloj de la base) o el error."""
    nueva = _partes(version)
    if ultima is None:
        return vigente_desde  # la primera version rige ya, sin aviso, salvo que se programe
    anterior = _partes(ultima)
    coherente = {
        "mayor": nueva[0] > anterior[0],
        "menor": nueva[0] == anterior[0] and nueva[1] > anterior[1],
        "parche": nueva[:2] == anterior[:2] and nueva[2] > anterior[2],
    }[tipo_cambio]
    if not coherente:
        raise VersionInvalida(
            f"La version {version} no es mayor que la ultima ({ultima}) como cambio {tipo_cambio}."
        )
    if tipo_cambio == "parche":
        return None
    if vigente_desde is None or vigente_desde < ahora + AVISO_MINIMO:
        raise AvisoInsuficiente("Una version mayor o menor exige 15 dias de aviso.")
    return vigente_desde


def validar_aceptacion_de_registro(textos: Sequence[tuple[str, str]]) -> None:
    tipos = [tipo for tipo, _ in textos]
    if not tipos or len(set(tipos)) != len(tipos) or not set(tipos) <= TIPOS_DEL_REGISTRO:
        raise DatosInvalidos(
            "El registro acepta terminos de uso, politica y declaracion, una vez cada uno.",
            {"campo": "textos"},
        )
