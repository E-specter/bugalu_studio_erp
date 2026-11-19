"""RF-17 CA-18: vista previa de un texto legal (administrador); no escribe nada."""

import base64
import json
import time
from collections.abc import Callable
from typing import Any
from uuid import uuid4

import jwt
import psycopg
import pytest
from cryptography.hazmat.primitives.asymmetric import ec
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient, Response

from bugalu.compartido.autenticacion import obtener_resolutor_clave
from bugalu.compartido.configuracion import Configuracion, obtener_configuracion
from bugalu.main import crear_app
from bugalu.modulos.identidad.infraestructura.salida.markdown_a_html import markdown_a_html
from tests.conftest import UsuarioDePrueba

pytestmark = pytest.mark.integracion

RUTA = "/api/v1/textos-legales/previsualizar"
Crear = Callable[[], UsuarioDePrueba]
ESCRITURAS = (
    "select (select count(*) from public.texto_legal), (select count(*) from public.aceptacion),"
    " (select count(*) from public.notificacion)"
)


def _con(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def administrador(
    crear_usuario: Crear, poner_rol: Callable[[UsuarioDePrueba, str, str | None], None]
) -> dict[str, str]:
    u = crear_usuario()
    poner_rol(u, "administrador", None)
    return _con(u.token)


@pytest.fixture
def escrituras(configuracion: Configuracion) -> Callable[[], tuple[Any, ...]]:
    def contar() -> tuple[Any, ...]:
        with psycopg.connect(configuracion.url_base_datos_admin) as c:
            return c.execute(ESCRITURAS).fetchone() or ()

    return contar


def _codigo(r: Response) -> tuple[int, str]:
    return r.status_code, r.json()["error"]["codigo"]


async def test_devuelve_el_mismo_html_saneado_que_el_texto_publicado_y_no_escribe(
    cliente: AsyncClient, administrador: dict[str, str], escrituras: Callable[[], tuple[Any, ...]]
) -> None:
    contenido = "# Términos\n\nTexto **completo** con [ayuda](/ayuda).\n\n- uno\n- dos"
    antes = escrituras()
    r = await cliente.post(RUTA, headers=administrador, json={"contenido": contenido})
    assert r.status_code == 200, r.text
    assert r.json() == {"contenido_html": markdown_a_html(contenido)}
    assert "<h1>Términos</h1>" in r.json()["contenido_html"]
    assert "<strong>completo</strong>" in r.json()["contenido_html"]
    assert escrituras() == antes


async def test_html_crudo_y_enlaces_javascript_quedan_neutralizados(
    cliente: AsyncClient, administrador: dict[str, str]
) -> None:
    contenido = (
        "<script>alert(1)</script>\n\n<img src=x onerror=alert(1)>\n\n"
        "[malo](javascript:alert(1)) ![f](javascript:alert(2)) [ok](https://bugalu.pe)"
    )
    r = await cliente.post(RUTA, headers=administrador, json={"contenido": contenido})
    html = r.json()["contenido_html"]
    assert "<script>" not in html and "<img" not in html
    assert "&lt;script&gt;" in html
    assert 'href="javascript' not in html and 'src="javascript' not in html  # queda como texto
    assert "<a " in html and html.count("<a ") == 1  # solo el enlace https
    assert 'href="https://bugalu.pe"' in html


async def test_el_limite_de_200000_caracteres_es_inclusivo(
    cliente: AsyncClient, administrador: dict[str, str]
) -> None:
    r = await cliente.post(RUTA, headers=administrador, json={"contenido": "a" * 200_000})
    assert r.status_code == 200, r.text


@pytest.mark.parametrize(
    "cuerpo",
    [
        {"contenido": ""},
        {"contenido": "   \n "},
        {"contenido": "a" * 200_001},
        {"contenido": "con\x00nul"},
        {"contenido": 5},
        {"contenido": None},
        {"contenido": ["x"]},
        {},
        {"contenido": "ok", "otro": 1},
    ],
)
async def test_422_datos_invalidos_con_su_campo_y_sin_escribir(
    cliente: AsyncClient,
    administrador: dict[str, str],
    escrituras: Callable[[], tuple[Any, ...]],
    cuerpo: dict[str, Any],
) -> None:
    antes = escrituras()
    r = await cliente.post(RUTA, headers=administrador, json=cuerpo)
    assert _codigo(r) == (422, "datos_invalidos")
    assert r.json()["error"]["detalles"]["campo"] in ("contenido", "otro")
    assert escrituras() == antes


async def test_403_un_cliente_no_previsualiza(cliente: AsyncClient, crear_usuario: Crear) -> None:
    r = await cliente.post(RUTA, headers=_con(crear_usuario().token), json={"contenido": "# Hola"})
    assert _codigo(r) == (403, "sin_permiso")


async def test_401_sin_token_con_alg_cambiado_o_caducado(
    app: FastAPI, cliente: AsyncClient, configuracion: Configuracion, crear_usuario: Crear
) -> None:
    cuerpo = {"contenido": "# Hola"}
    assert (await cliente.post(RUTA, json=cuerpo)).status_code == 401
    cabecera, carga, firma = crear_usuario().token.split(".")
    datos = json.loads(base64.urlsafe_b64decode(cabecera + "=="))
    datos["alg"] = "HS256"
    falsa = base64.urlsafe_b64encode(json.dumps(datos).encode()).rstrip(b"=").decode()
    r = await cliente.post(RUTA, headers=_con(f"{falsa}.{carga}.{firma}"), json=cuerpo)
    assert r.status_code == 401
    clave = ec.generate_private_key(ec.SECP256R1())
    app.dependency_overrides[obtener_resolutor_clave] = lambda: lambda _t: clave.public_key()
    caducado = jwt.encode(
        {
            "sub": str(uuid4()),
            "aud": "authenticated",
            "iss": configuracion.emisor_jwt,
            "exp": time.time() - 60,
        },
        clave,
        algorithm="ES256",
    )
    assert (await cliente.post(RUTA, headers=_con(caducado), json=cuerpo)).status_code == 401


async def test_503_con_la_base_caida_nunca_500(
    monkeypatch: pytest.MonkeyPatch, crear_usuario: Crear
) -> None:
    usuario = crear_usuario()
    monkeypatch.setenv("URL_BASE_DATOS", "postgresql://u:p@127.0.0.1:1/db")
    monkeypatch.setenv("TIMEOUT_POOL_SEGUNDOS", "0.5")
    obtener_configuracion.cache_clear()
    app = crear_app()
    async with (
        app.router.lifespan_context(app),
        AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c,
    ):
        r = await c.post(RUTA, headers=_con(usuario.token), json={"contenido": "# Hola"})
        assert _codigo(r) == (503, "base_de_datos_no_disponible")
    obtener_configuracion.cache_clear()


def test_openapi_declara_los_codigos_del_contrato(app: FastAPI) -> None:
    respuestas = app.openapi()["paths"][RUTA]["post"]["responses"]
    for codigo in ("401", "403", "422", "503"):
        assert respuestas[codigo]["content"]["application/json"]["schema"] == {
            "$ref": "#/components/schemas/RespuestaError"
        }
    assert "200" in respuestas
