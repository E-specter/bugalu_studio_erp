from datetime import date
from uuid import uuid4

import pytest

from bugalu.compartido.errores import ItseVencido, NoEncontrado, SinPermiso
from bugalu.modulos.reservas.aplicacion.actualizar_sala.caso_de_uso import ActualizarSala
from bugalu.modulos.reservas.dominio.modelos import Itse
from tests.modulos.reservas.aplicacion.falsos import SALA, ReservasFalso

HOY = date(2026, 11, 18)


async def test_el_administrador_guarda_aforo_y_certificado_y_recibe_la_sala() -> None:
    falso = ReservasFalso()
    sala = await ActualizarSala(falso).ejecutar(SALA.id, 12, "ITSE-001", date(2027, 5, 1), HOY)
    assert sala.aforo == 12 and sala.itse == Itse("ITSE-001", date(2027, 5, 1))
    assert falso.sala.aforo == 12


async def test_quien_no_es_administrador_recibe_403_y_la_sala_queda_intacta() -> None:
    falso = ReservasFalso(administrador=False)
    with pytest.raises(SinPermiso):
        await ActualizarSala(falso).ejecutar(SALA.id, 12, "ITSE-001", date(2027, 5, 1), HOY)
    assert falso.sala.aforo is None


async def test_un_itse_vencido_se_rechaza_sin_guardar() -> None:
    falso = ReservasFalso()
    with pytest.raises(ItseVencido):
        await ActualizarSala(falso).ejecutar(SALA.id, 12, "ITSE-001", date(2026, 11, 17), HOY)
    assert falso.sala.aforo is None


async def test_una_sala_inexistente_es_404() -> None:
    with pytest.raises(NoEncontrado):
        await ActualizarSala(ReservasFalso()).ejecutar(uuid4(), 12, "X", date(2027, 5, 1), HOY)
