
import pytest
from httpx import ASGITransport, AsyncClient

from bugalu.compartido.configuracion import obtener_configuracion
from bugalu.main import crear_app

PERMITIDO = "http://localhost:4321"


async def _preflight(monkeypatch: pytest.MonkeyPatch, env: str, origen: str):  # type: ignore[no-untyped-def]
    # setenv (incluso vacio) gana al backend/.env local; delenv dejaria pasar el del .env.
    monkeypatch.setenv("ORIGENES_PERMITIDOS", env)
    obtener_configuracion.cache_clear()
    try:
        app = crear_app()
    finally:
        obtener_configuracion.cache_clear()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as cliente:
        return await cliente.options(
            "/api/v1/perfil",
            headers={
                "Origin": origen,
                "Access-Control-Request-Method": "GET",
                "Access-Control-Request-Headers": "Authorization",
            },
        )


async def test_preflight_desde_origen_permitido(monkeypatch: pytest.MonkeyPatch) -> None:
    r = await _preflight(monkeypatch, f"{PERMITIDO},http://127.0.0.1:4321", PERMITIDO)
    assert r.status_code == 200
    assert r.headers["access-control-allow-origin"] == PERMITIDO
    assert "authorization" in r.headers["access-control-allow-headers"].lower()
    assert "access-control-allow-credentials" not in r.headers


async def test_preflight_desde_origen_no_permitido(monkeypatch: pytest.MonkeyPatch) -> None:
    r = await _preflight(monkeypatch, PERMITIDO, "http://malo.example")
    assert "access-control-allow-origin" not in r.headers


async def test_sin_origenes_no_hay_cors(monkeypatch: pytest.MonkeyPatch) -> None:
    r = await _preflight(monkeypatch, "", PERMITIDO)
    assert "access-control-allow-origin" not in r.headers
