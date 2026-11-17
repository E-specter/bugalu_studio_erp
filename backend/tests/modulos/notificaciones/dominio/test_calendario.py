"""Evento de calendario (ADR-016): `.ics` RFC 5545 y enlaces de respaldo a Google y Outlook."""

# ruff: noqa: E501 - datos de ejemplo y textos literales de la spec

from datetime import UTC, datetime
from urllib.parse import parse_qs, urlsplit

import pytest

from bugalu.modulos.notificaciones.dominio.calendario import (
    AVISO_ADR_016,
    DatosEvento,
    enlace_google,
    enlace_outlook,
    generar_ics,
    texto_evento,
)

EVENTO = DatosEvento(
    id_reserva="11111111-2222-3333-4444-555555555555",
    folio="R-2027-00007",
    inicio=datetime(2027, 3, 10, 15, 0, tzinfo=UTC),  # 10:00 en Lima
    fin=datetime(2027, 3, 10, 17, 30, tzinfo=UTC),
    servicio="Grabación, mezcla; y más",
    sala="Sala A",
)
URL = "https://erp.bugalu.pe"
AHORA = datetime(2027, 3, 1, 12, 30, 5, tzinfo=UTC)


def ics(metodo: str = "REQUEST", secuencia: int = 1800000000, **cambios: object) -> str:
    evento = DatosEvento(**{**EVENTO.__dict__, **cambios})
    return generar_ics(evento, metodo, secuencia, AHORA, "no-responder@bugalu.pe", "c@x.pe", URL)


def desplegar(texto: str) -> list[str]:
    """Deshace el plegado de RFC 5545 (CRLF + espacio) y devuelve las lineas logicas."""
    assert texto.endswith("\r\n")
    return texto.replace("\r\n ", "").split("\r\n")[:-1]


def test_usa_crlf_y_ninguna_linea_pasa_de_75_octetos() -> None:
    texto = ics(servicio="Á" * 200)
    assert "\n" not in texto.replace("\r\n", "")
    for linea in texto.split("\r\n")[:-1]:
        assert len(linea.encode()) <= 75
    assert any(linea.startswith(" ") for linea in texto.split("\r\n"))  # hubo plegado
    # El plegado no parte un caracter de varios octetos: se vuelve a decodificar sin error.
    assert "Á" * 200 in "".join(desplegar(texto))


def test_estructura_un_solo_vevent_con_zona_de_lima_y_uid_estable() -> None:
    lineas = desplegar(ics())
    assert lineas[0] == "BEGIN:VCALENDAR" and lineas[-1] == "END:VCALENDAR"
    assert lineas.count("BEGIN:VEVENT") == 1 and lineas.count("END:VEVENT") == 1
    assert "VERSION:2.0" in lineas and "METHOD:REQUEST" in lineas
    assert "TZID:America/Lima" in lineas and "TZOFFSETTO:-0500" in lineas
    assert f"UID:reserva-{EVENTO.id_reserva}@bugalu" in lineas
    assert "DTSTART;TZID=America/Lima:20270310T100000" in lineas
    assert "DTEND;TZID=America/Lima:20270310T123000" in lineas
    assert "DTSTAMP:20270301T123005Z" in lineas
    assert "STATUS:CONFIRMED" in lineas and "TRANSP:OPAQUE" in lineas
    assert f"URL:{URL}/app/reservas/detalle?id={EVENTO.id_reserva}" in lineas
    assert "ORGANIZER;CN=Bugalú Studio:mailto:no-responder@bugalu.pe" in lineas
    assert (
        "ATTENDEE;CN=c@x.pe;ROLE=REQ-PARTICIPANT;PARTSTAT=ACCEPTED;RSVP=FALSE:mailto:c@x.pe"
        in lineas
    )


def test_uid_igual_y_sequence_creciente_entre_alta_reprogramacion_y_cancelacion() -> None:
    alta, cambio, baja = ics(secuencia=100), ics(secuencia=200), ics("CANCEL", 300)

    def valor(texto: str, clave: str) -> str:
        return next(x.split(":", 1)[1] for x in desplegar(texto) if x.startswith(clave + ":"))

    assert len({valor(t, "UID") for t in (alta, cambio, baja)}) == 1
    assert [int(valor(t, "SEQUENCE")) for t in (alta, cambio, baja)] == [100, 200, 300]


def test_cancelacion_lleva_method_cancel_y_status_cancelled_con_las_mismas_horas() -> None:
    lineas = desplegar(ics("CANCEL"))
    assert "METHOD:CANCEL" in lineas and "STATUS:CANCELLED" in lineas
    assert "STATUS:CONFIRMED" not in lineas
    assert "DTSTART;TZID=America/Lima:20270310T100000" in lineas
    assert any(x.startswith("SUMMARY:") for x in lineas)


def test_escapa_coma_punto_y_coma_barra_y_saltos_de_linea() -> None:
    lineas = desplegar(ics(servicio="A,B;C\\D\nE"))
    resumen = next(x for x in lineas if x.startswith("SUMMARY:"))
    assert resumen == "SUMMARY:Bugalú Studio · A\\,B\\;C\\\\D\\nE · R-2027-00007"
    descripcion = next(x for x in lineas if x.startswith("DESCRIPTION:"))
    assert "\\n" in descripcion and "," not in descripcion.replace("\\,", "")


def test_ubicacion_y_descripcion_siguen_la_spec() -> None:
    lineas = desplegar(ics())
    assert (
        "LOCATION:Bugalú Studio\\, Sala A\\, Av. Javier Prado Este 5920\\, La Molina\\, Lima\\, Perú"
        in lineas
    )
    descripcion = next(x for x in lineas if x.startswith("DESCRIPTION:"))
    assert descripcion.count("\\n") == 2
    assert "Reserva R-2027-00007 en Bugalú Studio" in descripcion
    assert "WhatsApp +51 925 530 800" in descripcion


def test_un_correo_con_caracteres_de_parametro_no_lleva_cn_pero_sigue_siendo_valido() -> None:
    texto = generar_ics(EVENTO, "REQUEST", 1, AHORA, "no-responder@bugalu.pe", 'a"b;c@x.pe', URL)
    asistente = next(x for x in desplegar(texto) if x.startswith("ATTENDEE"))
    assert asistente.startswith("ATTENDEE;ROLE=REQ-PARTICIPANT")


def test_enlace_de_google_codifica_los_parametros_y_usa_utc() -> None:
    url = enlace_google(EVENTO, URL)
    partes = urlsplit(url)
    assert (partes.scheme, partes.netloc, partes.path) == (
        "https",
        "calendar.google.com",
        "/calendar/render",
    )
    consulta = parse_qs(partes.query)
    assert consulta["action"] == ["TEMPLATE"]
    assert consulta["dates"] == ["20270310T150000Z/20270310T173000Z"]
    assert consulta["ctz"] == ["America/Lima"]
    assert consulta["text"] == ["Bugalú Studio · Grabación, mezcla; y más · R-2027-00007"]
    assert "Sala A" in consulta["location"][0]
    assert "&text=Bugal%C3%BA%20Studio" in url and " " not in url


def test_enlace_de_outlook_usa_iso_con_desfase_de_lima() -> None:
    url = enlace_outlook(EVENTO, URL)
    partes = urlsplit(url)
    assert (partes.netloc, partes.path) == ("outlook.live.com", "/calendar/0/deeplink/compose")
    consulta = parse_qs(partes.query)
    assert consulta["path"] == ["/calendar/action/compose"] and consulta["rru"] == ["addevent"]
    assert consulta["startdt"] == ["2027-03-10T10:00:00-05:00"]
    assert consulta["enddt"] == ["2027-03-10T12:30:00-05:00"]
    assert consulta["subject"][0].endswith("R-2027-00007")
    assert "+" not in url  # los espacios van como %20, no como +


@pytest.mark.parametrize(
    ("metodo", "reprogramacion", "contiene"),
    [
        ("REQUEST", False, "Ábrelo para añadirlo"),
        ("REQUEST", True, "este lo reemplaza"),
        ("CANCEL", False, "Adjuntamos la cancelación"),
    ],
)
def test_texto_del_bloque_por_caso(metodo: str, reprogramacion: bool, contiene: str) -> None:
    texto = texto_evento(metodo, reprogramacion, "R-1")
    assert contiene in texto and "bugalu-R-1.ics" in texto


def test_el_aviso_de_adr_016_es_literal() -> None:
    assert AVISO_ADR_016 == (
        "Este evento es una copia para tu calendario y no se sincroniza con la agenda de Bugalú. "
        "Si tu reserva cambia, te enviaremos una actualización; lo vigente es lo que ves en "
        "Mis reservas."
    )
