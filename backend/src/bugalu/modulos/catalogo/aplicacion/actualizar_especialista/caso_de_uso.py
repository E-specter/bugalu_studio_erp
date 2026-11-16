from collections.abc import Mapping
from decimal import Decimal
from uuid import UUID

from bugalu.compartido.errores import NoEncontrado
from bugalu.modulos.catalogo.aplicacion.permisos import exigir_administrador
from bugalu.modulos.catalogo.dominio.precio import Especialista
from bugalu.modulos.catalogo.dominio.puertos import RepositorioCatalogo


class ActualizarEspecialista:
    def __init__(self, catalogo: RepositorioCatalogo) -> None:
        self._catalogo = catalogo

    async def ejecutar(
        self, id_especialista: UUID, cambios: Mapping[str, Decimal | bool | str]
    ) -> Especialista:
        await exigir_administrador(self._catalogo)
        if cambios:
            especialista = await self._catalogo.actualizar_especialista(id_especialista, cambios)
        else:
            encontrados = await self._catalogo.obtener_especialistas([id_especialista])
            especialista = encontrados[0] if encontrados else None
        if especialista is None:
            raise NoEncontrado("No existe el especialista.")
        return especialista
