from collections.abc import Mapping
from decimal import Decimal
from typing import Any
from uuid import UUID

from bugalu.compartido.errores import DatosInvalidos, NoEncontrado
from bugalu.modulos.catalogo.aplicacion.permisos import exigir_administrador
from bugalu.modulos.catalogo.dominio import cambios_sensibles as sensibles
from bugalu.modulos.catalogo.dominio.precio import Servicio
from bugalu.modulos.catalogo.dominio.puertos import RepositorioCatalogo


class ActualizarServicio:
    def __init__(self, catalogo: RepositorioCatalogo) -> None:
        self._catalogo = catalogo

    async def ejecutar(self, id_servicio: UUID, cambios: Mapping[str, Any]) -> Servicio:
        await exigir_administrador(self._catalogo)
        actual = await self._catalogo.obtener_servicio(id_servicio)
        if actual is None:
            raise NoEncontrado("No existe el servicio.")
        sensibles.exigir_confirmacion(
            "servicio",
            sensibles.valores_servicio(actual),
            {k: sensibles.texto(v) for k, v in cambios.items() if k != "especialistas_por_defecto"},
        )
        # Los sensibles llegan aqui con su mismo valor (si no, fue 428): solo se escribe lo demas.
        campos: dict[str, Decimal | bool] = {
            k: v
            for k, v in cambios.items()
            if k not in sensibles.SENSIBLES["servicio"] and k != "especialistas_por_defecto"
        }
        if (ids := cambios.get("especialistas_por_defecto")) is not None:
            unicos = list(dict.fromkeys(ids))
            if len(await self._catalogo.obtener_especialistas(unicos)) != len(unicos):
                raise DatosInvalidos("Algun especialista no existe.")
            await self._catalogo.reemplazar_especialistas_por_defecto(id_servicio, unicos)
        if campos:
            await self._catalogo.actualizar_servicio(id_servicio, campos)
        servicio = await self._catalogo.obtener_servicio(id_servicio)
        if servicio is None:
            raise LookupError("El servicio desaparecio durante la transaccion.")
        return servicio
