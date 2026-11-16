"""Pool de PostgreSQL y transaccion con la identidad del usuario (ADR-007)."""

import json
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

from psycopg import AsyncConnection
from psycopg_pool import AsyncConnectionPool


def crear_pool(url: str, timeout: float = 5) -> AsyncConnectionPool:
    return AsyncConnectionPool(url, open=False, min_size=1, max_size=10, timeout=timeout)


@asynccontextmanager
async def transaccion_con_identidad(
    pool: AsyncConnectionPool, claims: dict[str, Any]
) -> AsyncIterator[AsyncConnection]:
    """Abre una transaccion con `authenticated` y los claims; `set local` caduca al cerrarla."""
    async with pool.connection() as conexion, conexion.transaction():
        await conexion.execute("set local role authenticated")
        await conexion.execute(
            "select set_config('request.jwt.claims', %s, true)", (json.dumps(claims),)
        )
        yield conexion


@asynccontextmanager
async def transaccion_publica(pool: AsyncConnectionPool) -> AsyncIterator[AsyncConnection]:
    """Transaccion de un visitante sin sesion: rol `anon`, sin identidad."""
    async with pool.connection() as conexion, conexion.transaction():
        await conexion.execute("set local role anon")
        yield conexion
