from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from bugalu.compartido.errores import DatosInvalidos
from bugalu.modulos.catalogo.dominio.precio import (
    ConfiguracionImpuestos,
    Especialista,
    Servicio,
    Simulacion,
    bloques_del_tramo,
    calcular_simulacion,
    combinar_especialistas,
)
from bugalu.modulos.catalogo.dominio.puertos import RepositorioCatalogo


@dataclass(frozen=True)
class Cotizacion:
    """Lo que una reserva necesita guardar: el servicio, los especialistas aplicados y el precio."""

    servicio: Servicio
    especialistas: tuple[Especialista, ...]
    simulacion: Simulacion
    parametros_aplicados: dict[str, Any]  # los mismos con los que se calculo el precio


class SimularPrecio:
    """Misma funcion de precio que usara la reserva (RN-15); no escribe nada."""

    def __init__(self, catalogo: RepositorioCatalogo) -> None:
        self._catalogo = catalogo

    async def ejecutar(
        self,
        id_sala: UUID,
        id_servicio: UUID,
        inicio: datetime,
        fin: datetime,
        id_especialistas: Sequence[UUID],
    ) -> Simulacion:
        return (await self.cotizar(id_sala, id_servicio, inicio, fin, id_especialistas)).simulacion

    async def cotizar(
        self,
        id_sala: UUID,
        id_servicio: UUID,
        inicio: datetime,
        fin: datetime,
        id_especialistas: Sequence[UUID],
    ) -> Cotizacion:
        if not await self._catalogo.existe_sala(id_sala):
            raise DatosInvalidos("La sala no existe.")
        servicio = await self._catalogo.obtener_servicio(id_servicio)
        if servicio is None:
            raise DatosInvalidos("El servicio no existe.")
        elegidos = list(dict.fromkeys(id_especialistas))
        conocidos = {
            e.id: e
            for e in await self._catalogo.obtener_especialistas(
                {*servicio.especialistas_por_defecto, *elegidos}
            )
        }
        if any(i not in conocidos or not conocidos[i].activo for i in elegidos):
            raise DatosInvalidos("Algun especialista no existe o no esta disponible.")
        por_defecto = [
            conocidos[i] for i in servicio.especialistas_por_defecto if conocidos[i].activo
        ]
        fechas = {b.date() for b in bloques_del_tramo(inicio, fin)}  # valida el tramo
        extra = [conocidos[i] for i in elegidos]
        vigentes = (
            await self._catalogo.parametros_vigentes()
        )  # una lectura: precio y reserva coinciden
        simulacion = calcular_simulacion(
            servicio,
            por_defecto,
            extra,
            inicio,
            fin,
            await self._catalogo.obtener_recargos(),
            await self._catalogo.feriados_en(fechas),
            ConfiguracionImpuestos(
                Decimal(vigentes["porcentaje_igv"]), vigentes["precios_incluyen_igv"]
            ),
            vigentes["porcentaje_adelanto"],
        )
        return Cotizacion(
            servicio, tuple(combinar_especialistas(por_defecto, extra)), simulacion, vigentes
        )
