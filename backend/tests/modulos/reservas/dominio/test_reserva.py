from datetime import datetime, timedelta, timezone
from decimal import Decimal
from uuid import uuid4

import pytest

from bugalu.compartido.errores import (
    AnticipacionExcesiva,
    AnticipacionInsuficiente,
    DuracionInvalida,
    FueraDeFranja,
)
from bugalu.compartido.plazos import calcular_vence_pago
from bugalu.modulos.reservas.dominio.disponibilidad import Limites, Tramo
from bugalu.modulos.reservas.dominio.modelos import PagoCuota
from bugalu.modulos.reservas.dominio.reserva import (
    cuota_pagable,
    cuotas_de,
    estado_de_cuota,
    exigir_anticipacion,
    exigir_duracion,
    franja_que_contiene,
)

LIMA = timezone(timedelta(hours=-5))


def t(dia: int, hora: int, minuto: int = 0) -> datetime:
    return datetime(2027, 3, dia, hora, minuto, tzinfo=LIMA)


@pytest.mark.parametrize(
    ("inicio", "fin"),
    [
        (t(1, 10), t(1, 10)),  # duracion cero
        (t(1, 10), t(1, 9)),  # fin antes del inicio
        (t(1, 10, 15), t(1, 11, 15)),  # inicio fuera de los 30 min
        (t(1, 10), t(1, 11, 10)),  # duracion fuera de los 30 min
        (t(1, 10), t(1, 18, 30)),  # mas de 8 h
        (datetime(2027, 3, 1, 10), datetime(2027, 3, 1, 11)),  # sin zona horaria
    ],
)
def test_duracion_invalida(inicio: datetime, fin: datetime) -> None:
    with pytest.raises(DuracionInvalida) as error:
        exigir_duracion(inicio, fin)
    assert error.value.codigo == "duracion_invalida"
    assert error.value.detalles == {"campo": "fin"}


@pytest.mark.parametrize("fin", [t(1, 10, 30), t(1, 18)])
def test_duracion_valida_en_los_extremos(fin: datetime) -> None:
    exigir_duracion(t(1, 10), fin)


def test_anticipacion_dentro_de_la_ventana() -> None:
    limites = Limites(t(1, 10), t(30, 10))
    exigir_anticipacion(t(1, 10), limites)
    exigir_anticipacion(t(30, 10), limites)


def test_anticipacion_insuficiente_y_excesiva() -> None:
    limites = Limites(t(1, 10), t(30, 10))
    with pytest.raises(AnticipacionInsuficiente) as poca:
        exigir_anticipacion(t(1, 9, 30), limites)
    with pytest.raises(AnticipacionExcesiva) as mucha:
        exigir_anticipacion(t(30, 10, 30), limites)
    assert (poca.value.codigo, mucha.value.codigo) == (
        "anticipacion_insuficiente",
        "anticipacion_excesiva",
    )
    assert poca.value.detalles == {"campo": "inicio"}


def test_la_franja_debe_contener_el_tramo_con_su_buffer() -> None:
    franja = Tramo(t(1, 8), t(1, 12))
    assert franja_que_contiene(t(1, 10), t(1, 12), [franja]) == franja  # fin con buffer a las 12:00
    with pytest.raises(FueraDeFranja):
        franja_que_contiene(t(1, 10), t(1, 12, 30), [franja])  # el buffer se sale
    with pytest.raises(FueraDeFranja):
        franja_que_contiene(t(1, 7, 30), t(1, 9), [franja])
    with pytest.raises(FueraDeFranja) as sin_franjas:
        franja_que_contiene(t(1, 10), t(1, 11), [])
    assert sin_franjas.value.detalles == {"campo": "inicio"}


def test_vence_el_plazo_3_dias_antes_si_falta_mas() -> None:
    assert calcular_vence_pago(t(1, 10), t(20, 15), 3, 1) == t(17, 15)


def test_vence_1_hora_despues_si_faltan_menos_de_3_dias() -> None:
    assert calcular_vence_pago(t(1, 10), t(3, 15), 3, 1) == t(1, 11)


def test_a_exactamente_3_dias_el_cliente_tiene_la_hora_completa() -> None:
    assert calcular_vence_pago(t(1, 10), t(4, 10), 3, 1) == t(1, 11)


def test_a_3_dias_y_5_minutos_el_cliente_tiene_la_hora_completa_y_no_5_minutos() -> None:
    assert calcular_vence_pago(t(1, 10), t(4, 10, 5), 3, 1) == t(1, 11)


def test_pasada_la_hora_extra_manda_el_plazo_de_3_dias() -> None:
    assert calcular_vence_pago(t(1, 10), t(4, 11, 30), 3, 1) == t(1, 11, 30)


def test_nunca_vence_despues_del_inicio() -> None:
    assert calcular_vence_pago(t(1, 10), t(1, 10, 30), 3, 1) == t(1, 10, 30)


def test_los_plazos_son_parametros() -> None:
    assert calcular_vence_pago(t(1, 10), t(20, 15), 5, 2) == t(15, 15)
    assert calcular_vence_pago(t(1, 10), t(5, 15), 5, 2) == t(1, 12)


def test_las_cuotas_suman_el_total_con_el_anticipo_primero() -> None:
    assert cuotas_de(Decimal("100.01"), Decimal("50.01")) == [
        ("al_reservar", Decimal("50.01")),
        ("al_terminar", Decimal("50.00")),
    ]
    assert sum(m for _, m in cuotas_de(Decimal("33.33"), Decimal("16.67"))) == Decimal("33.33")


def _pago(estado: str) -> PagoCuota:
    return PagoCuota(uuid4(), estado, "yape", Decimal("25"), "AB-1234", None, t(1, 9))


@pytest.mark.parametrize(
    ("base", "pagos", "esperado"),
    [
        ("pendiente", [], "pendiente"),
        ("pendiente", ["rechazado"], "pendiente"),
        ("pendiente", ["rechazado", "pendiente_validacion"], "en_validacion"),
        ("pagada", ["aprobado"], "pagada"),
    ],
)
def test_estado_de_la_cuota(base: str, pagos: list[str], esperado: str) -> None:
    assert estado_de_cuota(base, [_pago(p) for p in pagos]) == esperado


@pytest.mark.parametrize(
    ("estado", "hito", "reserva", "esperado"),
    [
        ("pendiente", "al_reservar", "pre_reservada", True),
        ("pendiente", "al_reservar", "cancelada", False),
        ("pendiente", "al_terminar", "pre_reservada", False),
        ("pendiente", "al_terminar", "confirmada", True),
        ("pendiente", "al_terminar", "finalizada", True),
        ("en_validacion", "al_reservar", "confirmada", False),
        ("pagada", "al_terminar", "confirmada", False),
    ],
)
def test_cuota_pagable(estado: str, hito: str, reserva: str, esperado: bool) -> None:
    assert cuota_pagable(estado, hito, reserva) is esperado
