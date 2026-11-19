from collections.abc import Collection, Mapping, Sequence
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Protocol
from uuid import UUID

from bugalu.modulos.catalogo.dominio.cambios_sensibles import CambioRegistrado, Confirmacion
from bugalu.modulos.catalogo.dominio.precio import (
    ConfiguracionImpuestos,
    Especialista,
    Feriado,
    Recargos,
    Servicio,
)


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

    async def obtener_impuestos(self) -> ConfiguracionImpuestos: ...

    async def parametros_vigentes(self) -> dict[str, Any]:
        """IGV y parametros que una reserva guarda al crearse (RF-20 CA-07)."""
        ...

    async def obtener_parametros(self) -> dict[str, Any]: ...

    async def bloquear_recurso(self, recurso: str, id_recurso: UUID | None) -> None:
        """Serializa confirmaciones concurrentes sobre el mismo recurso (RF-20 CA-06)."""
        ...

    async def contar_operaciones_vigentes(self) -> int:
        """Reservas `pre_reservada` o `confirmada` con inicio futuro."""
        ...

    async def obtener_precios_profesional(
        self, id_profesional: UUID
    ) -> tuple[str, dict[str, str]] | None:
        """(nombre, {precio_30, precio_60} en texto canonico o `no_ofrece`) de un perfil (RF-15)."""
        ...

    async def contar_asesorias_vigentes(self, id_profesional: UUID) -> int:
        """Asesorias `pre_reservada` o `confirmada` del profesional que aun no empiezan."""
        ...

    async def obtener_recargos(self) -> Recargos: ...

    async def listar_feriados(self, anio: int | None) -> list[Feriado]: ...

    async def feriados_en(self, fechas: Collection[date]) -> frozenset[date]: ...

    async def agregar_feriado(self, feriado: Feriado) -> None:
        """Lanza FeriadoRepetido si la fecha ya existe."""
        ...

    async def eliminar_feriado(self, fecha: date) -> bool: ...


class RepositorioCambios(Protocol):
    """Confirmaciones de cambios sensibles y registro de cambios (RF-20)."""

    async def id_usuario(self) -> UUID: ...

    async def guardar_confirmacion(
        self,
        hash_token: str,
        recurso: str,
        id_recurso: UUID | None,
        nombre_recurso: str,
        cambios: Mapping[str, tuple[str, str]],
        minutos: int,
    ) -> datetime:
        """Devuelve `expira_en`."""
        ...

    async def tomar_confirmacion(self, hash_token: str) -> Confirmacion | None:
        """La busca por el hash de su token y la bloquea hasta el fin de la transaccion."""
        ...

    async def aplicar(self, confirmacion: Confirmacion) -> list[CambioRegistrado]:
        """Consume la confirmacion, aplica sus campos y escribe una fila de registro por campo.

        Es la unica via de escritura de los campos sensibles: la base la exige (RF-20 CA-04).
        """
        ...

    async def listar(
        self, desde: datetime, hasta: datetime, recurso: str | None
    ) -> list[CambioRegistrado]:
        """Del mas reciente al mas antiguo; `hasta` es exclusivo."""
        ...
