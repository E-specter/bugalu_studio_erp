from datetime import datetime, timedelta


def calcular_vence_pago(ahora: datetime, inicio: datetime, dias: int, horas: int) -> datetime:
    """RN-18: lo mas tarde entre inicio - `dias` y ahora + `horas`; nunca despues del inicio."""
    return min(inicio, max(inicio - timedelta(days=dias), ahora + timedelta(hours=horas)))
