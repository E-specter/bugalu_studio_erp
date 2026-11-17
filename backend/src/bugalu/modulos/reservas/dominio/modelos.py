from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Any
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
    pago_por_validar: bool = False  # solo lo llena la base para personal y administrador


@dataclass(frozen=True)
class Referencia:
    id: UUID
    nombre: str | None


@dataclass(frozen=True)
class ServicioReservado:
    id: UUID
    nombre: str
    categoria: str


@dataclass(frozen=True)
class PagoCuota:
    id: UUID
    estado: str
    metodo: str
    monto: Decimal
    numero_operacion: str
    motivo_rechazo: str | None
    registrado_en: datetime


@dataclass(frozen=True)
class CuotaReserva:
    id: UUID
    hito: str
    monto: Decimal
    estado: str  # pendiente | en_validacion | pagada
    pagable: bool
    pagos: tuple[PagoCuota, ...] = ()


@dataclass(frozen=True)
class Reserva:
    """Reserva con sus datos de lectura; `precio` es la simulacion guardada al reservarla."""

    id: UUID
    folio: str
    estado: str
    motivo_cancelacion: str | None
    inicio: datetime
    fin: datetime
    fin_buffer: datetime
    sala: Referencia
    servicio: ServicioReservado
    especialistas: tuple[Referencia, ...]
    precio: dict[str, Any]
    cuotas: tuple[CuotaReserva, ...]
    vence_pago: datetime | None
    id_cliente: UUID
    cliente: Referencia | None = None  # solo para personal y administrador
    nota_cancelacion: str | None = None  # solo el dueno y el administrador la reciben
    en_validacion: bool = False  # dato de la base: el personal no ve los pagos, solo si hay uno

    @property
    def pago_por_validar(self) -> bool:
        return self.en_validacion or any(c.estado == "en_validacion" for c in self.cuotas)


@dataclass(frozen=True)
class EspecialistaAplicado:
    id: UUID
    monto_fijo: Decimal
    monto_variable: Decimal
    unidad: str


@dataclass(frozen=True)
class Cotizacion:
    categoria: str
    precio: dict[str, Any]
    total: Decimal
    anticipo: Decimal
    especialistas: tuple[EspecialistaAplicado, ...]
    parametros_aplicados: dict[str, Any]  # IGV y parametros vigentes al cotizar (RF-20 CA-07)


@dataclass(frozen=True)
class NuevaReserva:
    id_sala: UUID
    id_servicio: UUID
    id_franja: UUID
    inicio: datetime
    fin: datetime
    detalle: str | None
    vence_pago: datetime
    cotizacion: Cotizacion
    cuotas: tuple[tuple[str, Decimal], ...]


PARAMETROS = (
    "dias_limite_pago",
    "horas_limite_pago",
    "anticipacion_minima_horas",
    "anticipacion_maxima_semanas",
    "porcentaje_adelanto",
    "horas_nivel_1",
    "horas_nivel_2",
    "porcentaje_penalizacion_nivel_2",
    "minutos_tolerancia_inasistencia",
    "dias_vigencia_credito",
    "reprogramaciones_nivel_1",
    "reprogramaciones_nivel_2",
)
