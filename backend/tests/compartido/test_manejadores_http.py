from typing import Any

import psycopg
import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from bugalu.compartido.manejadores_http import registrar_manejadores
from bugalu.main import crear_app


@pytest.fixture
def cliente() -> AsyncClient:
    app = FastAPI()
    registrar_manejadores(app)

    @app.get("/doble")
    def doble(n: int) -> int:
        return n * 2

    @app.get("/base-caida")
    def base_caida() -> None:
        raise psycopg.OperationalError("connection is bad")

    return AsyncClient(transport=ASGITransport(app=app), base_url="http://t")


async def test_422_usa_el_formato_unico_y_solo_nombra_el_campo(cliente: AsyncClient) -> None:
    r = await cliente.get("/doble", params={"n": "secreto-no-numerico"})
    assert r.status_code == 422
    cuerpo = r.json()
    assert cuerpo == {"error": {"codigo": "datos_invalidos", "mensaje": "Datos invalidos: n."}}
    assert "secreto-no-numerico" not in r.text


async def test_base_de_datos_caida_es_503_sin_www_authenticate(cliente: AsyncClient) -> None:
    r = await cliente.get("/base-caida")
    assert r.status_code == 503
    assert r.json()["error"]["codigo"] == "base_de_datos_no_disponible"
    assert "www-authenticate" not in r.headers


async def test_una_ruta_inexistente_es_404_con_formato_unico() -> None:
    async with AsyncClient(transport=ASGITransport(app=crear_app()), base_url="http://t") as c:
        r = await c.get("/api/v1/noexiste")
    assert r.status_code == 404
    assert r.json()["error"]["codigo"] == "no_encontrado"


async def test_un_metodo_no_permitido_es_405_con_formato_unico_y_conserva_allow() -> None:
    async with AsyncClient(transport=ASGITransport(app=crear_app()), base_url="http://t") as c:
        r = await c.post("/api/v1/perfil")
    assert r.status_code == 405
    assert r.json()["error"]["codigo"] == "metodo_no_permitido"
    assert r.headers["allow"] == "GET"


async def test_pool_sin_base_responde_503_en_lugar_de_500(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("URL_BASE_DATOS", "postgresql://u:p@127.0.0.1:1/db")  # puerto cerrado
    monkeypatch.setenv("URL_SUPABASE", "http://127.0.0.1:1")
    monkeypatch.setenv("TIMEOUT_POOL_SEGUNDOS", "0.5")
    from bugalu.compartido.autenticacion import obtener_claims
    from bugalu.compartido.configuracion import obtener_configuracion

    obtener_configuracion.cache_clear()
    try:
        app = crear_app()
        app.dependency_overrides[obtener_claims] = lambda: {
            "sub": "00000000-0000-0000-0000-00000000000a"
        }
        async with app.router.lifespan_context(app):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
                r: Any = await c.get("/api/v1/perfil")
    finally:
        obtener_configuracion.cache_clear()
    assert r.status_code == 503
    assert r.json()["error"]["codigo"] == "base_de_datos_no_disponible"
