from datetime import date, datetime, timedelta, timezone

import pytest

from bugalu.compartido.errores import DatosInvalidos
from bugalu.modulos.asesorias.dominio.disponibilidad import (
    minutos_libres_por_dia,
    validar_horarios_nuevos,
)
from bugalu.modulos.reservas.dominio.disponibilidad import Limites, Tramo

LIMA = timezone(timedelta(hours=-5))
ABIERTO = Limites(datetime(2000, 1, 1, tzinfo=LIMA), datetime(2100, 1, 1, tzinfo=LIMA))
AHORA = datetime(2026, 12, 1, 9, tzinfo=LIMA)


def t(dia: int, hora: int, minuto: int = 0) -> datetime:
    return datetime(2026, 12, dia, hora, minuto, tzinfo=LIMA)


def libres(horarios, ocupados=(), limites=ABIERTO, dias=1):  # type: ignore[no-untyped-def]
    return minutos_libres_por_dia(t(7, 0), t(7 + dias, 0), horarios, ocupados, limites)


def test_cada_media_hora_de_un_bloque_cuenta_sin_margen() -> None:
    # A diferencia de la sala, no hay margen entre asesorias: 08:00-10:00 son 120 minutos.
    assert libres([Tramo(t(7, 8), t(7, 10))]) == {date(2026, 12, 7): 120}


def test_un_ocupado_descuenta_solo_lo_que_toca() -> None:
    assert libres([Tramo(t(7, 8), t(7, 10))], [Tramo(t(7, 8, 30), t(7, 9))]) == {
        date(2026, 12, 7): 90
    }


def test_la_anticipacion_recorta_por_los_dos_lados() -> None:
    limites = Limites(t(7, 9), t(7, 9, 30))
    assert libres([Tramo(t(7, 8), t(7, 12))], limites=limites) == {date(2026, 12, 7): 60}


def test_un_dia_sin_bloques_vale_cero_y_el_dia_es_el_de_lima() -> None:
    assert libres([], dias=2) == {date(2026, 12, 7): 0, date(2026, 12, 8): 0}
    # 23:30 de Lima ya es el dia siguiente en UTC: cuenta para el dia 7 de Lima.
    assert libres([Tramo(t(7, 23), t(8, 0))]) == {date(2026, 12, 7): 60}


def test_horarios_futuros_en_multiplos_de_30() -> None:
    validar_horarios_nuevos([Tramo(t(7, 8), t(7, 9, 30))], AHORA)  # no lanza


@pytest.mark.parametrize(
    "tramo",
    [
        Tramo(t(1, 8), t(1, 9)),  # ya empezo (09:00 es ahora)
        Tramo(t(7, 8, 10), t(7, 9)),  # no es multiplo de 30
        Tramo(t(7, 8), t(7, 8)),  # sin duracion
        Tramo(t(7, 9), t(7, 8)),  # fin antes del inicio
    ],
)
def test_un_horario_pasado_o_malformado_es_invalido(tramo: Tramo) -> None:
    with pytest.raises(DatosInvalidos):
        validar_horarios_nuevos([tramo], AHORA)
