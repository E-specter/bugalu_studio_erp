from contextlib import AbstractAsyncContextManager
from dataclasses import dataclass
from typing import Any, Protocol
from uuid import UUID

from bugalu.modulos.notificaciones.dominio.correo import Correo

MAX_INTENTOS = 5


@dataclass(frozen=True)
class Pendiente:
    id: UUID
    tipo: str
    destinatario: str
    datos: dict[str, Any]
    intentos: int


class EnviadorCorreo(Protocol):
    async def enviar(self, correo: Correo) -> None: ...


class Lote(Protocol):
    pendientes: list[Pendiente]

    async def marcar_enviada(self, id_: UUID) -> None: ...

    async def marcar_fallo(self, id_: UUID, error: str) -> None: ...


class Bandeja(Protocol):
    def tomar(self, limite: int, max_intentos: int) -> AbstractAsyncContextManager[Lote]:
        """Reserva en exclusiva un lote de pendientes hasta cerrar el contexto."""
        ...
