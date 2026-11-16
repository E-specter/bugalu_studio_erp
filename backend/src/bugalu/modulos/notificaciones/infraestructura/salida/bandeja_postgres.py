from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from uuid import UUID

from psycopg import AsyncConnection
from psycopg_pool import AsyncConnectionPool

from bugalu.modulos.notificaciones.dominio.puertos import Pendiente


class LotePostgres:
    def __init__(self, conexion: AsyncConnection, pendientes: list[Pendiente]) -> None:
        self._conexion = conexion
        self.pendientes = pendientes

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
                "select id, tipo, destinatario, datos, intentos from public.notificacion "
                "where enviada_en is null and intentos < %s order by creada_en "
                "limit %s for update skip locked",
                (max_intentos, limite),
            )
            yield LotePostgres(conexion, [Pendiente(*fila) for fila in await cursor.fetchall()])
