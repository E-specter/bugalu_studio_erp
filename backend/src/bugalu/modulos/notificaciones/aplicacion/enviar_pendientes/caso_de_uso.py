import logging

from bugalu.modulos.notificaciones.dominio.correo import Correo
from bugalu.modulos.notificaciones.dominio.puertos import (
    MAX_INTENTOS,
    Bandeja,
    EnviadorCorreo,
)
from bugalu.modulos.notificaciones.dominio.redaccion import redactar

registro = logging.getLogger(__name__)


async def enviar_pendientes(bandeja: Bandeja, enviador: EnviadorCorreo, limite: int = 20) -> int:
    """Envia un lote de la bandeja; devuelve cuantos salieron. Un fallo solo marca esa fila."""
    enviados = 0
    async with bandeja.tomar(limite, MAX_INTENTOS) as lote:
        for p in lote.pendientes:
            try:
                asunto, cuerpo = redactar(p.tipo, p.datos, lote.instrucciones)
                await enviador.enviar(Correo(p.destinatario, asunto, cuerpo))
            except Exception as error:  # noqa: BLE001 - un fallo de correo nunca tumba el lote
                # Solo el tipo: el mensaje del servidor SMTP podria traer datos sensibles.
                nombre = type(error).__name__
                registro.warning("notificacion %s no enviada: %s", p.id, nombre)
                await lote.marcar_fallo(p.id, nombre)
            else:
                await lote.marcar_enviada(p.id)
                enviados += 1
    return enviados
