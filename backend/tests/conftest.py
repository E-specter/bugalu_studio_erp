import os
import re
import time
import uuid
from collections.abc import AsyncIterator, Callable, Iterator
from dataclasses import dataclass
from urllib.parse import parse_qs, urlparse

import httpx
import psycopg
import pytest
from psycopg_pool import AsyncConnectionPool

from bugalu.compartido.bucle import crear_bucle
from bugalu.compartido.configuracion import Configuracion, obtener_configuracion


@dataclass(frozen=True)
class UsuarioDePrueba:
    id: uuid.UUID
    token: str
    correo: str = ""


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


def saltar_o_fallar(motivo: str) -> None:
    """Modo estricto para CI: con EXIGIR_INTEGRACION=1 el stack caido es un fallo, no un salto."""
    if os.environ.get("EXIGIR_INTEGRACION") == "1":
        pytest.fail(f"EXIGIR_INTEGRACION=1 y no hay stack de integracion: {motivo}", pytrace=False)
    pytest.skip(motivo)


def pytest_runtest_setup(item: pytest.Item) -> None:
    if "integracion" in item.keywords and (motivo := _stack_responde()):
        saltar_o_fallar(motivo)


@pytest.fixture(autouse=True)
def _entorno_aislado(
    request: pytest.FixtureRequest, monkeypatch: pytest.MonkeyPatch
) -> Iterator[None]:
    """Las pruebas unitarias no dependen de backend/.env: el entorno gana a ese archivo."""
    monkeypatch.setenv("INTERVALO_ENVIO_CORREOS", "0")  # sin tarea periodica en las pruebas
    if request.node.get_closest_marker("integracion") is None:
        monkeypatch.setenv("URL_BASE_DATOS", "postgresql://u:p@127.0.0.1:1/db")
        monkeypatch.setenv("URL_SUPABASE", "http://127.0.0.1:45621")
        monkeypatch.setenv("ORIGENES_PERMITIDOS", "")
        obtener_configuracion.cache_clear()
    yield
    obtener_configuracion.cache_clear()


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
        correo = f"{uuid.uuid4().hex}@prueba.bugalu.pe"
        r = httpx.post(
            f"{configuracion.url_supabase}/auth/v1/signup",
            headers={"apikey": configuracion.clave_publicable_supabase},
            json={"email": correo, "password": "Clave-Segura-123"},
        )
        r.raise_for_status()
        usuario = UsuarioDePrueba(
            uuid.UUID(r.json()["user"]["id"]), r.json()["access_token"], correo
        )
        creados.append(usuario.id)
        return usuario

    yield crear
    with psycopg.connect(configuracion.url_base_datos_admin) as conexion:
        # Una prueba puede dejar al unico administrador. Solo ese trigger se apaga y se reactiva en
        # esta transaccion: las cascadas de claves foraneas siguen activas y no quedan huerfanos.
        trigger = "alter table public.usuario {} trigger usuario_conserva_administrador"
        conexion.execute(trigger.format("disable"))
        # id_revisor no tiene cascada: primero las solicitudes que tocan a estos usuarios.
        conexion.execute(
            "delete from public.solicitud_acceso "
            "where id_usuario = any(%s) or id_revisor = any(%s)",
            (creados, creados),
        )
        conexion.execute("delete from auth.users where id = any(%s)", (creados,))
        conexion.execute(trigger.format("enable"))
        huerfanos = conexion.execute(
            """select (select count(*) from public.usuario u
                       where not exists (select 1 from auth.users a where a.id = u.id))
                    + (select count(*) from public.solicitud_acceso s
                       where not exists (select 1 from auth.users a where a.id = s.id_usuario))
                    + (select count(*) from auth.users where email like '%%@prueba.bugalu.pe')"""
        ).fetchone()
    assert huerfanos == (0,), f"las pruebas dejaron basura en la base: {huerfanos}"


@pytest.fixture
def poner_rol(configuracion: Configuracion) -> Callable[[UsuarioDePrueba, str, str | None], None]:
    """Solo pruebas: sube o baja el rol por SQL con el rol administrador de la base."""

    def poner(usuario: UsuarioDePrueba, rol: str, especialidad: str | None = None) -> None:
        with psycopg.connect(configuracion.url_base_datos_admin) as conexion:
            conexion.execute(
                "update public.usuario set rol = %s, especialidad = %s where id = %s",
                (rol, especialidad, usuario.id),
            )

    return poner


@pytest.fixture(scope="session")
def sesion_por_enlace(configuracion: Configuracion) -> Callable[[UsuarioDePrueba], str]:
    """Token de una sesion abierta con el enlace de un solo uso de Mailpit (como signInWithOtp)."""
    mailpit = os.environ.get("URL_MAILPIT", "http://127.0.0.1:45624")

    def abrir(usuario: UsuarioDePrueba) -> str:
        httpx.post(
            f"{configuracion.url_supabase}/auth/v1/otp",
            headers={"apikey": configuracion.clave_publicable_supabase},
            json={"email": usuario.correo, "create_user": False},
        ).raise_for_status()
        mensajes: list[dict[str, str]] = []
        for _ in range(50):
            mensajes = httpx.get(
                f"{mailpit}/api/v1/search", params={"query": f"to:{usuario.correo}"}
            ).json()["messages"]
            if mensajes:
                break
            time.sleep(0.1)
        cuerpo = httpx.get(f"{mailpit}/api/v1/message/{mensajes[0]['ID']}").json()
        enlace = re.search(r'https?://[^\s"<>]+/verify\?[^\s"<>]+', cuerpo["HTML"] + cuerpo["Text"])
        assert enlace, "el correo no trae enlace"
        r = httpx.get(enlace.group(0).replace("&amp;", "&"), follow_redirects=False)
        return parse_qs(urlparse(r.headers["location"]).fragment)["access_token"][0]

    return abrir
