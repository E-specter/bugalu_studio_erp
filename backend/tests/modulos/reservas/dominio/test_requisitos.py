"""RF-17 (CA-05, CA-07, CA-08): requisitos del perfil para reservar, como regla pura."""

from dataclasses import replace

import pytest

from bugalu.compartido.errores import (
    AutorizacionMenorPendiente,
    PerfilIncompleto,
    ReaceptacionRequerida,
    TextoDesactualizado,
)
from bugalu.modulos.reservas.dominio.modelos import RequisitosReserva
from bugalu.modulos.reservas.dominio.reserva import exigir_requisitos

VIGENTE = {"tipo": "condiciones_contratacion", "version": "1.0.0", "vigente_desde": "2026-01-01"}
LISTO = RequisitosReserva((), (), False, VIGENTE)
TEXTO = {"tipo": "terminos_uso", "version": "2.0.0", "contexto": "registro", "motivo": "x"}


def test_un_perfil_listo_con_la_version_vigente_pasa() -> None:
    exigir_requisitos(LISTO, "1.0.0")


def test_texto_del_registro_pendiente_es_reaceptacion_con_los_textos() -> None:
    with pytest.raises(ReaceptacionRequerida) as error:
        exigir_requisitos(replace(LISTO, pendientes=(TEXTO,)), "1.0.0")
    assert error.value.detalles == {"textos": [TEXTO]}


def test_faltan_datos_es_perfil_incompleto_con_los_campos() -> None:
    with pytest.raises(PerfilIncompleto) as error:
        exigir_requisitos(replace(LISTO, campos_faltantes=("documento", "telefono")), "1.0.0")
    assert error.value.detalles == {"campos": ["documento", "telefono"]}


def test_quien_se_declara_menor_no_reserva_en_la_etapa_a() -> None:
    with pytest.raises(AutorizacionMenorPendiente):
        exigir_requisitos(replace(LISTO, es_menor=True), "1.0.0")


def test_otra_version_es_texto_desactualizado_con_la_vigente() -> None:
    with pytest.raises(TextoDesactualizado) as error:
        exigir_requisitos(LISTO, "0.9.0")
    assert error.value.detalles == {"vigente": VIGENTE}


def test_sin_condiciones_vigentes_no_se_puede_aceptar() -> None:
    with pytest.raises(TextoDesactualizado) as error:
        exigir_requisitos(replace(LISTO, condiciones_vigentes=None), "1.0.0")
    assert error.value.detalles == {"vigente": None}


def test_el_orden_es_reaceptacion_perfil_menor_y_version() -> None:
    todo = RequisitosReserva((TEXTO,), ("nombre",), True, VIGENTE)
    for esperado, quitar in (
        (ReaceptacionRequerida, {}),
        (PerfilIncompleto, {"pendientes": ()}),
        (AutorizacionMenorPendiente, {"pendientes": (), "campos_faltantes": ()}),
        (TextoDesactualizado, {"pendientes": (), "campos_faltantes": (), "es_menor": False}),
    ):
        with pytest.raises(esperado):
            exigir_requisitos(replace(todo, **quitar), "0.9.0")
