from collections.abc import Mapping
from typing import Any

from bugalu.modulos.catalogo.dominio import cambios_sensibles as sensibles
from bugalu.modulos.reservas.aplicacion.permisos import exigir_administrador
from bugalu.modulos.reservas.dominio.puertos import RepositorioReservas


class ActualizarParametros:
    def __init__(self, reservas: RepositorioReservas) -> None:
        self._reservas = reservas

    async def ejecutar(self, cambios: Mapping[str, Any]) -> dict[str, Any]:
        await exigir_administrador(self._reservas)
        actuales = await self._reservas.obtener_parametros()
        # RF-20 CA-04: un sensible con otro valor solo cambia por vista previa y confirmacion.
        sensibles.exigir_confirmacion(
            "parametros",
            sensibles.valores_parametros(actuales),
            sensibles.valores_parametros(cambios),
        )
        sensibles.validar_plazos({**actuales, **cambios})
        # Tras la barrera, un sensible que llega es de mismo valor: solo se escribe lo que cambia.
        if distintos := {c: v for c, v in cambios.items() if actuales[c] != v}:
            await self._reservas.guardar_parametros(distintos)
        return await self._reservas.obtener_parametros()
