import hashlib
import secrets
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from typing import Any
from uuid import UUID

from bugalu.compartido.errores import DatosInvalidos, SinCambios
from bugalu.modulos.catalogo.aplicacion.lectura_recurso import cargar, valores
from bugalu.modulos.catalogo.aplicacion.permisos import exigir_administrador
from bugalu.modulos.catalogo.dominio import cambios_sensibles as sensibles
from bugalu.modulos.catalogo.dominio import impacto
from bugalu.modulos.catalogo.dominio.impacto import Ejemplo
from bugalu.modulos.catalogo.dominio.precio import Especialista, Servicio
from bugalu.modulos.catalogo.dominio.puertos import RepositorioCambios, RepositorioCatalogo

_USOS_MAXIMOS = 3


def hash_de(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


@dataclass(frozen=True)
class Previsualizacion:
    token: str
    expira_en: datetime
    recurso: str
    id_recurso: UUID | None
    nombre_recurso: str
    cambios: list[tuple[str, str, str]]  # (campo, anterior, nuevo)
    ejemplos: list[Ejemplo]
    operaciones_vigentes: int


class PrevisualizarCambio:
    def __init__(self, catalogo: RepositorioCatalogo, cambios: RepositorioCambios) -> None:
        self._catalogo = catalogo
        self._cambios = cambios

    async def ejecutar(
        self,
        recurso: str,
        id_recurso: UUID | None,
        propuesto: Mapping[str, str],
        ahora: datetime,
    ) -> Previsualizacion:
        """Valida, calcula antes/despues e impacto y guarda la confirmacion; no cambia nada."""
        await exigir_administrador(self._catalogo)
        nombre, actual = await cargar(self._catalogo, recurso, id_recurso)
        diferencias = sensibles.diferencias(valores(recurso, actual), propuesto)
        if not diferencias:
            raise SinCambios("No hay diferencias con los valores actuales.")
        nuevo = sensibles.aplicar(recurso, actual, {c: d for c, (_, d) in diferencias.items()})
        if recurso == "parametros":
            sensibles.validar_plazos(nuevo)
        if recurso == "recargos" and nuevo.desde_noche == nuevo.hasta_noche:
            raise DatosInvalidos(
                "La noche no puede empezar y terminar a la misma hora.", {"campo": "noche"}
            )
        ejemplos = await self._ejemplos(recurso, actual, nuevo, diferencias, ahora)
        token = secrets.token_urlsafe(32)
        expira = await self._cambios.guardar_confirmacion(
            hash_de(token), recurso, id_recurso, nombre, diferencias, sensibles.MINUTOS_DE_VIGENCIA
        )
        return Previsualizacion(
            token,
            expira,
            recurso,
            id_recurso,
            nombre,
            [(c, a, n) for c, (a, n) in diferencias.items()],
            ejemplos,
            await self._catalogo.contar_operaciones_vigentes(),
        )

    async def _ejemplos(
        self,
        recurso: str,
        antes: Any,
        despues: Any,
        diferencias: Mapping[str, tuple[str, str]],
        ahora: datetime,
    ) -> list[Ejemplo]:
        if recurso == "parametros":
            return impacto.ejemplos_parametros(antes, despues, set(diferencias), ahora)
        if recurso == "impuestos":
            return impacto.ejemplos_impuestos(antes, despues)
        impuestos = await self._catalogo.obtener_impuestos()
        servicios = [
            s for s in await self._catalogo.listar_servicios() if s.ocupa_sala and s.activo
        ]
        if recurso == "servicio":
            return impacto.ejemplos_servicio(antes, despues, impuestos)
        if recurso == "especialista":
            return impacto.ejemplos_especialista(
                await self._usos(antes, servicios), antes, despues, impuestos
            )
        if not servicios:  # recargos: el servicio de referencia es el primero reservable
            return []
        return impacto.ejemplos_recargos(servicios[0], antes, despues, impuestos, diferencias)

    async def _usos(
        self, especialista: Especialista, servicios: list[Servicio]
    ) -> list[tuple[Servicio, list[Especialista]]]:
        """Los servicios que traen al especialista por defecto, con sus demas especialistas."""
        usos: list[tuple[Servicio, list[Especialista]]] = []
        for servicio in servicios:
            if especialista.id not in servicio.especialistas_por_defecto:
                continue
            otros = [i for i in servicio.especialistas_por_defecto if i != especialista.id]
            conocidos = await self._catalogo.obtener_especialistas(otros)
            usos.append((servicio, [e for e in conocidos if e.activo]))
        if usos:
            return usos[:_USOS_MAXIMOS]
        # Si ningun servicio lo trae, se ejemplifica sumado al de referencia.
        return [(servicios[0], [])] if servicios else []
