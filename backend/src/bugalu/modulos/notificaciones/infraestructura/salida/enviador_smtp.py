import asyncio
import smtplib
import ssl
from email.message import EmailMessage

from bugalu.modulos.notificaciones.dominio.correo import Correo


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
        mensaje = EmailMessage()
        mensaje["From"] = self._remitente
        mensaje["To"] = correo.destinatario
        mensaje["Subject"] = correo.asunto
        mensaje.set_content(correo.cuerpo)
        with smtplib.SMTP(self._host, self._puerto, timeout=10) as servidor:
            if self._starttls:
                servidor.starttls(context=ssl.create_default_context())
            if self._usuario:
                servidor.login(self._usuario, self._clave)
            servidor.send_message(mensaje)
