import smtplib
import ssl
from typing import Any

import pytest

from bugalu.modulos.notificaciones.dominio.correo import Correo
from bugalu.modulos.notificaciones.infraestructura.salida import enviador_smtp
from bugalu.modulos.notificaciones.infraestructura.salida.enviador_smtp import EnviadorSmtp

CORREO = Correo("cliente@ejemplo.pe", "Asunto", "Cuerpo")


class SmtpFalso:
    llamadas: list[tuple[str, Any]] = []
    fallar_login = False

    def __init__(self, host: str, puerto: int, timeout: float) -> None:
        self.llamadas.append(("conectar", (host, puerto)))

    def __enter__(self) -> SmtpFalso:
        return self

    def __exit__(self, *args: object) -> None:
        return None

    def starttls(self, *, context: ssl.SSLContext) -> None:
        self.llamadas.append(("starttls", context))

    def login(self, usuario: str, clave: str) -> None:
        self.llamadas.append(("login", (usuario, clave)))
        if self.fallar_login:
            raise smtplib.SMTPAuthenticationError(535, b"mala clave secreto-123")

    def send_message(self, mensaje: object) -> None:
        self.llamadas.append(("enviar", mensaje))


@pytest.fixture
def smtp(monkeypatch: pytest.MonkeyPatch) -> type[SmtpFalso]:
    SmtpFalso.llamadas = []
    SmtpFalso.fallar_login = False
    monkeypatch.setattr(enviador_smtp.smtplib, "SMTP", SmtpFalso)
    return SmtpFalso


async def test_con_starttls_verifica_certificado_y_se_autentica(smtp: type[SmtpFalso]) -> None:
    enviador = EnviadorSmtp("smtp.x", 587, "r@x", "u@x", "secreto-123", starttls=True)
    await enviador.enviar(CORREO)
    pasos = [p for p, _ in smtp.llamadas]
    assert pasos == ["conectar", "starttls", "login", "enviar"]
    contexto = dict(smtp.llamadas)["starttls"]
    assert contexto.verify_mode == ssl.CERT_REQUIRED and contexto.check_hostname
    assert dict(smtp.llamadas)["login"] == ("u@x", "secreto-123")


async def test_sin_starttls_ni_usuario_se_comporta_como_mailpit(smtp: type[SmtpFalso]) -> None:
    await EnviadorSmtp("127.0.0.1", 45625, "r@x").enviar(CORREO)
    assert [p for p, _ in smtp.llamadas] == ["conectar", "enviar"]


async def test_error_de_autenticacion_sale_como_excepcion_sin_la_clave(
    smtp: type[SmtpFalso],
) -> None:
    from bugalu.modulos.notificaciones.aplicacion.enviar_pendientes.caso_de_uso import (
        enviar_pendientes,
    )
    from tests.modulos.notificaciones.aplicacion.test_enviar_pendientes import (
        BandejaFalsa,
        pendiente,
    )

    smtp.fallar_login = True
    enviador = EnviadorSmtp("smtp.x", 587, "r@x", "u@x", "secreto-123", starttls=True)
    bandeja = BandejaFalsa([pendiente()])
    assert await enviar_pendientes(bandeja, enviador) == 0
    fallos = list(bandeja.lote.fallos.values())
    assert fallos == ["SMTPAuthenticationError"]
