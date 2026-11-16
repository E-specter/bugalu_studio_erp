from collections.abc import Sequence

from bugalu.compartido.errores import SinPermiso
from bugalu.modulos.pagos.dominio.instrucciones import (
    Instruccion,
    validar_contacto,
    validar_instrucciones,
)
from bugalu.modulos.pagos.dominio.puertos import RepositorioDatosPago


async def _exigir_administrador(datos: RepositorioDatosPago) -> None:
    if not await datos.es_administrador():
        raise SinPermiso("Solo el administrador edita estos datos.")


class ObtenerInstrucciones:
    def __init__(self, datos: RepositorioDatosPago) -> None:
        self._datos = datos

    async def ejecutar(self) -> list[Instruccion]:
        return await self._datos.listar_instrucciones()


class ReemplazarInstrucciones:
    def __init__(self, datos: RepositorioDatosPago) -> None:
        self._datos = datos

    async def ejecutar(self, entradas: Sequence[Instruccion]) -> list[Instruccion]:
        await _exigir_administrador(self._datos)
        await self._datos.guardar_instrucciones(validar_instrucciones(entradas))
        return await self._datos.listar_instrucciones()


class ObtenerContacto:
    def __init__(self, datos: RepositorioDatosPago) -> None:
        self._datos = datos

    async def ejecutar(self) -> str:
        return await self._datos.obtener_contacto()


class ActualizarContacto:
    def __init__(self, datos: RepositorioDatosPago) -> None:
        self._datos = datos

    async def ejecutar(self, texto: str) -> str:
        await _exigir_administrador(self._datos)
        await self._datos.guardar_contacto(validar_contacto(texto))
        return await self._datos.obtener_contacto()
