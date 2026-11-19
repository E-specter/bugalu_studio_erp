"""Armado del correo de un aviso: plantilla, evento de calendario y su metodo (ADR-016)."""

# ruff: noqa: E501 - datos de ejemplo y textos literales de la spec

import re
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
ID_RESERVA = "0b6f6f3e-1c2d-4e5f-8a9b-0c1d2e3f4a5b"
BASE = {"id_reserva": ID_RESERVA, "folio": "R-1"}
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
    assert TIPOS_CON_EVENTO == set(DATOS) | {
        "asesoria_confirmada_profesional",
        "asesoria_encuentro_cambiado",
    }  # los de asesoria: test_armado_asesorias


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
    assert (
        f"SEQUENCE:{int((CREADA - datetime(2026, 1, 1, tzinfo=UTC)).total_seconds())}"
        in correo.evento.ics
    )
    assert f"UID:reserva-{ID_RESERVA}@bugalu" in correo.evento.ics
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


def test_la_secuencia_exige_la_fecha_de_creacion() -> None:
    p = Pendiente(uuid4(), "pago_aprobado", "c@x.pe", DATOS["pago_aprobado"], 0)
    with pytest.raises(ValueError, match="creada_en"):
        armar_correo(p, (), RESERVA, URL, "r@x", AHORA)


def test_la_secuencia_cuenta_desde_una_epoca_propia_y_sigue_creciendo() -> None:
    def secuencia(creada: datetime) -> int:
        p = Pendiente(uuid4(), "pago_aprobado", "c@x.pe", DATOS["pago_aprobado"], 0, creada)
        ics = armar_correo(p, (), RESERVA, URL, "r@x", AHORA).evento.ics  # type: ignore[union-attr]
        return int(re.search(r"SEQUENCE:(\d+)", ics).group(1))  # type: ignore[union-attr]

    antes, despues = secuencia(CREADA), secuencia(CREADA.replace(minute=1))
    assert (
        despues == antes + 60 and antes < 2**26
    )  # 2027: ~5e7 s, lejos del tope de 32 bits (2038 en Unix)
    assert secuencia(datetime(2060, 1, 1, tzinfo=UTC)) < 2**31


@pytest.mark.parametrize("campo", ["id_reserva", "folio"])
@pytest.mark.parametrize("malo", ["x\r\nATTENDEE:mailto:a@b.c", "no-es-uuid-ni-folio\n", ""])
def test_id_y_folio_inseguros_no_llegan_al_ics(campo: str, malo: str) -> None:
    datos = {**DATOS["pago_aprobado"], campo: malo}
    with pytest.raises(ValueError, match=campo):
        armar("pago_aprobado", RESERVA, datos)
