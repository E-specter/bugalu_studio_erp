"""RF-20 CA-04: que cuenta como cambio de un campo sensible y como se compara (texto canonico)."""

from datetime import time
from decimal import Decimal
from uuid import uuid4

import pytest

from bugalu.compartido.errores import ConfirmacionRequerida, PlazosIncoherentes
from bugalu.modulos.catalogo.dominio import cambios_sensibles as cs
from bugalu.modulos.catalogo.dominio.precio import (
    ConfiguracionImpuestos,
    Especialista,
    Recargos,
    Servicio,
    Unidad,
)

D = Decimal

SERVICIO = Servicio(uuid4(), "Voces", "grabacion", True, D("80"), D("0"), (), True)
RECARGOS = Recargos(D(25), time(22), time(6), D(20), D(30))


def test_texto_canonico() -> None:
    assert cs.texto(D("80")) == "80.00"
    assert cs.texto(D("7.5")) == "7.50"
    assert cs.texto(True) == "true"
    assert cs.texto(Unidad.HORA) == "hora"
    assert cs.texto(time(6)) == "06:00"
    assert cs.texto(48) == "48"


def test_valores_de_recargos_usan_nombres_anidados() -> None:
    assert cs.valores_recargos(RECARGOS) == {
        "noche.porcentaje": "25.00",
        "noche.desde": "22:00",
        "noche.hasta": "06:00",
        "fin_de_semana.porcentaje": "20.00",
        "feriado.porcentaje": "30.00",
    }


def test_un_sensible_con_otro_valor_exige_confirmacion() -> None:
    actual = cs.valores_servicio(SERVICIO)
    with pytest.raises(ConfirmacionRequerida) as error:
        cs.exigir_confirmacion("servicio", actual, {"tarifa_hora": "90.00", "activo": "false"})
    assert error.value.detalles == {"campos": ["tarifa_hora"]}


@pytest.mark.parametrize(
    "propuesto",
    [{"tarifa_hora": "80.00"}, {"activo": "false"}, {}],
    ids=["igual", "no_sensible", "vacio"],
)
def test_mismo_valor_o_campo_no_sensible_sigue_en_un_paso(propuesto: dict[str, str]) -> None:
    cs.exigir_confirmacion("servicio", cs.valores_servicio(SERVICIO), propuesto)


def test_diferencias_solo_lista_lo_que_cambia() -> None:
    assert cs.diferencias({"a": "1", "b": "2"}, {"a": "1", "b": "3"}) == {"b": ("2", "3")}


def test_impuestos_y_especialista() -> None:
    assert cs.valores_impuestos(ConfiguracionImpuestos(D("18"), True)) == {
        "porcentaje_igv": "18.00",
        "precios_incluyen_igv": "true",
    }
    e = Especialista(uuid4(), "Ing", D(0), D("25"), Unidad.LAPSO_30, True)
    assert cs.valores_especialista(e)["unidad"] == "lapso_30"


def test_tipar_devuelve_el_valor_de_dominio() -> None:
    assert cs.tipar("noche.desde", "22:30") == time(22, 30)
    assert cs.tipar("precios_incluyen_igv", "false") is False
    assert cs.tipar("unidad", "hora") is Unidad.HORA
    assert cs.tipar("horas_nivel_1", "48") == 48
    assert cs.tipar("tarifa_hora", "9.50") == D("9.50")


def test_el_nivel_1_debe_superar_al_nivel_2() -> None:
    cs.validar_plazos({"horas_nivel_1": 48, "horas_nivel_2": 24})
    for malo in (
        {"horas_nivel_1": 24, "horas_nivel_2": 24},
        {"horas_nivel_1": 10, "horas_nivel_2": 24},
    ):
        with pytest.raises(PlazosIncoherentes):
            cs.validar_plazos(malo)


# --- RF-20 CA-11: parametros de danos ---

DANOS = {"tarifa_hora_gestion": D("0.00"), "tope_horas_sesiones_perdidas": 8}


def test_los_parametros_de_danos_son_sensibles_y_se_comparan_en_texto() -> None:
    assert {"tarifa_hora_gestion", "tope_horas_sesiones_perdidas"} <= set(
        cs.SENSIBLES["parametros"]
    )
    actual = cs.valores_parametros(DANOS)
    assert actual == {"tarifa_hora_gestion": "0.00", "tope_horas_sesiones_perdidas": "8"}
    with pytest.raises(ConfirmacionRequerida) as error:
        cs.exigir_confirmacion("parametros", actual, {"tarifa_hora_gestion": "25.00"})
    assert error.value.detalles == {"campos": ["tarifa_hora_gestion"]}
    with pytest.raises(ConfirmacionRequerida):
        cs.exigir_confirmacion("parametros", actual, {"tope_horas_sesiones_perdidas": "9"})
    cs.exigir_confirmacion("parametros", actual, {"tarifa_hora_gestion": "0.00"})  # mismo valor


def test_los_danos_no_afectan_a_reservas_vigentes_pero_el_resto_si() -> None:
    assert not cs.afecta_reservas_vigentes("parametros", ["tarifa_hora_gestion"])
    assert not cs.afecta_reservas_vigentes(
        "parametros", ["tarifa_hora_gestion", "tope_horas_sesiones_perdidas"]
    )
    assert cs.afecta_reservas_vigentes(
        "parametros", ["tope_horas_sesiones_perdidas", "horas_nivel_1"]
    )
    assert cs.afecta_reservas_vigentes("servicio", ["tarifa_hora"])


def test_la_tarifa_de_gestion_se_tipa_decimal_y_el_tope_entero() -> None:
    tarifa = cs.tipar("tarifa_hora_gestion", "25.50")
    tope = cs.tipar("tope_horas_sesiones_perdidas", "12")
    assert tarifa == D("25.50") and isinstance(tarifa, D)
    assert tope == 12 and type(tope) is int
