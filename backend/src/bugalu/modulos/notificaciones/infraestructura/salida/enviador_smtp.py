import asyncio
import smtplib
from email.message import EmailMessage

from bugalu.modulos.notificaciones.dominio.correo import Correo


class EnviadorSmtp:
    """SMTP de la biblioteca estandar; sin STARTTLS ni credenciales (Mailpit local, ADR-009)."""

    def __init__(self, host: str, puerto: int, remitente: str) -> None:
        self._host, self._puerto, self._remitente = host, puerto, remitente

    async def enviar(self, correo: Correo) -> None:
        await asyncio.to_thread(self._enviar, correo)

    def _enviar(self, correo: Correo) -> None:
        mensaje = EmailMessage()
        mensaje["From"] = self._remitente
        mensaje["To"] = correo.destinatario
        mensaje["Subject"] = correo.asunto
        mensaje.set_content(correo.cuerpo)
        with smtplib.SMTP(self._host, self._puerto, timeout=10) as servidor:
            servidor.send_message(mensaje)
