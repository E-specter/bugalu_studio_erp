"""Avisos de RF-18 (CA-14): cancelacion con pagos, inasistencia, credito y devoluciones."""

from typing import Any

import pytest

from bugalu.modulos.notificaciones.dominio.redaccion import redactar

RESERVA = {
    "id_reserva": "x",
    "folio": "R-2027-00042",
    "inicio": "2027-03-10T15:00:00+00:00",  # 10:00 en Lima
    "fin": "2027-03-10T17:00:00+00:00",
}


def test_cancelacion_con_pagos_dice_nivel_retenido_credito_y_vencimiento() -> None:
    datos = {
        **RESERVA,
        "nivel": 2,
        "pagado": 100,
        "retenido": 50,
        "credito": 50,
        "credito_vence": "2027-04-10T04:59:59.999999+00:00",
    }
    asunto, cuerpo = redactar("reserva_cancelada_con_pagos", datos)
    assert "R-2027-00042" in asunto
    assert "nivel 2" in cuerpo and "S/ 50,00" in cuerpo
    assert "9 de abril de 2027" in cuerpo  # el final del dia en Lima, no el siguiente en UTC


def test_cancelacion_en_nivel_3_no_habla_de_credito() -> None:
    datos = {
        **RESERVA,
        "nivel": 3,
        "pagado": 100,
        "retenido": 100,
        "credito": 0,
        "credito_vence": None,
    }
    _, cuerpo = redactar("reserva_cancelada_con_pagos", datos)
    assert "S/ 100,00" in cuerpo and "vence" not in cuerpo


def test_inasistencia_informa_lo_retenido() -> None:
    _, cuerpo = redactar("inasistencia_marcada", {**RESERVA, "retenido": 100})
    assert "no asististe" in cuerpo and "S/ 100,00" in cuerpo


def test_credito_por_vencer_dice_saldo_y_fecha() -> None:
    datos = {"saldo": 60, "vence": "2027-04-10T04:59:59+00:00", "folio_origen": "R-2027-00042"}
    asunto, cuerpo = redactar("credito_por_vencer", datos)
    assert "vence" in asunto and "S/ 60,00" in cuerpo and "R-2027-00042" in cuerpo


def test_devolucion_solicitada_avisa_al_administrador() -> None:
    datos = {
        "cliente": "Ana Torres",
        "saldo": 100,
        "motivo": "Cambie de planes",
        "folio_origen": "R-1",
    }
    _, cuerpo = redactar("devolucion_solicitada", datos)
    assert "Ana Torres" in cuerpo and "S/ 100,00" in cuerpo and "Cambie de planes" in cuerpo


@pytest.mark.parametrize(
    ("decision", "monto", "fragmento"),
    [
        ("total", 70, "aprobó la devolución"),
        ("parcial", 30, "S/ 30,00"),
        ("rechazo", None, "Rechazamos"),
    ],
)
def test_devolucion_decidida_segun_la_decision(decision: str, monto: Any, fragmento: str) -> None:
    datos = {
        "decision": decision,
        "monto_aprobado": monto,
        "motivo": "Por politica",
        "folio_origen": "R-1",
    }
    _, cuerpo = redactar("devolucion_decidida", datos)
    assert fragmento in cuerpo


def test_devolucion_realizada_lleva_la_nota() -> None:
    datos = {"monto_aprobado": 30, "nota": "Yape, operación 998877", "folio_origen": "R-1"}
    _, cuerpo = redactar("devolucion_realizada", datos)
    assert "S/ 30,00" in cuerpo and "Yape, operación 998877" in cuerpo
