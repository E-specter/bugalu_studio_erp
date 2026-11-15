import base64
import json
import time
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Thread
from typing import Annotated, Any

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import ec, ed25519
from fastapi import Depends, FastAPI
from httpx import ASGITransport, AsyncClient

from bugalu.compartido import autenticacion
from bugalu.compartido.autenticacion import obtener_claims, obtener_resolutor_clave
from bugalu.compartido.configuracion import Configuracion, obtener_configuracion
from bugalu.compartido.manejadores_http import registrar_manejadores

CLAVE = ec.generate_private_key(ec.SECP256R1())
OTRA_CLAVE = ec.generate_private_key(ec.SECP256R1())
ISS = "http://127.0.0.1:45621/auth/v1"
SUB = "00000000-0000-0000-0000-00000000000a"


@pytest.fixture
def app() -> Iterator[FastAPI]:
    app = FastAPI()
    registrar_manejadores(app)

    @app.get("/protegido")
    def protegido(claims: Annotated[dict[str, Any], Depends(obtener_claims)]) -> dict[str, Any]:
        return claims

    app.dependency_overrides[obtener_resolutor_clave] = lambda: lambda _token: CLAVE.public_key()
    yield app


def firmar(clave: ec.EllipticCurvePrivateKey = CLAVE, **cambios: Any) -> str:
    claims = {"sub": SUB, "aud": "authenticated", "iss": ISS, "exp": time.time() + 60} | cambios
    return jwt.encode({k: v for k, v in claims.items() if v is not None}, clave, algorithm="ES256")


def con_cabecera(alg: str) -> str:
    """Token ES256 valido con la cabecera `alg` cambiada (ataque de confusion de algoritmo)."""
    cabecera, carga, firma = firmar().split(".")
    nueva = json.dumps({"alg": alg, "typ": "JWT"}).encode()
    return ".".join([base64.urlsafe_b64encode(nueva).rstrip(b"=").decode(), carga, firma])


def firmar_con(clave: Any, algoritmo: str | None) -> str:
    claims = {"sub": SUB, "aud": "authenticated", "iss": ISS, "exp": time.time() + 60}
    return jwt.encode(claims, clave, algorithm=algoritmo)


async def pedir(app: FastAPI, token: str | None) -> Any:
    cabeceras = {"Authorization": f"Bearer {token}"} if token else {}
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as cliente:
        return await cliente.get("/protegido", headers=cabeceras)


async def test_token_valido_devuelve_los_claims(app: FastAPI) -> None:
    r = await pedir(app, firmar())
    assert r.status_code == 200 and r.json()["sub"] == SUB


@pytest.mark.parametrize(
    "token",
    [
        None,
        "no-es-un-jwt",
        firmar(exp=time.time() - 10),
        firmar(OTRA_CLAVE),
        firmar(aud="otro"),
        firmar(iss="http://otro"),
        firmar(sub=None),
        firmar(sub="no-es-uuid"),
        con_cabecera("RS256"),
        firmar_con(ed25519.Ed25519PrivateKey.generate(), "EdDSA"),
        firmar_con("secreto-hmac-de-32-bytes-o-mas-1234", "HS256"),
        firmar_con(None, "none"),
    ],
    ids=[
        "sin_token",
        "basura",
        "caducado",
        "firma_ajena",
        "audiencia",
        "emisor",
        "sin_sub",
        "sub_no_uuid",
        "alg_rsa_con_clave_ec",
        "eddsa",
        "hs256",
        "none",
    ],
)
async def test_token_ausente_o_invalido_es_401_con_formato_unico(
    app: FastAPI, token: str | None
) -> None:
    r = await pedir(app, token)
    assert r.status_code == 401
    assert r.json()["error"]["codigo"] == "no_autenticado"
    assert r.headers["www-authenticate"] == "Bearer"


async def test_jwks_inaccesible_es_503_con_formato_unico(app: FastAPI) -> None:
    del app.dependency_overrides[obtener_resolutor_clave]
    app.dependency_overrides[obtener_configuracion] = lambda: Configuracion(
        url_base_datos="x",
        url_supabase="http://127.0.0.1:1",  # puerto cerrado
    )
    r = await pedir(app, firmar())
    assert r.status_code == 503
    assert r.json()["error"]["codigo"] == "autenticacion_no_disponible"


@contextmanager
def _servidor_jwks(manejar: Callable[[BaseHTTPRequestHandler], None]) -> Iterator[str]:
    class Manejador(BaseHTTPRequestHandler):
        def do_GET(self) -> None:  # noqa: N802
            manejar(self)

        def log_message(self, *_: Any) -> None:
            pass

    servidor = ThreadingHTTPServer(("127.0.0.1", 0), Manejador)
    Thread(target=servidor.serve_forever, daemon=True).start()
    try:
        yield f"http://127.0.0.1:{servidor.server_port}"
    finally:
        servidor.shutdown()


def _cuerpo_no_json(m: BaseHTTPRequestHandler) -> None:
    m.send_response(200)
    m.end_headers()
    m.wfile.write(b"<html>no es json</html>")


def _colgar(m: BaseHTTPRequestHandler) -> None:
    time.sleep(1.5)


@pytest.mark.parametrize("respuesta", [_cuerpo_no_json, _colgar], ids=["no_json", "timeout"])
async def test_jwks_roto_o_lento_es_503_sin_www_authenticate(
    app: FastAPI, monkeypatch: pytest.MonkeyPatch, respuesta: Callable[[Any], None]
) -> None:
    monkeypatch.setattr(autenticacion, "TIMEOUT_JWKS_SEGUNDOS", 0.3)
    del app.dependency_overrides[obtener_resolutor_clave]
    with _servidor_jwks(respuesta) as url:
        app.dependency_overrides[obtener_configuracion] = lambda: Configuracion(
            url_base_datos="x", url_supabase=url
        )
        r = await pedir(app, firmar())
    assert r.status_code == 503
    assert r.json()["error"]["codigo"] == "autenticacion_no_disponible"
    assert "www-authenticate" not in r.headers
