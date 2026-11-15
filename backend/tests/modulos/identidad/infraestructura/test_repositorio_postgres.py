from collections.abc import Callable
from uuid import uuid4

import psycopg
import pytest
from psycopg_pool import AsyncConnectionPool

from bugalu.compartido.base_datos import transaccion_con_identidad
from bugalu.compartido.configuracion import Configuracion
from bugalu.modulos.identidad.dominio.usuario import Rol
from bugalu.modulos.identidad.infraestructura.salida.repositorio_postgres import (
    RepositorioPostgres,
)
from tests.conftest import UsuarioDePrueba

pytestmark = pytest.mark.integracion


async def _leer(pool: AsyncConnectionPool, quien: UsuarioDePrueba, id_buscado):  # type: ignore[no-untyped-def]
    async with transaccion_con_identidad(pool, {"sub": str(quien.id)}) as conexion:
        return await RepositorioPostgres(conexion).obtener_por_id(id_buscado)


async def test_lee_el_propio_perfil(
    pool: AsyncConnectionPool, crear_usuario: Callable[[], UsuarioDePrueba]
) -> None:
    a = crear_usuario()
    usuario = await _leer(pool, a, a.id)
    assert usuario is not None and usuario.id == a.id and usuario.rol is Rol.CLIENTE


async def test_a_no_lee_el_perfil_de_b(
    pool: AsyncConnectionPool, crear_usuario: Callable[[], UsuarioDePrueba]
) -> None:
    a, b = crear_usuario(), crear_usuario()
    assert await _leer(pool, a, b.id) is None


async def test_el_administrador_lee_el_perfil_de_otros(
    pool: AsyncConnectionPool,
    crear_usuario: Callable[[], UsuarioDePrueba],
    configuracion: Configuracion,
) -> None:
    admin, b = crear_usuario(), crear_usuario()
    with psycopg.connect(configuracion.url_base_datos_admin) as conexion:
        conexion.execute(
            "update public.usuario set rol = 'administrador' where id = %s", (admin.id,)
        )
    usuario = await _leer(pool, admin, b.id)
    assert usuario is not None and usuario.id == b.id


async def test_perfil_inexistente_devuelve_none(
    pool: AsyncConnectionPool, crear_usuario: Callable[[], UsuarioDePrueba]
) -> None:
    a = crear_usuario()
    assert await _leer(pool, a, uuid4()) is None
