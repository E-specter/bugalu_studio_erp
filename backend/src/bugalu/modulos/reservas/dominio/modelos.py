from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from bugalu.modulos.reservas.dominio.disponibilidad import LIMA


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
    estado: str  # pendiente | en_validacion | pagada | anulada
    pagable: bool
    pagos: tuple[PagoCuota, ...] = ()
    pagado: Decimal = Decimal("0.00")  # lo aplicado de captura y credito


@dataclass(frozen=True)
class Excepcion:
    motivo: str
    por: Referencia | None  # solo personal y administrador
    en: datetime


@dataclass(frozen=True)
class CancelacionReserva:
    """RF-18: lo que la base guardo al cancelar o marcar la inasistencia.

    `por`: cliente, estudio o inasistencia."""

    nivel: int | None
    aviso_en: datetime
    por: str
    pagado: Decimal
    retenido: Decimal
    credito: Decimal
    nota: str | None  # solo el dueno y el administrador
    registrada_por: Referencia | None  # solo personal y administrador
    excepcion: Excepcion | None = None


@dataclass(frozen=True)
class Reprogramacion:
    anterior_inicio: datetime
    nuevo_inicio: datetime
    nivel: int | None
    penalizacion: Decimal
    total_anterior: Decimal
    total_nuevo: Decimal
    por: Referencia | None
    en: datetime


@dataclass(frozen=True)
class Politica:
    """Plazos y porcentajes guardados en la reserva (`parametros_aplicados`), solo lectura."""

    horas_nivel_1: int
    horas_nivel_2: int
    porcentaje_penalizacion_nivel_2: int
    minutos_tolerancia_inasistencia: int
    dias_vigencia_credito: int
    reprogramaciones_nivel_1: int
    reprogramaciones_nivel_2: int

    @classmethod
    def desde_parametros(cls, parametros: dict[str, Any]) -> Politica:
        return cls(**{campo: int(parametros[campo]) for campo in cls.__dataclass_fields__})


@dataclass(frozen=True)
class Devolucion:
    """Devolucion de un credito de nivel 1 o de excepcion, o la del estudio (RF-18 CA-07, CA-13)."""

    id: UUID
    id_credito: UUID | None
    id_reserva: UUID
    folio: str
    cliente: Referencia
    tipo: str  # nivel_1 | estudio
    motivo: str
    monto_solicitado: Decimal
    solicitada_en: datetime
    estado: str  # pendiente | aprobada | rechazada | realizada
    monto_aprobado: Decimal | None = None
    motivo_decision: str | None = None
    decidida_en: datetime | None = None
    nota_realizada: str | None = None
    realizada_en: datetime | None = None
    limite: datetime | None = None


@dataclass(frozen=True)
class VistaCancelacion:
    nivel: int | None
    anticipacion_horas: Decimal
    pagado: Decimal
    en_validacion: Decimal
    retenido: Decimal
    credito: Decimal
    credito_vence: datetime | None
    puede_reprogramar: bool
    reprogramaciones_restantes: int

    def a_json(self) -> dict[str, Any]:
        """Para el `detalles` de un 409: montos como texto decimal y fechas ISO con zona de Lima."""
        return {
            "nivel": self.nivel,
            "anticipacion_horas": float(self.anticipacion_horas),
            "pagado": str(self.pagado),
            "en_validacion": str(self.en_validacion),
            "retenido": str(self.retenido),
            "credito": str(self.credito),
            "credito_vence": self.credito_vence.astimezone(LIMA).isoformat()
            if self.credito_vence
            else None,
            "puede_reprogramar": self.puede_reprogramar,
            "reprogramaciones_restantes": self.reprogramaciones_restantes,
        }


@dataclass(frozen=True)
class ContextoReprogramacion:
    """Lo que se conserva al reprogramar (misma sala, servicio, duracion y especialistas).

    `estudio`: la reserva espera la eleccion tras una cancelacion del estudio (sin nivel ni
    recalculo de precio)."""

    id_sala: UUID
    id_servicio: UUID
    inicio: datetime
    fin: datetime
    estudio: bool
    precio: dict[str, Any]
    total: Decimal
    id_especialistas: tuple[UUID, ...]


@dataclass(frozen=True)
class VistaReprogramacion:
    nivel: int | None
    penalizacion: Decimal
    precio: dict[str, Any]
    saldo: Decimal
    credito: Decimal
    reprogramaciones_restantes: int


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
    version_condiciones: str | None = None  # RF-17: solo la ven el dueno y el administrador
    pagado: Decimal = Decimal("0.00")
    politica: Politica | None = None
    cancelacion: CancelacionReserva | None = None
    reprogramaciones: tuple[Reprogramacion, ...] = ()
    eleccion_estudio: str | None = None
    devolucion: Devolucion | None = None  # la del estudio, si existe

    @property
    def pago_por_validar(self) -> bool:
        return self.en_validacion or any(c.estado == "en_validacion" for c in self.cuotas)


@dataclass(frozen=True)
class RequisitosReserva:
    """Lo que el perfil del cliente debe cumplir antes de reservar (RF-17, CA-05, CA-07)."""

    pendientes: tuple[dict[str, str], ...]  # textos del registro por aceptar
    campos_faltantes: tuple[str, ...]
    es_menor: bool
    condiciones_vigentes: dict[str, str] | None  # {tipo, version, vigente_desde}


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
