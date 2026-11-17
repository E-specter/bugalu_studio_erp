"""Ejecucion del envio de la bandeja: una vez (herramienta) o cada cierto tiempo (lifespan)."""

import asyncio
import logging
from collections.abc import Awaitable, Callable

from psycopg_pool import AsyncConnectionPool

from bugalu.compartido.configuracion import Configuracion
from bugalu.modulos.notificaciones.aplicacion.enviar_pendientes.caso_de_uso import enviar_pendientes
from bugalu.modulos.notificaciones.infraestructura.salida.bandeja_postgres import BandejaPostgres
from bugalu.modulos.notificaciones.infraestructura.salida.enviador_smtp import EnviadorSmtp

registro = logging.getLogger(__name__)


async def enviar_una_vez(pool: AsyncConnectionPool, configuracion: Configuracion) -> int:
    enviador = EnviadorSmtp(
        configuracion.smtp_host,
        configuracion.smtp_puerto,
        configuracion.correo_remitente,
        configuracion.smtp_usuario,
        configuracion.smtp_clave.get_secret_value(),
        configuracion.smtp_starttls,
    )
    return await enviar_pendientes(
        BandejaPostgres(pool),
        enviador,
        url_publica=configuracion.url_publica,
        remitente=configuracion.correo_remitente,
    )


async def repetir(accion: Callable[[], Awaitable[object]], intervalo: float) -> None:
    """Llama a `accion` cada `intervalo` segundos; un fallo se registra y la tarea sigue."""
    while True:
        try:
            await accion()
        except Exception as error:  # noqa: BLE001 - nada de aqui puede tumbar la app
            registro.warning("envio de correos fallido: %s", type(error).__name__)
        await asyncio.sleep(intervalo)
