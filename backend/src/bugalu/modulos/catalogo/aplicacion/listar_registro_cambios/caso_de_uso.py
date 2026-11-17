from datetime import date, datetime, time, timedelta

from bugalu.compartido.errores import RangoInvalido
from bugalu.modulos.catalogo.aplicacion.permisos import exigir_administrador
from bugalu.modulos.catalogo.dominio.cambios_sensibles import CambioRegistrado
from bugalu.modulos.catalogo.dominio.precio import LIMA
from bugalu.modulos.catalogo.dominio.puertos import RepositorioCambios, RepositorioCatalogo

DIAS_POR_DEFECTO = 30
DIAS_MAXIMOS = 366


class ListarRegistroCambios:
    def __init__(self, catalogo: RepositorioCatalogo, cambios: RepositorioCambios) -> None:
        self._catalogo = catalogo
        self._cambios = cambios

    async def ejecutar(
        self, desde: date | None, hasta: date | None, recurso: str | None, hoy: date
    ) -> list[CambioRegistrado]:
        """Fechas de Lima, ambas incluidas; por defecto, los ultimos 30 dias."""
        await exigir_administrador(self._catalogo)
        hasta = hasta or hoy
        desde = desde or hasta - timedelta(days=DIAS_POR_DEFECTO - 1)
        if not 1 <= (hasta - desde).days + 1 <= DIAS_MAXIMOS:
            raise RangoInvalido(
                f"El rango va de 1 a {DIAS_MAXIMOS} días y la fecha final no puede ser anterior.",
                {"campo": "desde"},
            )
        return await self._cambios.listar(
            datetime.combine(desde, time(0), LIMA),
            datetime.combine(hasta + timedelta(days=1), time(0), LIMA),
            recurso,
        )
