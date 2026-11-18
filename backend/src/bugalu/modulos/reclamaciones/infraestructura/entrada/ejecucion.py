"""Limpieza periodica de adjuntos huerfanos (lifespan de la API o una sola vez)."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from psycopg_pool import AsyncConnectionPool

from bugalu.compartido.configuracion import Configuracion
from bugalu.modulos.reclamaciones.aplicacion.limpiar.caso_de_uso import LimpiarAdjuntosHuerfanos
from bugalu.modulos.reclamaciones.infraestructura.salida.almacen_storage import AlmacenStorage
from bugalu.modulos.reclamaciones.infraestructura.salida.repositorio_postgres import (
    RepositorioHojasPostgres,
)


async def limpiar_una_vez(pool: AsyncConnectionPool, configuracion: Configuracion) -> int:
    @asynccontextmanager
    async def como_api() -> AsyncIterator[RepositorioHojasPostgres]:
        # Rol `bugalu_api` directo, sin `set local role`: es el unico que lista las rutas huerfanas.
        async with pool.connection() as conexion, conexion.transaction():
            yield RepositorioHojasPostgres(conexion)

    almacen = AlmacenStorage(configuracion.url_supabase, configuracion.clave_publicable_supabase)
    return await LimpiarAdjuntosHuerfanos(como_api, almacen).ejecutar()
