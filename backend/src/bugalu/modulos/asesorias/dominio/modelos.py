from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from uuid import UUID

from bugalu.modulos.catalogo.dominio.precio import Impuesto
from bugalu.modulos.reservas.dominio.disponibilidad import Tramo


@dataclass(frozen=True)
class Especialidad:
    id: UUID
    nombre: str
    activa: bool


@dataclass(frozen=True)
class Duracion:
    minutos: int
    precio: Decimal  # soles, con IGV
    igv: Impuesto  # forma de Simulacion.impuesto (RF-20 CA-02)


@dataclass(frozen=True)
class Profesional:
    id: UUID
    nombre: str | None
    nombre_artistico: str | None
    presentacion: str | None
    redes: tuple[dict[str, str], ...]
    especialidades: tuple[Especialidad, ...]  # solo las activas
    foto_ruta: str | None
    # minutos -> precio; si falta la duracion, no la ofrece
    precios: Mapping[int, Decimal] = field(default_factory=dict)
    activo: bool = False
    publicado: bool = False


@dataclass(frozen=True)
class Horario:
    id: UUID
    id_profesional: UUID
    inicio: datetime
    fin: datetime


@dataclass(frozen=True)
class Ocupado(Tramo):
    """Tramo ocupado de un profesional; `propia`: es del cliente que consulta."""

    propia: bool = False
