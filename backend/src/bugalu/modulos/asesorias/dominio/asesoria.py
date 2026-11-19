from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Any, Protocol
from uuid import UUID

from bugalu.modulos.asesorias.dominio.modelos import Horario, Profesional
from bugalu.modulos.catalogo.dominio.precio import ConfiguracionImpuestos
from bugalu.modulos.reservas.dominio.modelos import CuotaReserva, Politica, RequisitosReserva


@dataclass(frozen=True)
class NuevaAsesoria:
    id_profesional: UUID
    inicio: datetime
    fin: datetime
    modalidad: str
    total: Decimal  # con IGV: la unica cuota `al_reservar`
    precio: dict[str, Any]  # {total, impuesto}, guardado al agendar
    vence_pago: datetime


@dataclass(frozen=True)
class PersonaAsesoria:
    id: UUID
    nombre: str | None
    nombre_artistico: str | None
    telefono: str | None = None  # solo el cliente que ve su profesional o el administrador
    correo: str | None = None


@dataclass(frozen=True)
class Asesoria:
    id: UUID
    folio: str
    estado: str
    motivo_cancelacion: str | None
    inicio: datetime
    fin: datetime
    precio: dict[str, Any]
    vence_pago: datetime | None
    id_cliente: UUID
    profesional: PersonaAsesoria
    modalidad: str
    lugar: str | None
    enlace: str | None
    realizada_en: datetime | None = None
    cuotas: tuple[CuotaReserva, ...] | None = None  # None: no se le muestran
    pagado: Decimal | None = None
    politica: Politica | None = None
    version_condiciones: str | None = None
    cliente: PersonaAsesoria | None = None  # solo su profesional y el administrador
    notas: str | None = None  # idem

    @property
    def duracion(self) -> int:
        return int((self.fin - self.inicio).total_seconds() // 60)

    @property
    def constancia_disponible(self) -> bool:
        return self.estado == "realizada"


class RepositorioAgenda(Protocol):
    async def es_administrador(self) -> bool: ...

    async def es_profesional(self) -> bool: ...

    async def requisitos_para_reservar(self) -> RequisitosReserva: ...

    async def limites_reserva(self) -> tuple[int, int]: ...

    async def plazos_pago(self) -> tuple[int, int]: ...

    async def obtener_profesional(self, id_profesional: UUID) -> Profesional | None: ...

    async def obtener_impuestos(self) -> ConfiguracionImpuestos: ...

    async def listar_horarios(
        self, id_profesional: UUID, desde: datetime, hasta: datetime
    ) -> list[Horario]: ...

    async def insertar_asesoria(self, nueva: NuevaAsesoria) -> UUID:
        """Reserva, fila de asesoria y cuota unica. Lanza HorarioNoDisponible (exclusion),
        FueraDeHorario, DuracionNoOfrecida o NoEncontrado (perfil no publicado)."""
        ...

    async def aceptar_condiciones(self, id_asesoria: UUID, version: str) -> None: ...

    async def encolar_aviso(self, id_asesoria: UUID) -> None: ...

    async def obtener_asesoria(self, id_asesoria: UUID) -> Asesoria | None:
        """Con cuotas, contacto del cliente y notas si quien llama es el profesional o el
        administrador; la RLS decide la visibilidad."""
        ...

    async def listar_mias(self) -> list[Asesoria]: ...

    async def listar(
        self,
        estado: str | None,
        desde: datetime | None,
        hasta: datetime | None,
        id_profesional: UUID | None,
        por_cerrar_antes_de: datetime | None,
    ) -> list[Asesoria]: ...

    async def cambiar_encuentro(
        self, id_asesoria: UUID, modalidad: str, lugar: str | None, enlace: str | None
    ) -> None:
        """Lanza NoEncontrado, SinPermiso o NoEditable (la base lo decide)."""
        ...
