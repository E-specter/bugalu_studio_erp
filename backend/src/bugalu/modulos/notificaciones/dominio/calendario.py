"""Evento de calendario de los correos (ADR-016): `.ics` RFC 5545 y enlaces a Google y Outlook."""

import re
from dataclasses import dataclass
from datetime import UTC, datetime
from urllib.parse import quote, urlencode
from uuid import UUID

from bugalu.modulos.notificaciones.dominio.formato import LIMA

DIRECCION = "Av. Javier Prado Este 5920, La Molina, Lima, Perú"
AVISO_ADR_016 = (
    "Este evento es una copia para tu calendario y no se sincroniza con la agenda de Bugalú. "
    "Si tu reserva cambia, te enviaremos una actualización; lo vigente es lo que ves en "
    "Mis reservas."
)


_FOLIO = re.compile(r"[A-Za-z0-9._-]{1,40}")


@dataclass(frozen=True)
class DatosEvento:
    id_reserva: str
    folio: str
    inicio: datetime
    fin: datetime
    servicio: str
    sala: str
    ubicacion_texto: str | None = None  # asesoria: lugar o enlace en vez de la sala

    @property
    def es_asesoria(self) -> bool:
        return self.folio.startswith("A-")

    def __post_init__(self) -> None:
        # UID y URL llevan estos dos valores sin escapar: solo UUID y folios de caracteres seguros.
        try:
            if str(UUID(self.id_reserva)) != self.id_reserva:
                raise ValueError
        except ValueError:
            raise ValueError("id_reserva invalido para el evento") from None
        if not _FOLIO.fullmatch(self.folio):
            raise ValueError("folio invalido para el evento")


def titulo(e: DatosEvento) -> str:
    return f"Bugalú Studio · {e.servicio} · {e.folio}"


def ubicacion(e: DatosEvento) -> str:
    if e.ubicacion_texto:
        return e.ubicacion_texto
    return f"Bugalú Studio, {e.sala}, {DIRECCION}"


def url_detalle(e: DatosEvento, url: str) -> str:
    modulo = "asesorias" if e.es_asesoria else "reservas"
    return f"{url}/app/{modulo}/detalle?id={e.id_reserva}"


def descripcion(e: DatosEvento, url: str) -> str:
    cosa, lista = ("Asesoría", "Mis asesorías") if e.es_asesoria else ("Reserva", "Mis reservas")
    return (
        f"{cosa} {e.folio} en Bugalú Studio: {e.servicio}, {e.sala}.\n"
        "Esta es una copia para tu calendario y no se sincroniza con la agenda de Bugalú. "
        f"Lo vigente es lo que ves en {lista}: {url_detalle(e, url)}\n"
        "¿Dudas? WhatsApp +51 925 530 800."
    )


def _escapar(texto: str) -> str:
    return (
        texto.replace("\\", "\\\\")
        .replace(";", "\\;")
        .replace(",", "\\,")
        .replace("\r\n", "\\n")
        .replace("\n", "\\n")
        .replace("\r", "\\n")
    )


def _plegar(linea: str) -> str:
    """Pliega a 75 octetos UTF-8 (la continuacion lleva un espacio) sin partir un caracter."""
    salida: list[str] = []
    actual, octetos, tope = "", 0, 75
    for caracter in linea:
        largo = len(caracter.encode())
        if octetos + largo > tope:
            salida.append(actual)
            actual, octetos, tope = "", 1, 75  # el espacio inicial cuenta como un octeto
        actual += caracter
        octetos += largo
    salida.append(actual)
    return "\r\n ".join(salida)


def _lima(momento: datetime) -> str:
    return f"{momento.astimezone(LIMA):%Y%m%dT%H%M%S}"


def _utc(momento: datetime) -> str:
    return f"{momento.astimezone(UTC):%Y%m%dT%H%M%SZ}"


def _parametro_seguro(valor: str) -> bool:
    return not any(c in valor for c in ';:,"')


def generar_ics(
    e: DatosEvento,
    metodo: str,
    secuencia: int,
    ahora: datetime,
    remitente: str,
    destinatario: str,
    url: str,
) -> str:
    """Un VEVENT; `metodo` es REQUEST o CANCEL (con STATUS:CANCELLED)."""
    cn = f";CN={destinatario}" if _parametro_seguro(destinatario) else ""
    lineas = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//Bugalú Studio//Plataforma//ES",
        "CALSCALE:GREGORIAN",
        f"METHOD:{metodo}",
        "BEGIN:VTIMEZONE",
        "TZID:America/Lima",
        "BEGIN:STANDARD",
        "DTSTART:19700101T000000",
        "TZOFFSETFROM:-0500",
        "TZOFFSETTO:-0500",
        "TZNAME:-05",
        "END:STANDARD",
        "END:VTIMEZONE",
        "BEGIN:VEVENT",
        f"UID:reserva-{e.id_reserva}@bugalu",
        f"SEQUENCE:{secuencia}",
        f"DTSTAMP:{_utc(ahora)}",
        f"DTSTART;TZID=America/Lima:{_lima(e.inicio)}",
        f"DTEND;TZID=America/Lima:{_lima(e.fin)}",
        f"SUMMARY:{_escapar(titulo(e))}",
        f"LOCATION:{_escapar(ubicacion(e))}",
        f"DESCRIPTION:{_escapar(descripcion(e, url))}",
        f"URL:{url_detalle(e, url)}",
        f"STATUS:{'CANCELLED' if metodo == 'CANCEL' else 'CONFIRMED'}",
        "TRANSP:OPAQUE",
        f"ORGANIZER;CN=Bugalú Studio:mailto:{remitente}",
        f"ATTENDEE{cn};ROLE=REQ-PARTICIPANT;PARTSTAT=ACCEPTED;RSVP=FALSE:mailto:{destinatario}",
        "END:VEVENT",
        "END:VCALENDAR",
    ]
    return "".join(_plegar(linea) + "\r\n" for linea in lineas)


def enlace_google(e: DatosEvento, url: str) -> str:
    consulta = urlencode(
        {
            "action": "TEMPLATE",
            "text": titulo(e),
            "dates": f"{_utc(e.inicio)}/{_utc(e.fin)}",
            "details": descripcion(e, url),
            "location": ubicacion(e),
            "ctz": "America/Lima",
        },
        quote_via=quote,
    )
    return f"https://calendar.google.com/calendar/render?{consulta}"


def enlace_outlook(e: DatosEvento, url: str) -> str:
    consulta = urlencode(
        {
            "path": "/calendar/action/compose",
            "rru": "addevent",
            "subject": titulo(e),
            "startdt": e.inicio.astimezone(LIMA).isoformat(),
            "enddt": e.fin.astimezone(LIMA).isoformat(),
            "body": descripcion(e, url),
            "location": ubicacion(e),
        },
        quote_via=quote,
    )
    return f"https://outlook.live.com/calendar/0/deeplink/compose?{consulta}"


def texto_evento(metodo: str, reprogramacion: bool, folio: str, encuentro: bool = False) -> str:
    archivo = f"bugalu-{folio}.ics"
    if metodo == "CANCEL":
        return (
            f"Adjuntamos la cancelación del evento (archivo {archivo}). Si añadiste tu reserva "
            "con el archivo, al abrirlo se quita de tu calendario. Si usaste los enlaces de "
            "Google o Outlook, bórrala a mano."
        )
    if encuentro:
        return (
            f"Adjuntamos el evento actualizado con el nuevo lugar o enlace (archivo {archivo}). "
            "Si ya habías añadido el archivo anterior, este lo reemplaza."
        )
    if reprogramacion:
        return (
            f"Adjuntamos el evento con el nuevo horario (archivo {archivo}). Si ya habías "
            "añadido el archivo anterior, este lo reemplaza. Si usaste los enlaces de Google o "
            "Outlook, borra el evento anterior: esos enlaces crean uno nuevo y no reemplazan el "
            "que ya tenías."
        )
    return (
        f"Adjuntamos el evento de tu reserva (archivo {archivo}). Ábrelo para añadirlo a Google "
        "Calendar, Outlook, Apple Calendar u otro calendario."
    )
