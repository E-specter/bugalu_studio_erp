from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from uuid import UUID

from psycopg import AsyncConnection
from psycopg_pool import AsyncConnectionPool

from bugalu.modulos.notificaciones.dominio.armado import TIPOS_CON_EVENTO
from bugalu.modulos.notificaciones.dominio.puertos import DatosReserva, Pendiente

_CON_DATOS_PARA_PAGAR = ("reserva_creada", "reserva_finalizada_saldo")


class LotePostgres:
    def __init__(
        self,
        conexion: AsyncConnection,
        pendientes: list[Pendiente],
        instrucciones: list[tuple[str, str]],
        reservas: dict[UUID, DatosReserva],
    ) -> None:
        self._conexion = conexion
        self.pendientes = pendientes
        self.instrucciones = instrucciones
        self.reservas = reservas

    async def marcar_enviada(self, id_: UUID) -> None:
        await self._conexion.execute(
            "update public.notificacion set enviada_en = now(), error = null where id = %s", (id_,)
        )

    async def marcar_fallo(self, id_: UUID, error: str) -> None:
        await self._conexion.execute(
            "update public.notificacion set intentos = intentos + 1, error = %s where id = %s",
            (error[:200], id_),
        )


class BandejaPostgres:
    """Rol `bugalu_api` directo, sin `set local role`: es el unico que lee la bandeja (RLS)."""

    def __init__(self, pool: AsyncConnectionPool) -> None:
        self._pool = pool

    @asynccontextmanager
    async def tomar(self, limite: int, max_intentos: int) -> AsyncIterator[LotePostgres]:
        async with self._pool.connection() as conexion, conexion.transaction():
            cursor = await conexion.execute(
                "select id, tipo, destinatario, datos, intentos, creada_en "
                "from public.notificacion "
                "where enviada_en is null and intentos < %s order by creada_en "
                "limit %s for update skip locked",
                (max_intentos, limite),
            )
            pendientes = [Pendiente(*fila) for fila in await cursor.fetchall()]
            instrucciones: list[tuple[str, str]] = []
            if any(p.tipo in _CON_DATOS_PARA_PAGAR for p in pendientes):
                cursor = await conexion.execute(
                    "select metodo, texto from public.instruccion_pago where activo "
                    "order by array_position(array['transferencia', 'yape', 'plin', 'tarjeta'], "
                    "metodo)"
                )
                instrucciones = [(m, t) for m, t in await cursor.fetchall()]
            reservas: dict[UUID, DatosReserva] = {}
            con_evento = [p.id for p in pendientes if p.tipo in TIPOS_CON_EVENTO]
            if con_evento:
                cursor = await conexion.execute(
                    "select * from public.datos_reserva_para_correo(%s)", (con_evento,)
                )
                reservas = {f[0]: DatosReserva(*f[1:]) for f in await cursor.fetchall()}
            yield LotePostgres(conexion, pendientes, instrucciones, reservas)
