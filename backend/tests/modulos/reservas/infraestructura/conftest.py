from collections.abc import AsyncIterator, Callable, Iterator
from typing import Any
from uuid import UUID

import psycopg
import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from bugalu.compartido.configuracion import Configuracion
from bugalu.main import crear_app
from tests.conftest import UsuarioDePrueba

Ejecutar = Callable[..., list[tuple[Any, ...]]]


@pytest.fixture
async def app() -> AsyncIterator[FastAPI]:
    app = crear_app()
    async with app.router.lifespan_context(app):
        yield app


@pytest.fixture
async def cliente(app: FastAPI) -> AsyncIterator[AsyncClient]:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
        yield c


@pytest.fixture
def sql(configuracion: Configuracion) -> Ejecutar:
    """Solo pruebas: SQL con el rol administrador de la base (sin RLS); devuelve las filas."""

    def ejecutar(consulta: str, *parametros: Any) -> list[tuple[Any, ...]]:
        with psycopg.connect(configuracion.url_base_datos_admin) as c:
            cursor = c.execute(consulta, parametros)
            return cursor.fetchall() if cursor.description else []

    return ejecutar


@pytest.fixture(autouse=True)
def reservas_intactas(
    configuracion: Configuracion, request: pytest.FixtureRequest
) -> Iterator[None]:
    """Las pruebas usan 2027: se anticipa 100 semanas y al final se borra todo lo de ese anio."""
    if request.node.get_closest_marker("integracion") is None:
        yield
        return
    with psycopg.connect(configuracion.url_base_datos_admin) as c:
        antes = c.execute("select clave, valor from public.parametro").fetchall()
        c.execute(
            "update public.parametro set valor = 100 where clave = 'anticipacion_maxima_semanas'"
        )
    yield
    with psycopg.connect(configuracion.url_base_datos_admin) as c:
        c.execute(
            "delete from public.reserva where inicio >= '2027-01-01' and inicio < '2028-01-01'"
        )
        c.execute(
            "delete from public.franja_sala where inicio >= '2027-01-01' and inicio < '2028-01-01'"
        )
        c.execute(
            "delete from public.cierre_sala where inicio >= '2027-01-01' and inicio < '2028-01-01'"
        )
        c.execute("delete from public.notificacion where tipo = 'reserva_caducada'")
        for clave, valor in antes:
            c.execute("update public.parametro set valor = %s where clave = %s", (valor, clave))


def _con_rol(
    crear_usuario: Callable[[], UsuarioDePrueba],
    poner_rol: Callable[[UsuarioDePrueba, str, str | None], None],
    rol: str | None,
) -> UsuarioDePrueba:
    u = crear_usuario()
    if rol:
        poner_rol(u, rol, None)
    return u


@pytest.fixture
def administrador(
    crear_usuario: Callable[[], UsuarioDePrueba],
    poner_rol: Callable[[UsuarioDePrueba, str, str | None], None],
) -> UsuarioDePrueba:
    return _con_rol(crear_usuario, poner_rol, "administrador")


@pytest.fixture
def personal(
    crear_usuario: Callable[[], UsuarioDePrueba],
    poner_rol: Callable[[UsuarioDePrueba, str, str | None], None],
) -> UsuarioDePrueba:
    return _con_rol(crear_usuario, poner_rol, "personal")


@pytest.fixture
def cliente_a(
    crear_usuario: Callable[[], UsuarioDePrueba], configuracion: Configuracion
) -> UsuarioDePrueba:
    u = crear_usuario()
    with psycopg.connect(configuracion.url_base_datos_admin) as c:
        c.execute("update public.usuario set nombre = 'Ana Torres' where id = %s", (u.id,))
    return u


@pytest.fixture
def cliente_b(crear_usuario: Callable[[], UsuarioDePrueba]) -> UsuarioDePrueba:
    return crear_usuario()


def con(usuario: UsuarioDePrueba) -> dict[str, str]:
    return {"Authorization": f"Bearer {usuario.token}"}


@pytest.fixture
def sala(sql: Ejecutar) -> str:
    return str(sql("select id from public.sala_tecnica limit 1")[0][0])


@pytest.fixture
def franja(sql: Ejecutar, sala: str) -> Callable[[str, str], str]:
    def crear(inicio: str, fin: str) -> str:
        return str(
            sql(
                "insert into public.franja_sala (id_sala, inicio, fin) values (%s, %s, %s) "
                "returning id",
                sala,
                inicio,
                fin,
            )[0][0]
        )

    return crear


@pytest.fixture
def reservar(sql: Ejecutar, sala: str) -> Callable[..., str]:
    def crear(
        id_cliente: UUID,
        inicio: str,
        fin: str,
        estado: str = "confirmada",
        vence_pago: str | None = None,
    ) -> str:
        return str(
            sql(
                "insert into public.reserva (id_cliente, id_sala, id_servicio, inicio, fin, total, "
                "estado, vence_pago, motivo_cancelacion) "
                "select %s, %s, se.id, %s, %s, 50, %s, %s, %s "
                "from public.servicio se where se.nombre = 'Ensayo' returning id",
                id_cliente,
                sala,
                inicio,
                fin,
                estado,
                vence_pago,
                "cliente" if estado == "cancelada" else None,
            )[0][0]
        )

    return crear
