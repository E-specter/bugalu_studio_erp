from collections.abc import Sequence
from datetime import datetime
from uuid import UUID

from bugalu.compartido.errores import DatosInvalidos
from bugalu.modulos.catalogo.dominio.precio import (
    Simulacion,
    bloques_del_tramo,
    calcular_simulacion,
)
from bugalu.modulos.catalogo.dominio.puertos import RepositorioCatalogo


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
        return calcular_simulacion(
            servicio,
            por_defecto,
            [conocidos[i] for i in elegidos],
            inicio,
            fin,
            await self._catalogo.obtener_recargos(),
            await self._catalogo.feriados_en(fechas),
        )
