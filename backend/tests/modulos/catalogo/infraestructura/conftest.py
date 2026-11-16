from collections.abc import AsyncIterator, Callable, Iterator
from typing import Any

import psycopg
import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from bugalu.compartido.configuracion import Configuracion
from bugalu.main import crear_app
from tests.conftest import UsuarioDePrueba

TABLAS = ("servicio", "especialista", "recargo", "feriado", "servicio_especialista")


@pytest.fixture
async def app() -> AsyncIterator[FastAPI]:
    app = crear_app()
    async with app.router.lifespan_context(app):
        yield app


@pytest.fixture
async def cliente(app: FastAPI) -> AsyncIterator[AsyncClient]:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
        yield c


@pytest.fixture(autouse=True)
def catalogo_intacto(
    configuracion: Configuracion, request: pytest.FixtureRequest
) -> Iterator[None]:
    """Las pruebas editan el catalogo real: se restaura tal cual estaba."""
    if request.node.get_closest_marker("integracion") is None:
        yield
        return
    with psycopg.connect(configuracion.url_base_datos_admin) as c:
        antes = {t: c.execute(f"select * from public.{t} order by 1, 2").fetchall() for t in TABLAS}
    yield
    with psycopg.connect(configuracion.url_base_datos_admin) as c:
        c.execute("delete from public.servicio_especialista")
        c.execute("delete from public.feriado")
        for t in ("servicio", "especialista", "recargo"):
            filas = antes[t]
            if not filas:
                continue
            columnas = [
                d.name for d in c.execute(f"select * from public.{t} limit 0").description or []
            ]
            asignar = ", ".join(f"{k} = %s" for k in columnas[1:])
            for fila in filas:
                c.execute(
                    f"update public.{t} set {asignar} where {columnas[0]} = %s",
                    (*fila[1:], fila[0]),
                )
        for fila in antes["servicio_especialista"]:
            c.execute("insert into public.servicio_especialista values (%s, %s)", fila)
        for fila in antes["feriado"]:
            c.execute("insert into public.feriado values (%s, %s)", fila)


@pytest.fixture
def administrador(
    crear_usuario: Callable[[], UsuarioDePrueba],
    poner_rol: Callable[[UsuarioDePrueba, str, str | None], None],
) -> dict[str, str]:
    u = crear_usuario()
    poner_rol(u, "administrador", None)
    return {"Authorization": f"Bearer {u.token}"}


@pytest.fixture
def cliente_sin_rol(crear_usuario: Callable[[], UsuarioDePrueba]) -> dict[str, str]:
    return {"Authorization": f"Bearer {crear_usuario().token}"}


@pytest.fixture
def sql(configuracion: Configuracion) -> Callable[..., list[tuple[Any, ...]]]:
    """Solo pruebas: lee el estado real de la base con el rol administrador."""

    def consultar(consulta: str, *parametros: Any) -> list[tuple[Any, ...]]:
        with psycopg.connect(configuracion.url_base_datos_admin) as c:
            return c.execute(consulta, parametros).fetchall()

    return consultar
