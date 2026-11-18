from datetime import date

import pytest

from bugalu.compartido.errores import ItseVencido
from bugalu.modulos.reservas.dominio.sala import exigir_itse_vigente

HOY = date(2026, 11, 18)


def test_un_vencimiento_de_hoy_o_posterior_es_vigente() -> None:
    exigir_itse_vigente(HOY, HOY)
    exigir_itse_vigente(date(2027, 1, 1), HOY)


def test_un_vencimiento_anterior_a_hoy_es_itse_vencido_con_su_campo() -> None:
    with pytest.raises(ItseVencido) as error:
        exigir_itse_vigente(date(2026, 11, 17), HOY)
    assert error.value.codigo == "itse_vencido" and error.value.estado_http == 422
    assert error.value.detalles == {"campo": "itse_vence"}
