from datetime import UTC, datetime, timedelta

import pytest

from bugalu.compartido.errores import AvisoInsuficiente, VersionInvalida
from bugalu.modulos.identidad.dominio.textos_legales import (
    TIPOS_DEL_REGISTRO,
    validar_aceptacion_de_registro,
    validar_publicacion,
)

AHORA = datetime(2026, 12, 1, 12, tzinfo=UTC)
EN_20_DIAS = AHORA + timedelta(days=20)


def test_la_primera_version_rige_al_publicarse_sin_aviso() -> None:
    assert validar_publicacion("1.0.0", "mayor", None, None, AHORA) is None  # al publicarse


def test_la_primera_version_puede_programarse_con_cualquier_fecha() -> None:
    manana = AHORA + timedelta(days=1)
    assert validar_publicacion("1.0.0", "mayor", manana, None, AHORA) == manana


@pytest.mark.parametrize(
    ("version", "tipo_cambio"),
    [("2.0.0", "mayor"), ("1.1.0", "menor"), ("1.0.1", "parche")],
)
def test_una_version_coherente_con_su_tipo_se_acepta(version: str, tipo_cambio: str) -> None:
    efectiva = validar_publicacion(version, tipo_cambio, EN_20_DIAS, "1.0.0", AHORA)
    assert efectiva == (None if tipo_cambio == "parche" else EN_20_DIAS)


@pytest.mark.parametrize(
    ("version", "tipo_cambio", "ultima"),
    [
        ("1.0.0", "mayor", "1.0.0"),  # igual
        ("0.9.0", "mayor", "1.0.0"),  # menor que la ultima
        ("1.1.0", "mayor", "1.0.0"),  # no cambia la mayor
        ("2.0.0", "menor", "1.0.0"),  # cambia la mayor
        ("1.0.1", "menor", "1.0.0"),  # no cambia la menor
        ("1.1.0", "parche", "1.0.0"),  # cambia la menor
        ("1.0.0", "parche", "1.0.1"),  # retrocede
        ("1.0", "mayor", "1.0.0"),  # no es semantica
        ("v2.0.0", "mayor", "1.0.0"),
        ("01.0.0", "mayor", "1.0.0"),  # ceros a la izquierda
        ("2.0.0\n", "mayor", "1.0.0"),  # salto de linea final
    ],
)
def test_una_version_incoherente_es_invalida(version: str, tipo_cambio: str, ultima: str) -> None:
    with pytest.raises(VersionInvalida):
        validar_publicacion(version, tipo_cambio, EN_20_DIAS, ultima, AHORA)


def test_una_version_con_formato_invalido_lo_es_incluso_la_primera() -> None:
    with pytest.raises(VersionInvalida):
        validar_publicacion("uno", "mayor", None, None, AHORA)


def test_mayor_y_menor_exigen_quince_dias_de_aviso() -> None:
    for version, tipo in (("2.0.0", "mayor"), ("1.1.0", "menor")):
        for fecha in (None, AHORA, AHORA + timedelta(days=14, hours=23)):
            with pytest.raises(AvisoInsuficiente):
                validar_publicacion(version, tipo, fecha, "1.0.0", AHORA)


def test_quince_dias_exactos_bastan() -> None:
    fecha = AHORA + timedelta(days=15)
    assert validar_publicacion("2.0.0", "mayor", fecha, "1.0.0", AHORA) == fecha


def test_el_parche_rige_al_publicarse_aunque_traiga_fecha() -> None:
    assert validar_publicacion("1.0.1", "parche", EN_20_DIAS, "1.0.0", AHORA) is None


def test_el_registro_acepta_terminos_politica_y_declaracion() -> None:
    assert TIPOS_DEL_REGISTRO == {"terminos_uso", "politica_privacidad", "declaracion_agrupacion"}
    validar_aceptacion_de_registro([("terminos_uso", "1.0.0"), ("politica_privacidad", "1.0.0")])


@pytest.mark.parametrize(
    "textos",
    [
        [],
        [("condiciones_contratacion", "1.0.0")],
        [("terminos_uso", "1.0.0"), ("terminos_uso", "1.0.0")],
    ],
)
def test_el_registro_rechaza_lo_que_no_le_corresponde(textos: list[tuple[str, str]]) -> None:
    from bugalu.compartido.errores import DatosInvalidos

    with pytest.raises(DatosInvalidos):
        validar_aceptacion_de_registro(textos)
