from collections.abc import Callable
from typing import Any
from uuid import UUID

from bugalu.compartido.errores import NoEncontrado
from bugalu.modulos.catalogo.dominio import cambios_sensibles as sensibles
from bugalu.modulos.catalogo.dominio.puertos import RepositorioCatalogo


async def cargar(
    catalogo: RepositorioCatalogo, recurso: str, id_recurso: UUID | None
) -> tuple[str, Any]:
    """(nombre del recurso, objeto de dominio); 404 si el servicio o el especialista no existe."""
    if recurso == "servicio" and id_recurso:
        servicio = await catalogo.obtener_servicio(id_recurso)
        if servicio:
            return servicio.nombre, servicio
    elif recurso == "especialista" and id_recurso:
        for especialista in await catalogo.obtener_especialistas([id_recurso]):
            return especialista.nombre, especialista
    elif recurso == "profesional" and id_recurso:
        encontrado = await catalogo.obtener_precios_profesional(id_recurso)
        if encontrado:
            return encontrado
    elif recurso == "impuestos":
        return "Impuestos", await catalogo.obtener_impuestos()
    elif recurso == "recargos":
        return "Recargos", await catalogo.obtener_recargos()
    elif recurso == "parametros":
        return "Parámetros", await catalogo.obtener_parametros()
    raise NoEncontrado("No existe el recurso.")


def valores(recurso: str, objeto: Any) -> dict[str, str]:
    leer: dict[str, Callable[[Any], dict[str, str]]] = {
        "servicio": sensibles.valores_servicio,
        "especialista": sensibles.valores_especialista,
        "impuestos": sensibles.valores_impuestos,
        "recargos": sensibles.valores_recargos,
        "parametros": sensibles.valores_parametros,
        "profesional": dict,  # ya son {precio_30, precio_60} en texto canonico
    }
    return leer[recurso](objeto)
