from decimal import Decimal
from typing import Any
from uuid import UUID

from psycopg import AsyncConnection, errors

from bugalu.compartido.errores import (
    CreditoInsuficiente,
    CreditoNoVigente,
    CuotaPagada,
    DatosInvalidos,
    DevolucionDecidida,
    DevolucionNoAprobada,
    DevolucionNoPermitida,
    DevolucionPendiente,
    ErrorDeNegocio,
    MontoInvalido,
    MotivoRequerido,
    NoEncontrado,
    NoPagable,
    SinPermiso,
)
from bugalu.modulos.pagos.dominio.modelos import Credito, OrigenCredito
from bugalu.modulos.reservas.dominio.modelos import Devolucion
from bugalu.modulos.reservas.infraestructura.salida.devoluciones_sql import (
    DEVOLUCION,
    devolucion_desde_fila,
)

# Mensaje (= codigo) de las funciones de la base y su error de negocio.
_NEGOCIO: dict[str, tuple[type[ErrorDeNegocio], str]] = {
    "cuota_pagada": (CuotaPagada, "La cuota ya esta pagada."),
    "no_pagable": (NoPagable, "La cuota no se puede pagar ahora."),
    "credito_insuficiente": (CreditoInsuficiente, "El credito disponible no alcanza."),
    "devolucion_no_permitida": (DevolucionNoPermitida, "Ese credito no admite devolucion."),
    "devolucion_pendiente": (DevolucionPendiente, "Ya hay una devolucion pendiente."),
    "credito_no_vigente": (CreditoNoVigente, "El credito ya no esta vigente."),
    "devolucion_decidida": (DevolucionDecidida, "La devolucion ya se decidio."),
    "devolucion_no_aprobada": (DevolucionNoAprobada, "La devolucion no esta aprobada."),
}
_INVALIDOS: dict[str, tuple[type[DatosInvalidos], str, str]] = {
    "monto_invalido": (MontoInvalido, "El monto no es valido.", "monto"),
    "motivo_invalido": (DatosInvalidos, "El motivo debe tener de 10 a 500 caracteres.", "motivo"),
    "motivo_requerido": (MotivoRequerido, "Indica el motivo (de 10 a 500 caracteres).", "motivo"),
    "nota_invalida": (DatosInvalidos, "La nota debe tener de 1 a 500 caracteres.", "nota"),
    "decision_invalida": (DatosInvalidos, "La decision es total, parcial o rechazo.", "decision"),
}
_CREDITO = (
    "select k.id, k.monto, k.saldo, k.vence, "
    "case when k.estado = 'vigente' and k.vence <= now() and not k.congelado "
    "then 'vencido' else k.estado end, k.tipo, k.id_reserva, r.folio "
    "from public.credito k join public.reserva r on r.id = k.id_reserva "
)


def _traducir(error: Exception) -> ErrorDeNegocio:
    codigo = getattr(getattr(error, "diag", None), "message_primary", None) or ""
    if isinstance(error, errors.NoDataFound):
        return NoEncontrado("No existe el recurso.")
    if isinstance(error, errors.InsufficientPrivilege):
        return SinPermiso("No tienes permiso para esa accion.")
    if codigo in _INVALIDOS:
        clase, mensaje, campo = _INVALIDOS[codigo]
        return clase(mensaje, {"campo": campo})
    if codigo in _NEGOCIO:
        clase_negocio, mensaje = _NEGOCIO[codigo]
        return clase_negocio(mensaje)
    return DatosInvalidos("Datos invalidos.")


class RepositorioCreditosPostgres:
    """Recibe una transaccion con identidad: la RLS decide el acceso."""

    def __init__(self, conexion: AsyncConnection) -> None:
        self._conexion = conexion

    async def _filas(self, consulta: str, parametros: tuple[Any, ...] = ()) -> list[Any]:
        cursor = await self._conexion.execute(consulta, parametros)
        return await cursor.fetchall()

    async def _llamar(self, consulta: str, parametros: tuple[Any, ...]) -> list[Any]:
        try:
            return await self._filas(consulta, parametros)
        except (
            errors.NoDataFound,
            errors.InsufficientPrivilege,
            errors.RaiseException,
            errors.InvalidParameterValue,
        ) as e:
            raise _traducir(e) from None

    async def es_administrador(self) -> bool:
        return bool((await self._filas("select public.es_administrador()"))[0][0])

    async def es_personal(self) -> bool:
        return bool((await self._filas("select public.es_personal()"))[0][0])

    async def listar_creditos(self, id_cliente: UUID) -> list[Credito]:
        filas = await self._filas(
            f"{_CREDITO}where k.id_cliente = %s order by "
            "(case when k.estado = 'vigente' and k.vence > now() then 0 else 1 end), k.vence, k.id",
            (id_cliente,),
        )
        ids = [f[0] for f in filas]
        devoluciones: dict[UUID, Devolucion] = {}
        if ids:
            for f in await self._filas(
                f"{DEVOLUCION}where d.id_credito = any(%s) order by d.solicitada_en, d.id", (ids,)
            ):
                devoluciones[f[1]] = devolucion_desde_fila(f)  # la ultima de cada credito
        return [
            Credito(
                f[0],
                f[1],
                f[2],
                f[3],
                f[4],
                f[5],
                OrigenCredito(f[6], f[7]),
                devoluciones.get(f[0]),
            )
            for f in filas
        ]

    async def aplicar_credito(
        self, id_cuota: UUID, monto: Decimal, id_credito: UUID | None
    ) -> UUID:
        await self._llamar(
            "select public.aplicar_credito(%s, %s, %s)", (id_cuota, monto, id_credito)
        )
        filas = await self._filas("select id_reserva from public.cuota where id = %s", (id_cuota,))
        id_reserva: UUID = filas[0][0]
        return id_reserva

    async def solicitar_devolucion(self, id_credito: UUID, motivo: str) -> UUID:
        filas = await self._llamar(
            "select public.solicitar_devolucion(%s, %s)", (id_credito, motivo)
        )
        id_devolucion: UUID = filas[0][0]
        return id_devolucion

    async def obtener_devolucion(self, id_devolucion: UUID) -> Devolucion | None:
        filas = await self._filas(f"{DEVOLUCION}where d.id = %s", (id_devolucion,))
        return devolucion_desde_fila(filas[0]) if filas else None

    async def listar_devoluciones(self, estado: str) -> list[Devolucion]:
        orden = "d.solicitada_en, d.id" if estado == "pendiente" else "d.decidida_en desc, d.id"
        filas = await self._filas(f"{DEVOLUCION}where d.estado = %s order by {orden}", (estado,))
        return [devolucion_desde_fila(f) for f in filas]

    async def decidir_devolucion(
        self, id_devolucion: UUID, decision: str, monto: Decimal | None, motivo: str | None
    ) -> None:
        await self._llamar(
            "select public.decidir_devolucion(%s, %s, %s, %s)",
            (id_devolucion, decision, monto, motivo),
        )

    async def marcar_devolucion_realizada(self, id_devolucion: UUID, nota: str) -> None:
        await self._llamar(
            "select public.marcar_devolucion_realizada(%s, %s)", (id_devolucion, nota)
        )
