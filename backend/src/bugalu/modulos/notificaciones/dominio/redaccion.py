"""Redaccion pura de los correos: texto plano en espanol, hora de Lima, montos `S/ 1.234,50`."""

from collections.abc import Callable
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


def _reserva_creada(datos: dict[str, Any]) -> tuple[str, str]:
    limite = _lima(datos["vence_pago"])
    return (
        f"Reserva {datos['folio']} registrada",
        "Tu reserva en Bugalú Studio quedó registrada.\n\n"
        f"Folio: {datos['folio']}\n"
        f"Servicio: {datos['servicio']}\n"
        f"Fecha y hora: {_horario(datos)} (hora de Lima)\n"
        f"Total: {formatear_soles(Decimal(str(datos['total'])))}\n\n"
        f"Fecha límite de pago: {_fecha(limite)}, {limite:%H:%M} (hora de Lima).\n"
        "Si no registras el pago antes de esa fecha, la reserva caducará y el horario "
        "se liberará.\n",
    )


def _reserva_caducada(datos: dict[str, Any]) -> tuple[str, str]:
    return (
        f"Reserva {datos['folio']} caducada",
        f"Tu reserva {datos['folio']} caducó porque no se registró el pago a tiempo.\n\n"
        f"El horario ({_horario(datos)}, hora de Lima) se liberó. "
        "Puedes hacer una nueva reserva cuando quieras.\n",
    )


_REDACTORES: dict[str, Callable[[dict[str, Any]], tuple[str, str]]] = {
    "reserva_creada": _reserva_creada,
    "reserva_caducada": _reserva_caducada,
}


def redactar(tipo: str, datos: dict[str, Any]) -> tuple[str, str]:
    """Devuelve (asunto, cuerpo) del tipo de notificacion."""
    if tipo not in _REDACTORES:
        raise ValueError(f"tipo de notificacion desconocido: {tipo}")
    return _REDACTORES[tipo](datos)
