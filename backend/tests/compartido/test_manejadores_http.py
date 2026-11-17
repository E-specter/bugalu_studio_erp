from types import SimpleNamespace
from typing import Any

import psycopg
import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from bugalu.compartido.manejadores_http import registrar_manejadores
from bugalu.main import crear_app


class _ViolacionFk(psycopg.errors.ForeignKeyViolation):
    diag = SimpleNamespace(constraint_name="reserva_id_franja_fkey")  # type: ignore[assignment]


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

    @app.get("/dato-invalido")
    def dato_invalido() -> None:
        raise psycopg.DataError("invalid byte sequence: secreto-interno")

    @app.get("/integridad")
    def integridad() -> None:
        raise _ViolacionFk("viola: secreto-interno")

    return AsyncClient(transport=ASGITransport(app=app), base_url="http://t")


async def test_422_usa_el_formato_unico_y_solo_nombra_el_campo(cliente: AsyncClient) -> None:
    r = await cliente.get("/doble", params={"n": "secreto-no-numerico"})
    assert r.status_code == 422
    cuerpo = r.json()
    assert cuerpo == {
        "error": {
            "codigo": "datos_invalidos",
            "mensaje": "Datos invalidos: n.",
            "detalles": {"campo": "n"},
        }
    }
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


@pytest.mark.parametrize(
    "error", [psycopg.errors.DeadlockDetected, psycopg.errors.SerializationFailure]
)
async def test_interbloqueo_o_fallo_de_serializacion_es_409_conflicto(
    error: type[psycopg.OperationalError],
) -> None:
    app = FastAPI()
    registrar_manejadores(app)

    @app.get("/cruce")
    def cruce() -> None:
        raise error("detalle-interno")

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
        r = await c.get("/cruce")
    assert r.status_code == 409
    assert r.json() == {
        "error": {
            "codigo": "conflicto",
            "mensaje": "Otro cambio se cruzó con el tuyo. Vuelve a intentarlo.",
        }
    }
    assert "detalle-interno" not in r.text


async def test_data_error_de_psycopg_es_422_sin_filtrar_detalles(cliente: AsyncClient) -> None:
    r = await cliente.get("/dato-invalido")
    assert r.status_code == 422
    assert r.json() == {"error": {"codigo": "datos_invalidos", "mensaje": "Datos invalidos."}}
    assert "secreto-interno" not in r.text


async def test_un_error_de_negocio_con_detalles_los_incluye_y_sin_ellos_no() -> None:
    from bugalu.compartido.errores import Conflicto

    app = FastAPI()
    registrar_manejadores(app)

    @app.get("/con")
    def con() -> None:
        raise Conflicto("Hay reservas.", detalles={"reservas": [{"folio": "R-1"}]})

    @app.get("/sin")
    def sin() -> None:
        raise Conflicto("Choca.")

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
        con_detalles = (await c.get("/con")).json()
        sin_detalles = (await c.get("/sin")).json()
    assert con_detalles["error"]["detalles"] == {"reservas": [{"folio": "R-1"}]}
    assert "detalles" not in sin_detalles["error"]


async def test_una_violacion_de_integridad_imprevista_es_409_y_nunca_500(
    cliente: AsyncClient,
) -> None:
    r = await cliente.get("/integridad")
    assert r.status_code == 409
    assert r.json() == {
        "error": {"codigo": "conflicto", "mensaje": "La operación choca con datos existentes."}
    }
    assert "secreto-interno" not in r.text


async def test_la_violacion_de_integridad_se_registra_sin_valores_de_la_fila(
    cliente: AsyncClient, caplog: pytest.LogCaptureFixture
) -> None:
    with caplog.at_level("WARNING"):
        await cliente.get("/integridad")
    registro = next(r for r in caplog.records if r.levelname == "WARNING")
    mensaje = registro.getMessage()
    assert "_ViolacionFk" in mensaje and "reserva_id_franja_fkey" in mensaje
    assert "secreto-interno" not in mensaje
