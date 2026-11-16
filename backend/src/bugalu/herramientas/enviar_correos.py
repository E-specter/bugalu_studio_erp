"""Herramienta de mantenimiento: envia una vez los correos pendientes de la bandeja `notificacion`.

Uso: uv run python -m bugalu.herramientas.enviar_correos
Usa URL_BASE_DATOS (rol bugalu_api) y las variables SMTP_*; no forma parte de la API.
"""

import asyncio
import sys

from bugalu.compartido.base_datos import crear_pool
from bugalu.compartido.bucle import crear_bucle
from bugalu.compartido.configuracion import Configuracion
from bugalu.modulos.notificaciones.infraestructura.entrada.ejecucion import enviar_una_vez


async def _enviar() -> int:
    configuracion = Configuracion()
    async with crear_pool(
        configuracion.url_base_datos, configuracion.timeout_pool_segundos
    ) as pool:
        return await enviar_una_vez(pool, configuracion)


def main() -> int:
    with asyncio.Runner(loop_factory=crear_bucle) as ejecutor:
        enviados = ejecutor.run(_enviar())
    print(f"{enviados} correo(s) enviado(s).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
