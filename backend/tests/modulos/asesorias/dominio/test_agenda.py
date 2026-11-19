"""RF-15 B1: reglas puras de agendar y del encuentro (lugar o enlace)."""

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from bugalu.compartido.errores import DatosInvalidos, EnlaceInvalido, FueraDeHorario
from bugalu.modulos.asesorias.dominio import agenda
from bugalu.modulos.asesorias.dominio.modelos import Horario

P = uuid4()
D = datetime(2027, 3, 1, 15, 0, tzinfo=UTC)  # 10:00 en Lima
BLOQUE = Horario(uuid4(), P, D, D + timedelta(hours=2))


def test_el_inicio_va_en_media_hora_de_lima_y_con_zona() -> None:
    agenda.exigir_inicio(D)
    for malo in (D + timedelta(minutes=15), D.replace(tzinfo=None), D + timedelta(seconds=1)):
        with pytest.raises(DatosInvalidos):
            agenda.exigir_inicio(malo)


def test_la_asesoria_completa_debe_caber_en_un_bloque() -> None:
    assert agenda.bloque_que_contiene(D, D + timedelta(hours=1), [BLOQUE]) == BLOQUE
    assert agenda.bloque_que_contiene(D + timedelta(hours=1), D + timedelta(hours=2), [BLOQUE])
    for inicio in (D + timedelta(minutes=90), D - timedelta(minutes=30)):
        with pytest.raises(FueraDeHorario):
            agenda.bloque_que_contiene(inicio, inicio + timedelta(hours=1), [BLOQUE])


@pytest.mark.parametrize(
    "malo",
    [
        "http://meet.google.com/abc",
        "https://meet.google.com.evil.pe/a",
        "https://meet.google.com/",
        "https://x.pe/https://meet.google.com/a",
        "https://meet.google.com/a b",
        "https://u@meet.google.com/a",
    ],
)
def test_enlace_que_no_es_de_meet_se_rechaza(malo: str) -> None:
    with pytest.raises(EnlaceInvalido):
        agenda.validar_enlace(malo)


def test_enlace_de_meet_y_vacios() -> None:
    assert (
        agenda.validar_enlace("https://meet.google.com/abc-defg-hij")
        == "https://meet.google.com/abc-defg-hij"
    )
    assert agenda.validar_enlace("  ") is None and agenda.validar_enlace(None) is None


def test_lugar_de_1_a_300_o_vacio() -> None:
    assert agenda.validar_lugar(" Av. Lima 1 ") == "Av. Lima 1"
    assert agenda.validar_lugar("") is None
    with pytest.raises(DatosInvalidos):
        agenda.validar_lugar("x" * 301)


def test_cambiar_de_modalidad_borra_el_dato_de_la_otra() -> None:
    e = agenda.combinar_encuentro(("presencial", "Av. Lima 1", None), {"modalidad": "virtual"})
    assert e == ("virtual", None, None)
    e = agenda.combinar_encuentro(
        ("virtual", None, "https://meet.google.com/a"),
        {"modalidad": "presencial", "lugar": "Mi estudio"},
    )
    assert e == ("presencial", "Mi estudio", None)
    e = agenda.combinar_encuentro(("presencial", "Av. Lima 1", None), {"lugar": None})
    assert e == ("presencial", None, None)


def test_el_dato_de_la_otra_modalidad_se_rechaza() -> None:
    with pytest.raises(DatosInvalidos):
        agenda.combinar_encuentro(("virtual", None, None), {"lugar": "Av. Lima 1"})


def test_encuentro_pendiente_y_por_cerrar() -> None:
    assert agenda.encuentro_pendiente("presencial", None, None)
    assert not agenda.encuentro_pendiente("virtual", None, "https://meet.google.com/a")
    ahora = D + timedelta(hours=3)
    assert agenda.por_cerrar("confirmada", D + timedelta(hours=1), ahora)
    assert not agenda.por_cerrar("confirmada", D + timedelta(hours=4), ahora)
    assert not agenda.por_cerrar("pre_reservada", D, ahora)
