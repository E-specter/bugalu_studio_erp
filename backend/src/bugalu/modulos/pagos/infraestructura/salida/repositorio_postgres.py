from uuid import UUID

from psycopg import AsyncConnection, errors

from bugalu.compartido.errores import (
    CuotaNoPagable,
    CuotaPagada,
    DatosInvalidos,
    MetodoNoDisponible,
    NoEncontrado,
    OperacionDuplicada,
    PagoEnValidacion,
    SinPermiso,
)
from bugalu.modulos.pagos.dominio.modelos import (
    ClienteResumen,
    CuotaResumen,
    NuevoPago,
    Pago,
    ReservaResumen,
)

# P0001 de `validar_pago_nuevo` (mensaje = codigo) y, como ultima barrera, los indices unicos.
_NEGOCIO = {
    "cuota_pagada": (CuotaPagada, "La cuota ya esta pagada."),
    "pago_en_validacion": (PagoEnValidacion, "La cuota ya tiene un pago en validacion."),
    "cuota_no_pagable": (CuotaNoPagable, "La cuota no se puede pagar ahora."),
    "metodo_no_disponible": (MetodoNoDisponible, "Ese metodo de pago no esta disponible."),
    "operacion_duplicada": (OperacionDuplicada, "Ese numero de operacion ya esta registrado."),
}
_INDICES = {
    "comprobante_pago_pendiente_uq": "pago_en_validacion",
    "comprobante_pago_operacion_uq": "operacion_duplicada",
}
_PAGO = (
    "select p.id, p.estado, p.metodo, p.monto, p.numero_operacion, p.motivo_rechazo, "
    "p.registrado_en, p.validado_en, p.ruta_captura, p.tipo_captura, c.id, c.hito, c.monto, "
    "r.id, r.folio, r.inicio, r.estado, p.id_cliente, u.nombre "
    "from public.comprobante_pago p join public.cuota c on c.id = p.id_cuota "
    "join public.reserva r on r.id = c.id_reserva "
    "left join public.usuario u on u.id = p.id_cliente "
)


class RepositorioPagosPostgres:
    """Recibe una transaccion con identidad: la RLS decide el acceso."""

    def __init__(self, conexion: AsyncConnection) -> None:
        self._conexion = conexion

    async def es_administrador(self) -> bool:
        cursor = await self._conexion.execute("select public.es_administrador()")
        return bool((await cursor.fetchone())[0])  # type: ignore[index]

    async def insertar_pago(self, nuevo: NuevoPago) -> None:
        try:
            await self._conexion.execute(
                "insert into public.comprobante_pago (id, id_cuota, id_cliente, metodo, monto, "
                "numero_operacion, ruta_captura, tipo_captura) "
                "values (%s, %s, %s, %s, %s, %s, %s, %s)",
                (
                    nuevo.id,
                    nuevo.id_cuota,
                    nuevo.id_cliente,
                    nuevo.metodo,
                    nuevo.monto,
                    nuevo.numero_operacion,
                    nuevo.ruta_captura,
                    nuevo.tipo_captura,
                ),
            )
        except errors.RaiseException as error:
            clase, mensaje = _NEGOCIO.get(error.diag.message_primary or "", (None, ""))
            if clase is None:
                raise
            raise clase(mensaje) from None
        except errors.UniqueViolation as error:
            codigo = _INDICES.get(error.diag.constraint_name or "")
            if codigo is None:
                raise
            clase, mensaje = _NEGOCIO[codigo]
            raise clase(mensaje) from None
        except errors.InsufficientPrivilege:
            raise SinPermiso("Esa cuota no es tuya.") from None
        except errors.NoDataFound:
            raise NoEncontrado("No existe la cuota.") from None
        except errors.CheckViolation:
            raise DatosInvalidos("Datos invalidos.") from None

    async def obtener_pago(self, id_pago: UUID) -> Pago | None:
        cursor = await self._conexion.execute(f"{_PAGO}where p.id = %s", (id_pago,))
        fila = await cursor.fetchone()
        if fila is None:
            return None
        cliente = ClienteResumen(fila[17], fila[18]) if await self.es_administrador() else None
        (id_, estado, metodo, monto, operacion, motivo, registrado, validado, ruta, tipo) = fila[
            :10
        ]
        return Pago(
            id_,
            estado,
            metodo,
            monto,
            operacion,
            motivo,
            registrado,
            validado,
            ruta,
            tipo,
            CuotaResumen(*fila[10:13]),
            ReservaResumen(*fila[13:17]),
            cliente,
        )

    async def existe_pago(self, id_pago: UUID) -> bool:
        cursor = await self._conexion.execute("select public.existe_pago(%s)", (id_pago,))
        return bool((await cursor.fetchone())[0])  # type: ignore[index]
