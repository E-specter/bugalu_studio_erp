from contextlib import AbstractAsyncContextManager
from dataclasses import dataclass
from datetime import datetime
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
    creada_en: datetime | None = None  # su epoch es el SEQUENCE del evento de calendario


@dataclass(frozen=True)
class DatosReserva:
    """Lo que el evento de calendario necesita y el aviso no trae."""

    inicio: datetime
    fin: datetime
    servicio: str
    sala: str
    tiene_evento: bool  # hubo un pago_aprobado con reserva_confirmada antes de este aviso
    ubicacion: str | None = None  # asesoria: lugar o enlace (o `Por confirmar`)


class EnviadorCorreo(Protocol):
    async def enviar(self, correo: Correo) -> None: ...


class Lote(Protocol):
    pendientes: list[Pendiente]
    instrucciones: list[tuple[str, str]]  # (metodo, texto) activos, para `reserva_creada`
    reservas: dict[UUID, DatosReserva]  # por id de notificacion, solo avisos con evento

    async def marcar_enviada(self, id_: UUID) -> None: ...

    async def marcar_fallo(self, id_: UUID, error: str) -> None: ...


class Bandeja(Protocol):
    def tomar(self, limite: int, max_intentos: int) -> AbstractAsyncContextManager[Lote]:
        """Reserva en exclusiva un lote de pendientes hasta cerrar el contexto."""
        ...
