import asyncio
import smtplib
import ssl
from email.message import EmailMessage
from functools import cache
from pathlib import Path
from typing import cast

from bugalu.modulos.notificaciones.dominio.correo import Correo

_LOGO = Path(__file__).with_name("logo-correo.png")


@cache
def _logo() -> bytes:
    return _LOGO.read_bytes()


def construir_mensaje(correo: Correo, remitente: str) -> EmailMessage:
    """Texto plano solo, o ADR-016: texto + HTML con logo por cid (+ .ics si hay evento)."""
    mensaje = EmailMessage()
    mensaje["From"] = remitente
    mensaje["To"] = correo.destinatario
    mensaje["Subject"] = correo.asunto
    mensaje.set_content(correo.cuerpo)
    if not correo.html:
        return mensaje
    mensaje.add_alternative(correo.html, subtype="html")
    html = cast(EmailMessage, mensaje.get_payload()[1])  # type: ignore[index]
    html.add_related(_logo(), "image", "png", cid="<logo-bugalu>", disposition="inline")
    if correo.evento:
        e = correo.evento
        mensaje.add_alternative(e.ics, subtype="calendar", params={"method": e.metodo})
        mensaje.add_attachment(
            e.ics.encode(), maintype="application", subtype="ics", filename=e.nombre_archivo
        )
    return mensaje


class EnviadorSmtp:
    """SMTP de la biblioteca estandar. Sin STARTTLS ni usuario: Mailpit local (ADR-009);
    con ellos: la cuenta de Google del estudio (ADR-011). Los fallos suben como excepcion."""

    def __init__(
        self,
        host: str,
        puerto: int,
        remitente: str,
        usuario: str = "",
        clave: str = "",
        starttls: bool = False,
    ) -> None:
        self._host, self._puerto, self._remitente = host, puerto, remitente
        self._usuario, self._clave, self._starttls = usuario, clave, starttls

    async def enviar(self, correo: Correo) -> None:
        await asyncio.to_thread(self._enviar, correo)

    def _enviar(self, correo: Correo) -> None:
        mensaje = construir_mensaje(correo, self._remitente)
        with smtplib.SMTP(self._host, self._puerto, timeout=10) as servidor:
            if self._starttls:
                servidor.starttls(context=ssl.create_default_context())
            if self._usuario:
                servidor.login(self._usuario, self._clave)
            servidor.send_message(mensaje)
