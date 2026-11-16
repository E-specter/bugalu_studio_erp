from collections.abc import Collection, Mapping, Sequence
from datetime import date
from decimal import Decimal
from typing import Protocol
from uuid import UUID

from bugalu.modulos.catalogo.dominio.precio import Especialista, Feriado, Recargos, Servicio


class RepositorioCatalogo(Protocol):
    async def es_administrador(self) -> bool: ...

    async def existe_sala(self, id_sala: UUID) -> bool:
        """Solo cuenta las salas activas."""
        ...

    async def listar_servicios(self) -> list[Servicio]: ...

    async def obtener_servicio(self, id_servicio: UUID) -> Servicio | None: ...

    async def actualizar_servicio(
        self, id_servicio: UUID, cambios: Mapping[str, Decimal | bool]
    ) -> None: ...

    async def reemplazar_especialistas_por_defecto(
        self, id_servicio: UUID, ids: Sequence[UUID]
    ) -> None: ...

    async def listar_especialistas(self) -> list[Especialista]: ...

    async def obtener_especialistas(self, ids: Collection[UUID]) -> list[Especialista]:
        """Los que existen entre `ids` (activos o no)."""
        ...

    async def actualizar_especialista(
        self, id_especialista: UUID, cambios: Mapping[str, Decimal | bool | str]
    ) -> Especialista | None: ...

    async def obtener_recargos(self) -> Recargos: ...

    async def guardar_recargos(self, recargos: Recargos) -> None: ...

    async def listar_feriados(self, anio: int | None) -> list[Feriado]: ...

    async def feriados_en(self, fechas: Collection[date]) -> frozenset[date]: ...

    async def agregar_feriado(self, feriado: Feriado) -> None:
        """Lanza FeriadoRepetido si la fecha ya existe."""
        ...

    async def eliminar_feriado(self, fecha: date) -> bool: ...
