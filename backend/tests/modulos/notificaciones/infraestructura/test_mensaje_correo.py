"""Mensaje MIME de cada aviso (ADR-016): partes, logo por cid y .ics segun la tabla de avisos.md."""

from datetime import UTC, datetime
from email.message import EmailMessage, Message
from email.policy import SMTP
from typing import Any
from uuid import uuid4

import pytest

from bugalu.modulos.notificaciones.dominio.armado import TIPOS_CON_EVENTO, armar_correo
from bugalu.modulos.notificaciones.dominio.correo import Correo
from bugalu.modulos.notificaciones.dominio.plantilla import AVISOS
from bugalu.modulos.notificaciones.dominio.puertos import DatosReserva, Pendiente
from bugalu.modulos.notificaciones.infraestructura.salida.enviador_smtp import construir_mensaje
from tests.modulos.notificaciones.datos_avisos import DATOS_AVISOS

URL = "https://erp.bugalu.pe"
CREADA = datetime(2027, 3, 1, 11, 0, tzinfo=UTC)
RESERVA = DatosReserva(
    datetime(2027, 3, 10, 15, 0, tzinfo=UTC), datetime(2027, 3, 10, 17, 0, tzinfo=UTC),
    "Grabación", "Sala A", True,
)  # fmt: skip
METODO = {
    "pago_aprobado": "REQUEST",
    "reserva_reprogramada": "REQUEST",
    "reserva_cancelada_estudio": "CANCEL",
    "reserva_cancelada_con_pagos": "CANCEL",
    "asesoria_confirmada_profesional": "REQUEST",
    "asesoria_encuentro_cambiado": "REQUEST",
    "asesoria_cancelada_profesional": "CANCEL",
    "asesoria_reprogramada_profesional": "REQUEST",
}


def mensaje(tipo: str) -> tuple[EmailMessage, Correo]:
    p = Pendiente(uuid4(), tipo, "c@x.pe", DATOS_AVISOS[tipo], 0, CREADA)
    correo = armar_correo(
        p, [("yape", "Yape al 999")], RESERVA, URL, "no-responder@bugalu.pe", CREADA
    )
    return construir_mensaje(correo, "no-responder@bugalu.pe"), correo


def tipos_mime(parte: Message) -> Any:
    """Arbol de tipos de contenido: (tipo, [hijos]) o solo el tipo en las hojas."""
    if parte.is_multipart():
        return (parte.get_content_type(), [tipos_mime(h) for h in parte.get_payload()])  # type: ignore[union-attr]
    return parte.get_content_type()


def test_todos_los_tipos_de_aviso_estan_cubiertos() -> None:
    assert set(DATOS_AVISOS) == set(AVISOS)


@pytest.mark.parametrize("tipo", sorted(set(DATOS_AVISOS) - TIPOS_CON_EVENTO))
def test_aviso_sin_evento_es_alternativa_de_texto_y_html_con_logo_y_sin_ics(tipo: str) -> None:
    msg, _ = mensaje(tipo)
    assert tipos_mime(msg) == (
        "multipart/alternative",
        ["text/plain", ("multipart/related", ["text/html", "image/png"])],
    )
    assert not any(p.get_content_type() == "text/calendar" for p in msg.walk())
    assert not any(p.get_filename() for p in msg.walk() if p.get_content_type() != "image/png")


@pytest.mark.parametrize("tipo", sorted(TIPOS_CON_EVENTO))
def test_aviso_con_evento_lleva_el_ics_en_la_alternativa_y_como_adjunto(tipo: str) -> None:
    msg, correo = mensaje(tipo)
    assert tipos_mime(msg) == (
        "multipart/mixed",
        [
            (
                "multipart/alternative",
                [
                    "text/plain",
                    ("multipart/related", ["text/html", "image/png"]),
                    "text/calendar",
                ],
            ),
            "application/ics",
        ],
    )
    calendario = next(p for p in msg.walk() if p.get_content_type() == "text/calendar")
    assert calendario.get_param("method") == METODO[tipo]
    adjunto = list(msg.iter_attachments())[0]
    assert adjunto.get_filename() == f"bugalu-{DATOS_AVISOS[tipo]['folio']}.ics"
    assert adjunto.get_content_disposition() == "attachment"
    for texto in (
        calendario.get_payload(decode=True).decode(),  # type: ignore[union-attr]
        adjunto.get_payload(decode=True).decode(),  # type: ignore[union-attr]
    ):
        assert texto.replace("\r\n", "\n") == correo.evento.ics.replace("\r\n", "\n")  # type: ignore[union-attr]
        assert f"METHOD:{METODO[tipo]}" in texto
    # En el cable (SMTP) las lineas del .ics terminan en CRLF.
    assert b"BEGIN:VCALENDAR\r\nVERSION:2.0\r\n" in msg.as_bytes(policy=SMTP)


@pytest.mark.parametrize("tipo", sorted(DATOS_AVISOS))
def test_logo_por_cid_y_texto_equivalente_en_todos_los_avisos(tipo: str) -> None:
    msg, correo = mensaje(tipo)
    logo = next(p for p in msg.walk() if p.get_content_type() == "image/png")
    assert logo["Content-ID"] == "<logo-bugalu>" and logo.get_content_disposition() == "inline"
    assert logo.get_payload(decode=True).startswith(b"\x89PNG")  # type: ignore[union-attr]
    assert "cid:logo-bugalu" in correo.html
    plano = msg.get_body(("plain",))
    html = msg.get_body(("html",))
    assert plano is not None and html is not None
    assert plano.get_content() == correo.cuerpo and html.get_content() == correo.html
    assert msg["Subject"] == correo.asunto and msg["To"] == "c@x.pe"
    msg.as_bytes()  # serializa sin error


def test_sin_html_sale_solo_texto_como_antes() -> None:
    msg = construir_mensaje(Correo("c@x.pe", "Asunto", "Cuerpo"), "r@x.pe")
    assert tipos_mime(msg) == "text/plain" and msg["From"] == "r@x.pe"


@pytest.mark.parametrize("tipo", sorted(TIPOS_CON_EVENTO))
def test_la_parte_calendario_viaja_en_quoted_printable_o_base64(tipo: str) -> None:
    m, _ = mensaje(tipo)
    partes = [p for p in m.walk() if p.get_content_type() == "text/calendar"]
    assert partes and all(
        p["Content-Transfer-Encoding"] in ("quoted-printable", "base64") for p in partes
    )
    assert partes[0].get_content().replace("\r\n", "\n").startswith("BEGIN:VCALENDAR")
