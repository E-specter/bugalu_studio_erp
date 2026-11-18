from datetime import date

from bugalu.compartido.errores import ItseVencido


def exigir_itse_vigente(vence: date, hoy: date) -> None:
    """El certificado vale todo el dia de `vence`; `hoy` es la fecha en Lima."""
    if vence < hoy:
        raise ItseVencido("El certificado ITSE ya venció.", {"campo": "itse_vence"})
