import logging
from datetime import UTC, datetime

from bugalu.modulos.notificaciones.dominio.armado import armar_correo
from bugalu.modulos.notificaciones.dominio.puertos import (
    MAX_INTENTOS,
    Bandeja,
    EnviadorCorreo,
)

registro = logging.getLogger(__name__)


async def enviar_pendientes(
    bandeja: Bandeja,
    enviador: EnviadorCorreo,
    limite: int = 20,
    url_publica: str = "http://127.0.0.1:4321",
    remitente: str = "no-responder@bugalu.pe",
) -> int:
    """Envia un lote de la bandeja; devuelve cuantos salieron. Un fallo solo marca esa fila."""
    enviados = 0
    async with bandeja.tomar(limite, MAX_INTENTOS) as lote:
        for p in lote.pendientes:
            try:
                correo = armar_correo(
                    p,
                    lote.instrucciones,
                    lote.reservas.get(p.id),
                    url_publica,
                    remitente,
                    datetime.now(UTC),
                )
                await enviador.enviar(correo)
            except Exception as error:  # noqa: BLE001 - un fallo de correo nunca tumba el lote
                # Solo el tipo: el mensaje del servidor SMTP podria traer datos sensibles.
                nombre = type(error).__name__
                registro.warning("notificacion %s no enviada: %s", p.id, nombre)
                await lote.marcar_fallo(p.id, nombre)
            else:
                await lote.marcar_enviada(p.id)
                enviados += 1
    return enviados
