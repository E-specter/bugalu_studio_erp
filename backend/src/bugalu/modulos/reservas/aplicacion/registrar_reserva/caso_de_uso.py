from collections.abc import Sequence
from datetime import datetime
from uuid import UUID

from bugalu.compartido.errores import DatosInvalidos, EnsayoNoDisponible, FueraDeFranja
from bugalu.compartido.plazos import calcular_vence_pago
from bugalu.modulos.reservas.aplicacion.clientes import con_clientes
from bugalu.modulos.reservas.dominio import disponibilidad as calculo
from bugalu.modulos.reservas.dominio import reserva as reglas
from bugalu.modulos.reservas.dominio.disponibilidad import PASO
from bugalu.modulos.reservas.dominio.modelos import NuevaReserva, Reserva
from bugalu.modulos.reservas.dominio.puertos import Cotizador, RepositorioReservas


class RegistrarReserva:
    def __init__(self, reservas: RepositorioReservas, cotizador: Cotizador) -> None:
        self._reservas = reservas
        self._cotizador = cotizador

    async def ejecutar(
        self,
        id_sala: UUID,
        id_servicio: UUID,
        inicio: datetime,
        fin: datetime,
        id_especialistas: Sequence[UUID],
        detalle: str | None,
        ahora: datetime,
    ) -> Reserva:
        reglas.exigir_duracion(inicio, fin)
        await self._reservas.bloquear_sala(id_sala)  # antes de leer franjas, cierres y ocupacion
        cotizacion = await self._cotizador.cotizar(
            id_sala, id_servicio, inicio, fin, id_especialistas
        )  # valida sala, servicio y especialistas
        if cotizacion.categoria == "ensayo" and not await self._reservas.tiene_servicio_previo():
            raise EnsayoNoDisponible("El ensayo se reserva tras un servicio confirmado.")
        minima, maxima = await self._reservas.limites_reserva()
        reglas.exigir_anticipacion(inicio, calculo.calcular_limites(ahora, minima, maxima))
        fin_buffer = fin + PASO
        franjas = await self._reservas.franjas_en(id_sala, inicio, fin_buffer)
        franja = reglas.franja_que_contiene(inicio, fin_buffer, franjas)
        if await self._reservas.cierres_en(id_sala, inicio, fin_buffer):
            raise FueraDeFranja("La sala está cerrada en ese horario.", {"campo": "inicio"})
        dias, horas = await self._reservas.plazos_pago()
        id_reserva = await self._reservas.insertar_reserva(
            NuevaReserva(
                id_sala,
                id_servicio,
                franja.id,
                inicio,
                fin,
                detalle,
                calcular_vence_pago(ahora, inicio, dias, horas),
                cotizacion,
                tuple(reglas.cuotas_de(cotizacion.total, cotizacion.anticipo)),
            )
        )
        await self._reservas.encolar_aviso_reserva(id_reserva)
        creada = await self._reservas.obtener_reserva(id_reserva)
        if creada is None:  # no deberia pasar: la acaba de insertar el propio usuario
            raise DatosInvalidos("No se pudo leer la reserva creada.")
        return (await con_clientes(self._reservas, [creada]))[0]
