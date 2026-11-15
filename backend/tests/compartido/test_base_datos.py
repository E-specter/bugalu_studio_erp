from collections.abc import Callable

import pytest
from psycopg_pool import AsyncConnectionPool

from bugalu.compartido.base_datos import transaccion_con_identidad
from tests.conftest import UsuarioDePrueba

pytestmark = pytest.mark.integracion

A = "00000000-0000-0000-0000-00000000000a"
B = "00000000-0000-0000-0000-00000000000b"


async def _quien(pool: AsyncConnectionPool, sub: str) -> tuple[str, str, int]:
    async with transaccion_con_identidad(pool, {"sub": sub, "role": "authenticated"}) as conexion:
        cursor = await conexion.execute("select auth.uid()::text, current_user, pg_backend_pid()")
        fila = await cursor.fetchone()
        assert fila is not None
        return fila


async def test_la_transaccion_asume_la_identidad_del_usuario(pool: AsyncConnectionPool) -> None:
    uid, rol, _ = await _quien(pool, A)
    assert (uid, rol) == (A, "authenticated")


async def test_la_identidad_no_se_filtra_entre_transacciones_en_la_misma_conexion(
    pool: AsyncConnectionPool,
) -> None:
    uid_a, _, pid_a = await _quien(pool, A)
    uid_b, _, pid_b = await _quien(pool, B)
    assert pid_a == pid_b  # pool de una conexion: es la misma conexion fisica
    assert (uid_a, uid_b) == (A, B)
    async with pool.connection() as conexion:  # tras las transacciones, la conexion vuelve limpia
        cursor = await conexion.execute("select auth.uid(), current_user")
        assert await cursor.fetchone() == (None, "postgres")


async def test_una_excepcion_deshace_la_transaccion_y_la_conexion_vuelve_limpia(
    pool: AsyncConnectionPool, crear_usuario: Callable[[], UsuarioDePrueba]
) -> None:
    a = crear_usuario()
    with pytest.raises(RuntimeError):
        async with transaccion_con_identidad(
            pool, {"sub": str(a.id), "role": "authenticated"}
        ) as c:
            await c.execute("update public.usuario set nombre = 'Cambiado' where id = %s", (a.id,))
            raise RuntimeError("fallo a mitad de la transaccion")
    async with pool.connection() as conexion:
        cursor = await conexion.execute("select auth.uid(), current_user")
        assert await cursor.fetchone() == (None, "postgres")
        cursor = await conexion.execute("select nombre from public.usuario where id = %s", (a.id,))
        assert await cursor.fetchone() == (None,)  # el update se deshizo
