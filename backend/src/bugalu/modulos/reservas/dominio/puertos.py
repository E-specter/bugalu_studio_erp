from collections.abc import Mapping, Sequence
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Protocol
from uuid import UUID

from bugalu.modulos.reservas.dominio.disponibilidad import Tramo
from bugalu.modulos.reservas.dominio.modelos import (
    Cierre,
    ContextoReprogramacion,
    Cotizacion,
    EspecialistaAplicado,
    Franja,
    NuevaReserva,
    ParametrosDanos,
    RequisitosReserva,
    Reserva,
    ReservaVisible,
    Sala,
    VistaCancelacion,
    VistaReprogramacion,
)


class Cotizador(Protocol):
    """Precio de un tramo con el motor del catalogo (RN-15); sin escribir nada."""

    async def cotizar(
        self,
        id_sala: UUID,
        id_servicio: UUID,
        inicio: datetime,
        fin: datetime,
        id_especialistas: Sequence[UUID],
        parametros: dict[str, Any] | None = None,
    ) -> Cotizacion:
        """`parametros`: los guardados en una reserva (IGV, adelanto); sin ellos, los vigentes."""
        ...


class RepositorioReservas(Protocol):
    async def es_administrador(self) -> bool: ...

    async def es_personal(self) -> bool:
        """Personal o administrador."""
        ...

    async def listar_salas(self) -> list[Sala]: ...

    async def actualizar_itse_sala(
        self, id_sala: UUID, aforo: int, certificado: str, vence: date
    ) -> Sala | None:
        """None si la sala no existe."""
        ...

    async def existe_sala(self, id_sala: UUID) -> bool: ...

    async def limites_reserva(self) -> tuple[int, int]:
        """(anticipacion minima en horas, anticipacion maxima en semanas)."""
        ...

    async def franjas_en(self, id_sala: UUID, desde: datetime, hasta: datetime) -> list[Franja]:
        """Las que se solapan con [desde, hasta)."""
        ...

    async def franjas_antes_de(self, id_sala: UUID, instante: datetime) -> list[Franja]:
        """Las mas recientes que empiezan antes de `instante` (con un tope fijo)."""
        ...

    async def cierres_en(self, id_sala: UUID, desde: datetime, hasta: datetime) -> list[Cierre]: ...

    async def ocupacion(self, id_sala: UUID, desde: datetime, hasta: datetime) -> list[Tramo]:
        """Reservas vigentes con su buffer; una pre_reservada vencida cuenta como libre."""
        ...

    async def reservas_visibles(
        self, id_sala: UUID, desde: datetime, hasta: datetime
    ) -> list[ReservaVisible]: ...

    async def nombres_de_clientes(self, ids: Sequence[UUID]) -> Mapping[UUID, str | None]: ...

    async def insertar_franjas(self, id_sala: UUID, tramos: Sequence[Tramo]) -> list[Franja]:
        """FranjaSolapada si alguna se solapa con otra de la sala o entre si."""
        ...

    async def bloquear_sala(self, id_sala: UUID) -> None:
        """Serializa las escrituras que dependen de franjas, cierres y ocupacion de la sala."""
        ...

    async def obtener_franja(self, id_franja: UUID) -> Franja | None: ...

    async def eliminar_franja(self, id_franja: UUID) -> None: ...

    async def insertar_cierre(self, id_sala: UUID, tramo: Tramo, motivo: str) -> Cierre: ...

    async def obtener_cierre(self, id_cierre: UUID) -> Cierre | None: ...

    async def eliminar_cierre(self, id_cierre: UUID) -> None: ...

    async def obtener_parametros(self) -> dict[str, Any]:
        """Enteros por clave, mas `tarifa_hora_gestion` (Decimal)."""
        ...

    async def obtener_parametros_danos(self) -> ParametrosDanos: ...

    async def guardar_parametros(self, cambios: Mapping[str, int]) -> None: ...

    async def plazos_pago(self) -> tuple[int, int]:
        """(dias, horas) de RN-18."""
        ...

    async def tiene_servicio_previo(self) -> bool:
        """El usuario tiene una reserva no ensayo `confirmada` o posterior (RN-13)."""
        ...

    async def insertar_reserva(self, nueva: NuevaReserva) -> UUID:
        """TramoNoDisponible si la base detecta un solape. Con sus cuotas y especialistas."""
        ...

    async def encolar_aviso_reserva(self, id_reserva: UUID) -> None: ...

    async def requisitos_para_reservar(self) -> RequisitosReserva: ...

    async def aceptar_condiciones(self, id_reserva: UUID, version: str) -> None:
        """Registra la aceptacion de las condiciones vigentes ligada a la reserva (CA-08)."""
        ...

    async def obtener_reserva(self, id_reserva: UUID) -> Reserva | None:
        """Solo las que la RLS deja ver."""
        ...

    async def existe_reserva(self, id_reserva: UUID) -> bool:
        """Existe, sea o no visible para quien pregunta."""
        ...

    async def listar_mias(self) -> list[Reserva]: ...

    async def listar_en_rango(self, desde: datetime, hasta: datetime) -> list[Reserva]: ...

    async def cancelar_reserva(
        self,
        id_reserva: UUID,
        nota: str | None = None,
        nivel_esperado: int | None = None,
        por: str | None = None,
        aviso_en: datetime | None = None,
    ) -> None:
        """La base calcula el nivel y los montos. NoEncontrado, SinPermiso, NoCancelable,
        NotaRequerida, AvisoInvalido, NivelCambiado (con la vista nueva en `detalles`) o
        DatosInvalidos."""
        ...

    async def vista_cancelacion(
        self, id_reserva: UUID, aviso_en: datetime | None = None
    ) -> VistaCancelacion:
        """Sin cambiar nada. NoEncontrado, SinPermiso, NoCancelable o AvisoInvalido."""
        ...

    async def marcar_inasistencia(self, id_reserva: UUID) -> None:
        """NoEncontrado, SinPermiso, NoAplicable o ToleranciaNoCumplida."""
        ...

    async def aplicar_excepcion(self, id_reserva: UUID, motivo: str) -> None:
        """NoEncontrado, SinPermiso, ExcepcionNoAplicable, ExcepcionYaAplicada o DatosInvalidos."""
        ...

    async def ocupacion_excluyendo(
        self, id_sala: UUID, desde: datetime, hasta: datetime, excluir: UUID
    ) -> list[Tramo]:
        """Como `ocupacion`, sin la reserva `excluir` (puede solaparse con su propio horario)."""
        ...

    async def contexto_reprogramacion(self, id_reserva: UUID) -> ContextoReprogramacion:
        """NoEncontrado (no es suya), SinPermiso (personal; administrador fuera del estudio),
        ReprogramacionNoPermitida o LimiteReprogramaciones."""
        ...

    async def vista_reprogramacion(
        self, id_reserva: UUID, inicio: datetime, total: Decimal, precio: dict[str, Any]
    ) -> VistaReprogramacion:
        """Sin cambiar nada; `precio` es el desglose que se devuelve junto a lo calculado."""
        ...

    async def reprogramar_reserva(  # noqa: PLR0913
        self,
        id_reserva: UUID,
        inicio: datetime,
        nivel_esperado: int | None,
        total_esperado: Decimal | None,
        id_franja: UUID,
        precio: dict[str, Any],
        total: Decimal,
        especialistas: Sequence[EspecialistaAplicado],
    ) -> None:
        """La base calcula nivel, penalizacion, saldo y credito. Ademas de los de
        `contexto_reprogramacion`: NivelCambiado o PrecioCambiado (con la vista nueva en
        `detalles`), TramoNoDisponible o DatosInvalidos."""
        ...

    async def elegir_estudio_devolucion(self, id_reserva: UUID) -> None:
        """NoEncontrado, SinPermiso o EleccionNoDisponible."""
        ...
