from collections.abc import Mapping, Sequence
from datetime import datetime
from typing import Any
from uuid import UUID

from psycopg import AsyncConnection, errors
from psycopg.types.json import Jsonb

from bugalu.compartido.errores import (
    FranjaSolapada,
    NoCancelable,
    NoEncontrado,
    SinPermiso,
    TienePagos,
    TramoNoDisponible,
)
from bugalu.modulos.reservas.dominio.disponibilidad import Tramo
from bugalu.modulos.reservas.dominio.modelos import (
    PARAMETROS,
    Cierre,
    CuotaReserva,
    Franja,
    NuevaReserva,
    Referencia,
    Reserva,
    ReservaVisible,
    Sala,
    ServicioReservado,
)

_TOPE_SUGERENCIA = 300
_RESERVA = (
    "select r.id, r.folio, r.estado, r.motivo_cancelacion, r.inicio, r.fin, r.fin_buffer, "
    "r.precio, r.vence_pago, r.id_cliente, sa.id, sa.nombre, se.id, se.nombre, se.categoria "
    "from public.reserva r join public.sala_tecnica sa on sa.id = r.id_sala "
    "join public.servicio se on se.id = r.id_servicio "
)


class RepositorioReservasPostgres:
    """Recibe una transaccion ya abierta (publica o con identidad): la RLS decide el acceso."""

    def __init__(self, conexion: AsyncConnection) -> None:
        self._conexion = conexion

    async def _filas(self, consulta: str, parametros: Sequence[Any] = ()) -> list[Any]:
        cursor = await self._conexion.execute(consulta, parametros)
        return await cursor.fetchall()

    async def es_administrador(self) -> bool:
        return bool((await self._filas("select public.es_administrador()"))[0][0])

    async def es_personal(self) -> bool:
        return bool((await self._filas("select public.es_personal()"))[0][0])

    async def listar_salas(self) -> list[Sala]:
        filas = await self._filas(
            "select id, nombre, sede from public.sala_tecnica where activa order by sede, nombre"
        )
        return [Sala(*f) for f in filas]

    async def existe_sala(self, id_sala: UUID) -> bool:
        filas = await self._filas(
            "select 1 from public.sala_tecnica where id = %s and activa", (id_sala,)
        )
        return bool(filas)

    async def limites_reserva(self) -> tuple[int, int]:
        minima, maxima = (await self._filas("select * from public.limites_reserva()"))[0]
        return int(minima), int(maxima)

    async def franjas_en(self, id_sala: UUID, desde: datetime, hasta: datetime) -> list[Franja]:
        filas = await self._filas(
            "select id, id_sala, inicio, fin from public.franja_sala "
            "where id_sala = %s and inicio < %s and fin > %s order by inicio",
            (id_sala, hasta, desde),
        )
        return [Franja(*f) for f in filas]

    async def franjas_antes_de(self, id_sala: UUID, instante: datetime) -> list[Franja]:
        filas = await self._filas(
            "select id, id_sala, inicio, fin from public.franja_sala "
            "where id_sala = %s and inicio < %s order by inicio desc limit %s",
            (id_sala, instante, _TOPE_SUGERENCIA),
        )
        return [Franja(*f) for f in filas]

    async def cierres_en(self, id_sala: UUID, desde: datetime, hasta: datetime) -> list[Cierre]:
        filas = await self._filas(
            "select id, id_sala, inicio, fin, motivo from public.cierre_sala "
            "where id_sala = %s and inicio < %s and fin > %s order by inicio",
            (id_sala, hasta, desde),
        )
        return [Cierre(*f) for f in filas]

    async def ocupacion(self, id_sala: UUID, desde: datetime, hasta: datetime) -> list[Tramo]:
        filas = await self._filas(
            "select inicio, fin_buffer from public.ocupacion_sala(%s, %s, %s)",
            (id_sala, desde, hasta),
        )
        return [Tramo(*f) for f in filas]

    async def reservas_visibles(
        self, id_sala: UUID, desde: datetime, hasta: datetime
    ) -> list[ReservaVisible]:
        filas = await self._filas(
            "select r.id, r.folio, r.id_cliente, s.nombre, r.estado, r.inicio, r.fin_buffer "
            "from public.reserva r join public.servicio s on s.id = r.id_servicio "
            "where r.id_sala = %s and r.estado <> 'cancelada' "
            "and r.inicio < %s and r.fin_buffer > %s order by r.inicio",
            (id_sala, hasta, desde),
        )
        return [ReservaVisible(*f) for f in filas]

    async def nombres_de_clientes(self, ids: Sequence[UUID]) -> Mapping[UUID, str | None]:
        if not ids:
            return {}
        filas = await self._filas(
            "select id, nombre from public.nombres_de_clientes(%s)", (list(ids),)
        )
        return {f[0]: f[1] for f in filas}

    async def insertar_franjas(self, id_sala: UUID, tramos: Sequence[Tramo]) -> list[Franja]:
        nuevas = []
        for tramo in tramos:
            try:
                filas = await self._filas(
                    "insert into public.franja_sala (id_sala, inicio, fin, id_publicador) "
                    "values (%s, %s, %s, (select auth.uid())) "
                    "returning id, id_sala, inicio, fin",
                    (id_sala, tramo.inicio, tramo.fin),
                )
            except errors.ExclusionViolation:
                raise FranjaSolapada("La franja se solapa con otra de la sala.") from None
            nuevas.append(Franja(*filas[0]))
        return nuevas

    async def bloquear_sala(self, id_sala: UUID) -> None:
        # Bloqueo hasta el fin de la transaccion; todas las lecturas del caso de uso van despues.
        await self._conexion.execute(
            "select pg_advisory_xact_lock(hashtextextended(%s, 0))", (str(id_sala),)
        )

    async def obtener_franja(self, id_franja: UUID) -> Franja | None:
        filas = await self._filas(
            "select id, id_sala, inicio, fin from public.franja_sala where id = %s", (id_franja,)
        )
        return Franja(*filas[0]) if filas else None

    async def eliminar_franja(self, id_franja: UUID) -> None:
        await self._conexion.execute("delete from public.franja_sala where id = %s", (id_franja,))

    async def insertar_cierre(self, id_sala: UUID, tramo: Tramo, motivo: str) -> Cierre:
        filas = await self._filas(
            "insert into public.cierre_sala (id_sala, inicio, fin, motivo, id_autor) "
            "values (%s, %s, %s, %s, (select auth.uid())) "
            "returning id, id_sala, inicio, fin, motivo",
            (id_sala, tramo.inicio, tramo.fin, motivo),
        )
        return Cierre(*filas[0])

    async def obtener_cierre(self, id_cierre: UUID) -> Cierre | None:
        filas = await self._filas(
            "select id, id_sala, inicio, fin, motivo from public.cierre_sala where id = %s",
            (id_cierre,),
        )
        return Cierre(*filas[0]) if filas else None

    async def eliminar_cierre(self, id_cierre: UUID) -> None:
        await self._conexion.execute("delete from public.cierre_sala where id = %s", (id_cierre,))

    async def obtener_parametros(self) -> dict[str, int]:
        filas = await self._filas("select clave, valor from public.parametro")
        return {clave: int(valor) for clave, valor in filas}

    async def guardar_parametros(self, cambios: Mapping[str, int]) -> None:
        for clave, valor in cambios.items():
            if clave not in PARAMETROS:
                raise ValueError("Parametro desconocido.")
            await self._conexion.execute(
                "update public.parametro set valor = %s where clave = %s", (valor, clave)
            )

    async def plazos_pago(self) -> tuple[int, int]:
        dias, horas = (await self._filas("select * from public.plazos_pago()"))[0]
        return int(dias), int(horas)

    async def tiene_servicio_previo(self) -> bool:
        filas = await self._filas(
            "select exists (select 1 from public.reserva r "
            "join public.servicio s on s.id = r.id_servicio "
            "where r.id_cliente = (select auth.uid()) "
            "and r.estado in ('confirmada', 'en_curso', 'finalizada') and s.categoria <> 'ensayo')"
        )
        return bool(filas[0][0])

    async def insertar_reserva(self, nueva: NuevaReserva) -> UUID:
        try:
            filas = await self._filas(
                "insert into public.reserva (id_cliente, id_sala, id_servicio, id_franja, inicio, "
                "fin, precio, total, vence_pago, detalle) "
                "values ((select auth.uid()), %s, %s, %s, %s, %s, %s, %s, %s, %s) returning id",
                (
                    nueva.id_sala,
                    nueva.id_servicio,
                    nueva.id_franja,
                    nueva.inicio,
                    nueva.fin,
                    Jsonb(nueva.cotizacion.precio),
                    nueva.cotizacion.total,
                    nueva.vence_pago,
                    nueva.detalle,
                ),
            )
        except errors.ExclusionViolation:  # RN-01: la base es quien decide el solape
            raise TramoNoDisponible("Ese horario ya no está disponible.") from None
        id_reserva: UUID = filas[0][0]
        for e in nueva.cotizacion.especialistas:
            await self._conexion.execute(
                "insert into public.reserva_especialista "
                "(id_reserva, id_especialista, monto_fijo, monto_variable, unidad) "
                "values (%s, %s, %s, %s, %s)",
                (id_reserva, e.id, e.monto_fijo, e.monto_variable, e.unidad),
            )
        for hito, monto in nueva.cuotas:
            await self._conexion.execute(
                "insert into public.cuota (id_reserva, hito, monto) values (%s, %s, %s)",
                (id_reserva, hito, monto),
            )
        return id_reserva

    async def encolar_aviso_reserva(self, id_reserva: UUID) -> None:
        await self._conexion.execute("select public.encolar_aviso_reserva(%s)", (id_reserva,))

    async def _reservas(self, condicion: str, parametros: Sequence[Any]) -> list[Reserva]:
        filas = await self._filas(
            f"{_RESERVA} where {condicion} order by r.inicio, r.folio", parametros
        )
        ids = [f[0] for f in filas]
        cuotas: dict[UUID, list[CuotaReserva]] = {}
        especialistas: dict[UUID, list[Referencia]] = {}
        if ids:
            for f in await self._filas(
                "select id, id_reserva, hito, monto, estado from public.cuota "
                "where id_reserva = any(%s) order by hito",
                (ids,),
            ):
                cuotas.setdefault(f[1], []).append(CuotaReserva(f[0], f[2], f[3], f[4]))
            for f in await self._filas(
                "select re.id_reserva, e.id, e.nombre from public.reserva_especialista re "
                "join public.especialista e on e.id = re.id_especialista "
                "where re.id_reserva = any(%s) order by e.nombre",
                (ids,),
            ):
                especialistas.setdefault(f[0], []).append(Referencia(f[1], f[2]))
        return [
            Reserva(
                id=f[0],
                folio=f[1],
                estado=f[2],
                motivo_cancelacion=f[3],
                inicio=f[4],
                fin=f[5],
                fin_buffer=f[6],
                precio=f[7],
                vence_pago=f[8],
                id_cliente=f[9],
                sala=Referencia(f[10], f[11]),
                servicio=ServicioReservado(f[12], f[13], f[14]),
                especialistas=tuple(especialistas.get(f[0], [])),
                cuotas=tuple(cuotas.get(f[0], [])),
            )
            for f in filas
        ]

    async def obtener_reserva(self, id_reserva: UUID) -> Reserva | None:
        encontradas = await self._reservas("r.id = %s", (id_reserva,))
        return encontradas[0] if encontradas else None

    async def existe_reserva(self, id_reserva: UUID) -> bool:
        return bool((await self._filas("select public.existe_reserva(%s)", (id_reserva,)))[0][0])

    async def listar_mias(self) -> list[Reserva]:
        return await self._reservas("r.id_cliente = (select auth.uid())", ())

    async def listar_en_rango(self, desde: datetime, hasta: datetime) -> list[Reserva]:
        return await self._reservas("r.inicio < %s and r.fin_buffer > %s", (hasta, desde))

    async def cancelar_reserva(self, id_reserva: UUID) -> None:
        try:
            await self._conexion.execute("select public.cancelar_reserva(%s)", (id_reserva,))
        except errors.NoDataFound:
            raise NoEncontrado("No existe la reserva.") from None
        except errors.InsufficientPrivilege:
            raise SinPermiso("Esa reserva no es tuya.") from None
        except errors.RaiseException as error:
            if error.diag.message_primary == "tiene_pagos":
                raise TienePagos("La reserva ya tiene pagos registrados.") from None
            raise NoCancelable("La reserva ya no se puede cancelar.") from None
