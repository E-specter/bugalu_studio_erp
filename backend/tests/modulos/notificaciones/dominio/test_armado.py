"""Armado del correo de un aviso: plantilla, evento de calendario y su metodo (ADR-016)."""

# ruff: noqa: E501 - datos de ejemplo y textos literales de la spec

from datetime import UTC, datetime
from uuid import uuid4

import pytest

from bugalu.modulos.notificaciones.dominio.armado import TIPOS_CON_EVENTO, armar_correo
from bugalu.modulos.notificaciones.dominio.puertos import DatosReserva, Pendiente

URL = "https://erp.bugalu.pe"
AHORA = datetime(2027, 3, 1, 12, 0, tzinfo=UTC)
CREADA = datetime(2027, 3, 1, 11, 0, tzinfo=UTC)
RESERVA = DatosReserva(
    inicio=datetime(2027, 3, 10, 15, 0, tzinfo=UTC),
    fin=datetime(2027, 3, 10, 17, 0, tzinfo=UTC),
    servicio="Grabación",
    sala="Sala A",
    tiene_evento=True,
)
BASE = {"id_reserva": "r-1", "folio": "R-1"}
CON_HORARIO = {**BASE, "inicio": "2027-03-11T15:00:00+00:00", "fin": "2027-03-11T17:00:00+00:00"}
DATOS = {
    "pago_aprobado": {**BASE, "hito": "al_reservar", "monto": "50", "reserva_confirmada": True},
    "reserva_reprogramada": {
        **CON_HORARIO, "anterior_inicio": "2027-03-10T15:00:00+00:00",
        "sin_costo": True, "nivel": 1, "penalizacion": 0, "saldo": 0, "credito": 0,
    },
    "reserva_cancelada_estudio": {**CON_HORARIO, "nota": None},
    "reserva_cancelada_con_pagos": {
        **CON_HORARIO, "nivel": 2, "pagado": "50", "retenido": "10", "credito": "0",
        "credito_vence": None,
    },
}  # fmt: skip


def armar(tipo: str, reserva: DatosReserva | None = RESERVA, datos: dict | None = None):  # type: ignore[no-untyped-def]
    p = Pendiente(uuid4(), tipo, "c@x.pe", datos or DATOS[tipo], 0, CREADA)
    return armar_correo(p, (), reserva, URL, "no-responder@bugalu.pe", AHORA)


def test_los_tipos_con_evento_son_los_de_la_spec() -> None:
    assert TIPOS_CON_EVENTO == set(DATOS)


@pytest.mark.parametrize(
    ("tipo", "metodo"),
    [
        ("pago_aprobado", "REQUEST"),
        ("reserva_reprogramada", "REQUEST"),
        ("reserva_cancelada_estudio", "CANCEL"),
        ("reserva_cancelada_con_pagos", "CANCEL"),
    ],
)
def test_cada_tipo_lleva_el_metodo_que_dice_la_spec(tipo: str, metodo: str) -> None:
    correo = armar(tipo)
    assert correo.evento is not None and correo.evento.metodo == metodo
    assert correo.evento.nombre_archivo == "bugalu-R-1.ics"
    assert f"METHOD:{metodo}" in correo.evento.ics
    assert f"SEQUENCE:{int(CREADA.timestamp())}" in correo.evento.ics
    assert "UID:reserva-r-1@bugalu" in correo.evento.ics
    assert "EVENTO DE CALENDARIO" in correo.cuerpo and "Evento de calendario" in correo.html
    assert ("Añadir a Google Calendar" in correo.html) == (metodo == "REQUEST")
    assert ("no se sincroniza" in correo.html) == (metodo == "REQUEST")


def test_el_horario_del_aviso_manda_sobre_el_de_la_reserva_y_pago_aprobado_usa_el_de_la_reserva() -> (
    None
):
    assert "DTSTART;TZID=America/Lima:20270311T100000" in armar("reserva_reprogramada").evento.ics  # type: ignore[union-attr]
    assert "DTSTART;TZID=America/Lima:20270310T100000" in armar("pago_aprobado").evento.ics  # type: ignore[union-attr]
    assert "Grabación" in armar("pago_aprobado").evento.ics  # type: ignore[union-attr]


def test_reprogramada_con_evento_usa_el_texto_que_reemplaza_al_anterior() -> None:
    assert "este lo reemplaza" in armar("reserva_reprogramada").cuerpo


@pytest.mark.parametrize("tipo", ["reserva_reprogramada", "reserva_cancelada_estudio"])
def test_sin_evento_previo_no_hay_ics_ni_bloque(tipo: str) -> None:
    sin = DatosReserva(RESERVA.inicio, RESERVA.fin, "Grabación", "Sala A", tiene_evento=False)
    correo = armar(tipo, sin)
    assert correo.evento is None and "alendario" not in correo.html


def test_pago_aprobado_sin_confirmar_no_lleva_evento() -> None:
    datos = {**DATOS["pago_aprobado"], "reserva_confirmada": False}
    assert armar("pago_aprobado", RESERVA, datos).evento is None


def test_pago_aprobado_confirmado_sin_datos_de_la_reserva_falla_en_vez_de_enviar_sin_evento() -> (
    None
):
    with pytest.raises(ValueError, match="reserva"):
        armar("pago_aprobado", None)


@pytest.mark.parametrize("tipo", ["reserva_reprogramada", "reserva_cancelada_estudio"])
def test_sin_datos_de_la_reserva_el_aviso_sale_sin_evento(tipo: str) -> None:
    assert armar(tipo, None).evento is None


def test_tipos_sin_evento_salen_con_plantilla_y_sin_ics() -> None:
    p = Pendiente(uuid4(), "reserva_caducada", "c@x.pe", CON_HORARIO, 0, CREADA)
    correo = armar_correo(p, (), None, URL, "r@x", AHORA)
    assert correo.evento is None and correo.html.startswith("<!doctype html>")
    assert correo.cuerpo.startswith("BUGALÚ STUDIO\n// RESERVA")


def test_el_nombre_del_archivo_no_admite_caracteres_raros() -> None:
    datos = {**DATOS["pago_aprobado"], "folio": 'R/../"1"'}
    assert armar("pago_aprobado", RESERVA, datos).evento.nombre_archivo == "bugalu-R_.._1_.ics"  # type: ignore[union-attr]


def test_la_secuencia_exige_la_fecha_de_creacion() -> None:
    p = Pendiente(uuid4(), "pago_aprobado", "c@x.pe", DATOS["pago_aprobado"], 0)
    with pytest.raises(ValueError, match="creada_en"):
        armar_correo(p, (), RESERVA, URL, "r@x", AHORA)
