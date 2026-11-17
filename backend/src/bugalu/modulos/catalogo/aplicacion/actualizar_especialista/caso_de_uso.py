from collections.abc import Mapping
from decimal import Decimal
from uuid import UUID

from bugalu.compartido.errores import NoEncontrado
from bugalu.modulos.catalogo.aplicacion.permisos import exigir_administrador
from bugalu.modulos.catalogo.dominio import cambios_sensibles as sensibles
from bugalu.modulos.catalogo.dominio.precio import Especialista
from bugalu.modulos.catalogo.dominio.puertos import RepositorioCatalogo


class ActualizarEspecialista:
    def __init__(self, catalogo: RepositorioCatalogo) -> None:
        self._catalogo = catalogo

    async def ejecutar(
        self, id_especialista: UUID, cambios: Mapping[str, Decimal | bool | str]
    ) -> Especialista:
        await exigir_administrador(self._catalogo)
        encontrados = await self._catalogo.obtener_especialistas([id_especialista])
        if not encontrados:
            raise NoEncontrado("No existe el especialista.")
        sensibles.exigir_confirmacion(
            "especialista",
            sensibles.valores_especialista(encontrados[0]),
            {k: sensibles.texto(v) for k, v in cambios.items()},
        )
        # Los sensibles llegan aqui con su mismo valor (si no, fue 428): solo se escribe lo demas.
        campos = {k: v for k, v in cambios.items() if k not in sensibles.SENSIBLES["especialista"]}
        if not campos:
            return encontrados[0]
        especialista = await self._catalogo.actualizar_especialista(id_especialista, campos)
        if especialista is None:
            raise LookupError("El especialista desaparecio durante la transaccion.")
        return especialista
