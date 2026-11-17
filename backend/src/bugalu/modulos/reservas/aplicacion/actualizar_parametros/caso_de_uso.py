from collections.abc import Mapping

from bugalu.modulos.catalogo.dominio import cambios_sensibles as sensibles
from bugalu.modulos.reservas.aplicacion.permisos import exigir_administrador
from bugalu.modulos.reservas.dominio.puertos import RepositorioReservas


class ActualizarParametros:
    def __init__(self, reservas: RepositorioReservas) -> None:
        self._reservas = reservas

    async def ejecutar(self, cambios: Mapping[str, int]) -> dict[str, int]:
        await exigir_administrador(self._reservas)
        actuales = await self._reservas.obtener_parametros()
        # RF-20 CA-04: un sensible con otro valor solo cambia por vista previa y confirmacion.
        sensibles.exigir_confirmacion(
            "parametros",
            sensibles.valores_parametros(actuales),
            sensibles.valores_parametros(cambios),
        )
        sensibles.validar_plazos({**actuales, **cambios})
        if cambios:
            await self._reservas.guardar_parametros(cambios)
        return await self._reservas.obtener_parametros()
