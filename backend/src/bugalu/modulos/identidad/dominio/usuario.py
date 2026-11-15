from dataclasses import dataclass
from enum import StrEnum
from uuid import UUID


class Rol(StrEnum):
    CLIENTE = "cliente"
    PERSONAL = "personal"
    ADMINISTRADOR = "administrador"


@dataclass(frozen=True)
class Usuario:
    id: UUID
    nombre: str | None
    rol: Rol
    especialidad: str | None
