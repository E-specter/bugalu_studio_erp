from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from uuid import UUID


@dataclass(frozen=True)
class NuevoPago:
    id: UUID
    id_cuota: UUID
    id_cliente: UUID
    metodo: str
    monto: Decimal
    numero_operacion: str
    ruta_captura: str
    tipo_captura: str  # mime


@dataclass(frozen=True)
class CuotaResumen:
    id: UUID
    hito: str
    monto: Decimal


@dataclass(frozen=True)
class ReservaResumen:
    id: UUID
    folio: str
    inicio: datetime
    estado: str
    porcentaje_igv: Decimal  # el guardado en la reserva al crearla (RF-20 CA-03)


@dataclass(frozen=True)
class ClienteResumen:
    id: UUID
    nombre: str | None


@dataclass(frozen=True)
class Pago:
    id: UUID
    estado: str
    metodo: str
    monto: Decimal
    numero_operacion: str
    motivo_rechazo: str | None
    registrado_en: datetime
    validado_en: datetime | None
    ruta_captura: str
    tipo_captura: str  # mime
    cuota: CuotaResumen
    reserva: ReservaResumen
    cliente: ClienteResumen | None  # solo lo ve el administrador

    @property
    def monto_coincide(self) -> bool:
        return self.monto == self.cuota.monto


@dataclass(frozen=True)
class CapturaFirmada:
    url: str
    expira_en: datetime
    tipo: str  # "imagen" | "pdf"
