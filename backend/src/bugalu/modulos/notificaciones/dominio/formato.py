"""Formato comun de los correos: hora de Lima, fechas en espanol y montos `S/ 1.234,50`."""

from datetime import datetime, timedelta, timezone
from decimal import ROUND_HALF_UP, Decimal
from typing import Any

# Lima no tiene horario de verano (UTC-5 todo el anio), asi que no hace falta base de zonas.
LIMA = timezone(timedelta(hours=-5))
_DIAS = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]
_MESES = [
    "enero", "febrero", "marzo", "abril", "mayo", "junio",
    "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre",
]  # fmt: skip


def formatear_soles(monto: Decimal) -> str:
    entero, decimales = f"{monto.quantize(Decimal('0.01'), ROUND_HALF_UP):,.2f}".split(".")
    return f"S/ {entero.replace(',', ' ')},{decimales}"


def _lima(iso: str) -> datetime:
    return datetime.fromisoformat(iso).astimezone(LIMA)


def _fecha(f: datetime) -> str:
    return f"{_DIAS[f.weekday()]} {f.day} de {_MESES[f.month - 1]} de {f.year}"


def _horario(datos: dict[str, Any]) -> str:
    inicio, fin = _lima(datos["inicio"]), _lima(datos["fin"])
    return f"{_fecha(inicio)}, de {inicio:%H:%M} a {fin:%H:%M}"


def _soles(valor: Any) -> str:
    return formatear_soles(Decimal(str(valor)))
