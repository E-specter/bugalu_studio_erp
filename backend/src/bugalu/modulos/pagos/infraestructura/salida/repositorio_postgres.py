from decimal import Decimal
from typing import Any
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
    PagoYaValidado,
    SinPermiso,
)
from bugalu.modulos.pagos.dominio.instrucciones import METODOS, Instruccion
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
    "pago_ya_validado": (PagoYaValidado, "El pago ya fue validado."),
}
_INDICES = {
    "comprobante_pago_pendiente_uq": "pago_en_validacion",
    "comprobante_pago_operacion_uq": "operacion_duplicada",
}
_PAGO = (
    "select p.id, p.estado, p.metodo, p.monto, p.numero_operacion, p.motivo_rechazo, "
    "p.registrado_en, p.validado_en, p.ruta_captura, p.tipo_captura, c.id, c.hito, c.monto, "
    "r.id, r.folio, r.inicio, r.estado, p.id_cliente, u.nombre, "
    "r.parametros_aplicados->>'porcentaje_igv' "
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
        # RF-17: la version vigente de las condiciones queda ligada al pago (sin cliente).
        await self._conexion.execute(
            "select public.aceptar_condiciones('pago', %s, null)", (nuevo.id,)
        )

    @staticmethod
    def _pago(fila: tuple[Any, ...], cliente: ClienteResumen | None) -> Pago:
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
            ReservaResumen(fila[13], fila[14], fila[15], fila[16], Decimal(fila[19])),
            cliente,
        )

    async def obtener_pago(self, id_pago: UUID) -> Pago | None:
        cursor = await self._conexion.execute(f"{_PAGO}where p.id = %s", (id_pago,))
        fila = await cursor.fetchone()
        if fila is None:
            return None
        cliente = ClienteResumen(fila[17], fila[18]) if await self.es_administrador() else None
        return self._pago(fila, cliente)

    async def listar_pagos(self, estado: str) -> list[Pago]:
        orden = (
            "p.registrado_en, p.id"
            if estado == "pendiente_validacion"
            else "p.validado_en desc, p.id"
        )
        cursor = await self._conexion.execute(
            f"{_PAGO}where p.estado = %s order by {orden}", (estado,)
        )
        return [self._pago(f, ClienteResumen(f[17], f[18])) for f in await cursor.fetchall()]

    async def _validar(self, consulta: str, parametros: tuple[Any, ...]) -> None:
        try:
            await self._conexion.execute(consulta, parametros)
        except errors.RaiseException as error:
            clase, mensaje = _NEGOCIO.get(error.diag.message_primary or "", (None, ""))
            if clase is None:
                raise
            raise clase(mensaje) from None
        except errors.InsufficientPrivilege:
            raise SinPermiso("Solo el administrador valida pagos.") from None
        except errors.NoDataFound:
            raise NoEncontrado("No existe el pago.") from None
        except errors.InvalidParameterValue:
            raise DatosInvalidos(
                "El motivo debe tener de 1 a 300 caracteres.", {"campo": "motivo"}
            ) from None

    async def aprobar_pago(self, id_pago: UUID) -> None:
        await self._validar("select public.aprobar_pago(%s)", (id_pago,))

    async def rechazar_pago(self, id_pago: UUID, motivo: str) -> None:
        await self._validar("select public.rechazar_pago(%s, %s)", (id_pago, motivo))

    async def existe_pago(self, id_pago: UUID) -> bool:
        cursor = await self._conexion.execute("select public.existe_pago(%s)", (id_pago,))
        return bool((await cursor.fetchone())[0])  # type: ignore[index]

    async def listar_instrucciones(self) -> list[Instruccion]:
        cursor = await self._conexion.execute(
            "select metodo, texto, activo from public.instruccion_pago"
        )
        filas = [Instruccion(*f) for f in await cursor.fetchall()]
        return sorted(filas, key=lambda i: METODOS.index(i.metodo))

    async def guardar_instrucciones(self, instrucciones: list[Instruccion]) -> None:
        for i in instrucciones:
            await self._conexion.execute(
                "update public.instruccion_pago set texto = %s, activo = %s where metodo = %s",
                (i.texto, i.activo, i.metodo),
            )

    async def obtener_contacto(self) -> str:
        cursor = await self._conexion.execute("select texto from public.contacto_estudio")
        return str((await cursor.fetchone())[0])  # type: ignore[index]

    async def guardar_contacto(self, texto: str) -> None:
        await self._conexion.execute("update public.contacto_estudio set texto = %s", (texto,))
