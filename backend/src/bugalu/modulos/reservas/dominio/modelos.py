from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass(frozen=True)
class Sala:
    id: UUID
    nombre: str
    sede: str


@dataclass(frozen=True)
class Franja:
    id: UUID
    id_sala: UUID
    inicio: datetime
    fin: datetime


@dataclass(frozen=True)
class Cierre:
    id: UUID
    id_sala: UUID
    inicio: datetime
    fin: datetime
    motivo: str


@dataclass(frozen=True)
class ReservaVisible:
    """Reserva no cancelada tal como la deja ver la RLS: las propias o, para personal, todas."""

    id: UUID
    folio: str
    id_cliente: UUID
    servicio: str
    estado: str
    inicio: datetime
    fin_buffer: datetime


PARAMETROS = (
    "dias_limite_pago",
    "horas_limite_pago",
    "anticipacion_minima_horas",
    "anticipacion_maxima_semanas",
)
