from datetime import date, datetime, timedelta, timezone

import pytest

from bugalu.modulos.reservas.dominio.disponibilidad import (
    Limites,
    Tramo,
    calcular_limites,
    lunes_de_semana_iso,
    minutos_libres_por_dia,
    sugerir_semana,
)

LIMA = timezone(timedelta(hours=-5))
ABIERTO = Limites(datetime(2000, 1, 1, tzinfo=LIMA), datetime(2100, 1, 1, tzinfo=LIMA))


def t(dia: int, hora: int, minuto: int = 0) -> datetime:
    return datetime(2026, 12, dia, hora, minuto, tzinfo=LIMA)


def tramo(dia: int, h1: int, h2: int, m1: int = 0, m2: int = 0) -> Tramo:
    return Tramo(t(dia, h1, m1), t(dia, h2, m2))


def libres(franjas, cierres=(), ocupados=(), limites=ABIERTO, dias=1):  # type: ignore[no-untyped-def]
    return minutos_libres_por_dia(t(7, 0), t(7 + dias, 0), franjas, cierres, ocupados, limites)


def test_una_franja_descuenta_el_margen_de_30_min_del_ultimo_tramo() -> None:
    # 08:00-12:00 admite inicios 08:00..11:00 (7 tramos de 30 min): el de 11:30 no tiene margen.
    assert libres([tramo(7, 8, 12)]) == {date(2026, 12, 7): 210}


def test_una_franja_de_30_min_no_ofrece_nada_y_una_de_60_ofrece_un_tramo() -> None:
    assert libres([tramo(7, 8, 8, 0, 30)]) == {date(2026, 12, 7): 0}
    assert libres([tramo(7, 8, 9)]) == {date(2026, 12, 7): 30}


def test_un_cierre_parcial_quita_los_tramos_que_toca_con_su_margen() -> None:
    # cierre 10:00-11:00: 09:30 ya no sirve (su margen llega a 10:30); quedan 4 inicios.
    assert libres([tramo(7, 8, 12)], cierres=[tramo(7, 10, 11)]) == {date(2026, 12, 7): 120}


def test_un_cierre_de_todo_el_dia_deja_cero() -> None:
    assert libres([tramo(7, 8, 20)], cierres=[tramo(7, 0, 23)]) == {date(2026, 12, 7): 0}


def test_un_ocupado_con_su_buffer_quita_sus_tramos() -> None:
    # ocupado (reserva 09:00-10:00 + buffer) = 09:00-10:30; inicios libres: 08:00 (margen a 09:00)
    # y 10:30, 11:00 (margen hasta 12:00).
    assert libres([tramo(7, 8, 12)], ocupados=[tramo(7, 9, 10, 0, 30)]) == {date(2026, 12, 7): 90}


def test_los_limites_de_anticipacion_recortan_por_inicio() -> None:
    limites = Limites(t(7, 10), t(7, 11))  # inicio permitido: 10:00 a 11:00 (inclusive)
    assert libres([tramo(7, 8, 14)], limites=limites) == {date(2026, 12, 7): 90}


def test_el_dia_es_el_de_lima_aunque_la_franja_cruce_medianoche() -> None:
    # franja 23:00 -> 02:00 del dia siguiente: inicios 23:00, 23:30 (dia 7) y 00:00..01:00 (dia 8).
    franja = Tramo(t(7, 23), t(8, 2))
    r = minutos_libres_por_dia(t(7, 0), t(9, 0), [franja], [], [], ABIERTO)
    assert r == {date(2026, 12, 7): 60, date(2026, 12, 8): 90}


def test_un_dia_sin_franja_aparece_con_cero_minutos() -> None:
    r = libres([tramo(8, 8, 12)], dias=3)
    assert r == {date(2026, 12, 7): 0, date(2026, 12, 8): 210, date(2026, 12, 9): 0}


def test_los_limites_se_calculan_con_minimo_en_horas_y_maximo_en_semanas() -> None:
    ahora = t(7, 12)
    assert calcular_limites(ahora, 2, 8) == Limites(t(7, 14), ahora + timedelta(weeks=8))


def test_la_semana_iso_empieza_en_lunes_y_una_invalida_falla() -> None:
    assert lunes_de_semana_iso("2026-W47") == date(2026, 11, 16)
    with pytest.raises(ValueError):
        lunes_de_semana_iso("2027-W53")  # 2027 solo tiene 52 semanas ISO


def test_la_sugerencia_desplaza_la_ultima_semana_publicada_anterior() -> None:
    previas = [tramo(7, 8, 12), tramo(9, 8, 12), Tramo(t(1, 8), t(1, 12))]  # semana del 7 (lun)
    sugeridas = sugerir_semana(previas, date(2026, 12, 14))
    assert sugeridas == [tramo(14, 8, 12), tramo(16, 8, 12)]


def test_la_sugerencia_sin_semana_previa_es_vacia() -> None:
    assert sugerir_semana([], date(2026, 12, 14)) == []
