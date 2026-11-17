from decimal import Decimal
from uuid import UUID

from bugalu.compartido.errores import DatosInvalidos, NoEncontrado, SinPermiso
from bugalu.modulos.pagos.dominio.modelos import Credito
from bugalu.modulos.pagos.dominio.puertos import RepositorioCreditos
from bugalu.modulos.reservas.dominio.modelos import Devolucion, Reserva
from bugalu.modulos.reservas.dominio.puertos import RepositorioReservas


async def _exigir_administrador(creditos: RepositorioCreditos) -> None:
    if not await creditos.es_administrador():
        raise SinPermiso("Solo un administrador puede hacer esto.")


class ListarCreditos:
    """Cada cliente ve los suyos; el administrador los de `id_cliente`; el personal ninguno."""

    def __init__(self, creditos: RepositorioCreditos) -> None:
        self._creditos = creditos

    async def ejecutar(self, id_usuario: UUID, id_cliente: UUID | None) -> list[Credito]:
        if await self._creditos.es_administrador():
            if id_cliente is None:
                raise DatosInvalidos("Indica el cliente.", {"campo": "id_cliente"})
            return await self._creditos.listar_creditos(id_cliente)
        if await self._creditos.es_personal() or id_cliente not in (None, id_usuario):
            raise SinPermiso("Solo ves tus propios creditos.")
        return await self._creditos.listar_creditos(id_usuario)


class AplicarCredito:
    """CA-06: aplica credito a una cuota propia y devuelve la reserva ya actualizada."""

    def __init__(self, creditos: RepositorioCreditos, reservas: RepositorioReservas) -> None:
        self._creditos = creditos
        self._reservas = reservas

    async def ejecutar(self, id_cuota: UUID, monto: Decimal, id_credito: UUID | None) -> Reserva:
        id_reserva = await self._creditos.aplicar_credito(id_cuota, monto, id_credito)
        reserva = await self._reservas.obtener_reserva(id_reserva)
        if reserva is None:
            raise NoEncontrado("No existe la reserva.")
        return reserva


async def devolucion_visible(creditos: RepositorioCreditos, id_devolucion: UUID) -> Devolucion:
    """El dueno y el administrador la ven; el personal recibe 403; los demas, 404 (RLS)."""
    devolucion = await creditos.obtener_devolucion(id_devolucion)
    if devolucion is None:
        if await creditos.es_personal():
            raise SinPermiso("Solo el administrador ve las devoluciones.")
        raise NoEncontrado("No existe la devolucion.")
    return devolucion


class SolicitarDevolucion:
    def __init__(self, creditos: RepositorioCreditos) -> None:
        self._creditos = creditos

    async def ejecutar(self, id_credito: UUID, motivo: str) -> Devolucion:
        id_devolucion = await self._creditos.solicitar_devolucion(id_credito, motivo)
        return await devolucion_visible(self._creditos, id_devolucion)


class ObtenerDevolucion:
    def __init__(self, creditos: RepositorioCreditos) -> None:
        self._creditos = creditos

    async def ejecutar(self, id_devolucion: UUID) -> Devolucion:
        return await devolucion_visible(self._creditos, id_devolucion)


class ListarDevoluciones:
    def __init__(self, creditos: RepositorioCreditos) -> None:
        self._creditos = creditos

    async def ejecutar(self, estado: str) -> list[Devolucion]:
        await _exigir_administrador(self._creditos)
        return await self._creditos.listar_devoluciones(estado)


class DecidirDevolucion:
    def __init__(self, creditos: RepositorioCreditos) -> None:
        self._creditos = creditos

    async def ejecutar(
        self, id_devolucion: UUID, decision: str, monto: Decimal | None, motivo: str | None
    ) -> Devolucion:
        await self._creditos.decidir_devolucion(id_devolucion, decision, monto, motivo)
        return await devolucion_visible(self._creditos, id_devolucion)


class MarcarDevolucionRealizada:
    def __init__(self, creditos: RepositorioCreditos) -> None:
        self._creditos = creditos

    async def ejecutar(self, id_devolucion: UUID, nota: str) -> Devolucion:
        await self._creditos.marcar_devolucion_realizada(id_devolucion, nota)
        return await devolucion_visible(self._creditos, id_devolucion)
