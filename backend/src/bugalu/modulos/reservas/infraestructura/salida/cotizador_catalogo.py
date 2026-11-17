from collections.abc import Sequence
from datetime import datetime
from typing import Any
from uuid import UUID

from psycopg import AsyncConnection

from bugalu.modulos.catalogo.aplicacion.simular_precio.caso_de_uso import SimularPrecio
from bugalu.modulos.catalogo.infraestructura.entrada.http.esquemas import Simulacion
from bugalu.modulos.catalogo.infraestructura.salida.repositorio_postgres import (
    RepositorioCatalogoPostgres,
)
from bugalu.modulos.reservas.dominio.modelos import Cotizacion, EspecialistaAplicado


class CotizadorCatalogo:
    """Adaptador de salida: el motor de precio del catalogo, con la misma transaccion."""

    def __init__(self, conexion: AsyncConnection) -> None:
        self._simular = SimularPrecio(RepositorioCatalogoPostgres(conexion))

    async def cotizar(
        self,
        id_sala: UUID,
        id_servicio: UUID,
        inicio: datetime,
        fin: datetime,
        id_especialistas: Sequence[UUID],
        parametros: dict[str, Any] | None = None,
    ) -> Cotizacion:
        c = await self._simular.cotizar(
            id_sala, id_servicio, inicio, fin, id_especialistas, parametros
        )
        return Cotizacion(
            categoria=c.servicio.categoria,
            precio=Simulacion.desde_dominio(c.simulacion).model_dump(mode="json"),
            total=c.simulacion.total,
            anticipo=c.simulacion.anticipo,
            especialistas=tuple(
                EspecialistaAplicado(e.id, e.monto_fijo, e.monto_variable, e.unidad.value)
                for e in c.especialistas
            ),
            parametros_aplicados=c.parametros_aplicados,
        )
