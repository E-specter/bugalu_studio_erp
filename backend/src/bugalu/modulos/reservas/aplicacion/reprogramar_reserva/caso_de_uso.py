from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from bugalu.compartido.errores import (
    DatosInvalidos,
    FueraDeFranja,
    NivelCambiado,
    PrecioCambiado,
    TramoNoDisponible,
)
from bugalu.modulos.reservas.aplicacion.clientes import con_clientes
from bugalu.modulos.reservas.dominio import disponibilidad as calculo
from bugalu.modulos.reservas.dominio import reserva as reglas
from bugalu.modulos.reservas.dominio.disponibilidad import PASO
from bugalu.modulos.reservas.dominio.modelos import (
    Cotizacion,
    EspecialistaAplicado,
    Reserva,
    VistaReprogramacion,
)
from bugalu.modulos.reservas.dominio.puertos import Cotizador, RepositorioReservas


@dataclass(frozen=True)
class _Plan:
    id_franja: UUID
    precio: dict[str, Any]
    total: Decimal
    especialistas: tuple[EspecialistaAplicado, ...]


async def _planificar(
    reservas: RepositorioReservas,
    cotizador: Cotizador,
    id_reserva: UUID,
    inicio: datetime,
    ahora: datetime,
    bloquear: bool,
) -> _Plan:
    """Las reglas de una reserva nueva para el horario nuevo (franja, anticipacion, cierres y tramo
    libre sin contar la propia reserva) y el precio con las tarifas vigentes (CA-08, CA-09)."""
    contexto = await reservas.contexto_reprogramacion(id_reserva)  # permisos y elegibilidad
    fin = inicio + (contexto.fin - contexto.inicio)
    reglas.exigir_duracion(inicio, fin)
    if bloquear:
        await reservas.bloquear_sala(contexto.id_sala)  # antes de leer franjas, cierres y ocupacion
    minima, maxima = await reservas.limites_reserva()
    reglas.exigir_anticipacion(inicio, calculo.calcular_limites(ahora, minima, maxima))
    fin_buffer = fin + PASO
    franja = reglas.franja_que_contiene(
        inicio, fin_buffer, await reservas.franjas_en(contexto.id_sala, inicio, fin_buffer)
    )
    if await reservas.cierres_en(contexto.id_sala, inicio, fin_buffer):
        raise FueraDeFranja("La sala está cerrada en ese horario.", {"campo": "inicio"})
    if await reservas.ocupacion_excluyendo(contexto.id_sala, inicio, fin_buffer, id_reserva):
        raise TramoNoDisponible("Ese horario ya no está disponible.")
    if contexto.estudio:  # tras una cancelacion del estudio el precio no se recalcula
        return _Plan(franja.id, contexto.precio, contexto.total, ())
    cotizacion: Cotizacion = await cotizador.cotizar(
        contexto.id_sala, contexto.id_servicio, inicio, fin, contexto.id_especialistas
    )
    return _Plan(franja.id, cotizacion.precio, cotizacion.total, cotizacion.especialistas)


class SimularReprogramacion:
    """RF-18 CA-10: la vista previa de reprogramar, sin cambiar nada."""

    def __init__(self, reservas: RepositorioReservas, cotizador: Cotizador) -> None:
        self._reservas = reservas
        self._cotizador = cotizador

    async def ejecutar(
        self, id_reserva: UUID, inicio: datetime, ahora: datetime
    ) -> VistaReprogramacion:
        plan = await _planificar(
            self._reservas, self._cotizador, id_reserva, inicio, ahora, bloquear=False
        )
        return await self._reservas.vista_reprogramacion(
            id_reserva, inicio, plan.total, plan.precio
        )


class ReprogramarReserva:
    """RF-18 CA-08, CA-09, CA-13: una transaccion; la base calcula nivel, saldo y credito."""

    def __init__(self, reservas: RepositorioReservas, cotizador: Cotizador) -> None:
        self._reservas = reservas
        self._cotizador = cotizador

    async def ejecutar(
        self,
        id_reserva: UUID,
        inicio: datetime,
        nivel_esperado: int | None,
        total_esperado: Decimal | None,
        ahora: datetime,
    ) -> Reserva:
        plan = await _planificar(
            self._reservas, self._cotizador, id_reserva, inicio, ahora, bloquear=True
        )
        try:
            await self._reservas.reprogramar_reserva(
                id_reserva,
                inicio,
                nivel_esperado,
                total_esperado,
                plan.id_franja,
                plan.precio,
                plan.total,
                plan.especialistas,
            )
        except (NivelCambiado, PrecioCambiado) as cambio:  # la vista nueva lleva su desglose
            raise type(cambio)(
                cambio.mensaje, {**(cambio.detalles or {}), "precio": plan.precio}
            ) from None
        creada = await self._reservas.obtener_reserva(id_reserva)
        if creada is None:  # no deberia pasar: la acaba de mover su dueno o un administrador
            raise DatosInvalidos("No se pudo leer la reserva.")
        return (await con_clientes(self._reservas, [creada]))[0]
