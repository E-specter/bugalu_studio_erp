import uuid
from collections.abc import AsyncIterator, Callable, Iterator
from dataclasses import dataclass

import httpx
import psycopg
import pytest
from psycopg_pool import AsyncConnectionPool

from bugalu.compartido.bucle import crear_bucle
from bugalu.compartido.configuracion import Configuracion


@dataclass(frozen=True)
class UsuarioDePrueba:
    id: uuid.UUID
    token: str


def _configuracion() -> Configuracion:
    return Configuracion()  # type: ignore[call-arg]


def _stack_responde() -> str | None:
    try:
        configuracion = _configuracion()
        psycopg.connect(configuracion.url_base_datos, connect_timeout=2).close()
        httpx.get(f"{configuracion.url_supabase}/auth/v1/health", timeout=2)
    except Exception as error:  # noqa: BLE001 - cualquier fallo significa "stack no disponible"
        return (
            "Supabase local de Bugalu no responde (npx supabase start y backend/.env): "
            f"{type(error).__name__}"
        )
    return None


def pytest_asyncio_loop_factories(config: pytest.Config, item: pytest.Item) -> dict[str, Callable]:  # type: ignore[type-arg]
    return {"selector": crear_bucle}


def pytest_runtest_setup(item: pytest.Item) -> None:
    if "integracion" in item.keywords and (motivo := _stack_responde()):
        pytest.skip(motivo)


@pytest.fixture(scope="session")
def configuracion() -> Configuracion:
    return _configuracion()


@pytest.fixture(scope="session")
async def pool(configuracion: Configuracion) -> AsyncIterator[AsyncConnectionPool]:
    async with AsyncConnectionPool(configuracion.url_base_datos, min_size=1, max_size=1) as pool:
        yield pool


@pytest.fixture(scope="session")
def crear_usuario(configuracion: Configuracion) -> Iterator[Callable[[], UsuarioDePrueba]]:
    """Alta real por la API de Auth del stack local; borra los usuarios al terminar."""
    creados: list[uuid.UUID] = []

    def crear() -> UsuarioDePrueba:
        r = httpx.post(
            f"{configuracion.url_supabase}/auth/v1/signup",
            headers={"apikey": configuracion.clave_publicable_supabase},
            json={"email": f"{uuid.uuid4().hex}@prueba.bugalu.pe", "password": "clave-segura-123"},
        )
        r.raise_for_status()
        usuario = UsuarioDePrueba(uuid.UUID(r.json()["user"]["id"]), r.json()["access_token"])
        creados.append(usuario.id)
        return usuario

    yield crear
    with psycopg.connect(configuracion.url_base_datos) as conexion:
        conexion.execute("delete from auth.users where id = any(%s)", (creados,))
