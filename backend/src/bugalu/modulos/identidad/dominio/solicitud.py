from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from uuid import UUID


class EstadoSolicitud(StrEnum):
    PENDIENTE = "pendiente"
    APROBADA = "aprobada"
    RECHAZADA = "rechazada"


@dataclass(frozen=True)
class Solicitud:
    id: UUID
    id_usuario: UUID
    nombre: str | None
    correo: str | None
    especialidad: str
    mensaje: str | None
    estado: EstadoSolicitud
    motivo: str | None
    creada_en: datetime
    revisada_en: datetime | None
