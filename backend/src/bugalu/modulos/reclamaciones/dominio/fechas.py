"""Fecha original de una hoja transcrita del libro fisico."""

from datetime import datetime, timedelta

from bugalu.compartido.errores import FechaOriginalInvalida

DIAS_MAXIMOS_ATRAS = 90


def validar_fecha_original(fecha: datetime, ahora: datetime) -> None:
    """Ni futura ni de hace mas de 90 dias (la transcripcion se hace al poco de recibir la hoja)."""
    if fecha > ahora or fecha < ahora - timedelta(days=DIAS_MAXIMOS_ATRAS):
        raise FechaOriginalInvalida(
            "La fecha original no puede ser futura ni de hace mas de 90 dias.",
            {"campo": "fecha_original"},
        )
