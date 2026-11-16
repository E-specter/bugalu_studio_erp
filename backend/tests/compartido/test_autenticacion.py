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
from bugalu.compartido.autenticacion import (
    obtener_claims,
    obtener_claims_opcionales,
    obtener_resolutor_clave,
    obtener_token,
)
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

    @app.get("/token")
    def token(crudo: Annotated[str, Depends(obtener_token)]) -> dict[str, str]:
        return {"token": crudo}

    @app.get("/opcional")
    def opcional(
        claims: Annotated[dict[str, Any] | None, Depends(obtener_claims_opcionales)],
    ) -> dict[str, Any]:
        return {"claims": claims}

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


def _jwks(cuerpo: Any) -> Callable[[Any], None]:
    def responder(m: BaseHTTPRequestHandler) -> None:
        m.send_response(200)
        m.send_header("Content-Type", "application/json")
        m.end_headers()
        m.wfile.write(json.dumps(cuerpo).encode())

    return responder


async def _pedir_con_jwks(app: FastAPI, cuerpo: Any, token: str) -> Any:
    del app.dependency_overrides[obtener_resolutor_clave]
    with _servidor_jwks(_jwks(cuerpo)) as url:
        app.dependency_overrides[obtener_configuracion] = lambda: Configuracion(
            url_base_datos="x", url_supabase=url
        )
        return await pedir(app, token)


@pytest.mark.parametrize(
    "cuerpo",
    [[], {}, {"keys": []}, {"keys": "x"}, {"keys": [1]}, {"keys": [{"kty": "basura"}]}, "x", 7],
    ids=[
        "lista",
        "objeto",
        "keys_vacio",
        "keys_texto",
        "keys_no_objeto",
        "clave_basura",
        "texto",
        "numero",
    ],
)
async def test_jwks_sin_forma_de_jwks_es_503_sin_www_authenticate(
    app: FastAPI, cuerpo: Any
) -> None:
    r = await _pedir_con_jwks(app, cuerpo, firmar())
    assert r.status_code == 503
    assert r.json()["error"]["codigo"] == "autenticacion_no_disponible"
    assert "www-authenticate" not in r.headers


async def test_kid_ausente_del_jwks_bien_formado_sigue_siendo_401(app: FastAPI) -> None:
    jwk = json.loads(jwt.algorithms.ECAlgorithm.to_jwk(CLAVE.public_key()))
    cuerpo = {"keys": [{**jwk, "kid": "otra", "alg": "ES256", "use": "sig"}]}
    token = jwt.encode(
        {"sub": SUB, "aud": "authenticated", "iss": ISS, "exp": time.time() + 60},
        CLAVE,
        algorithm="ES256",
        headers={"kid": "no-esta"},
    )
    r = await _pedir_con_jwks(app, cuerpo, token)
    assert r.status_code == 401 and r.headers["www-authenticate"] == "Bearer"


async def _opcional(app: FastAPI, token: str | None) -> Any:
    cabeceras = {"Authorization": f"Bearer {token}"} if token else {}
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as cliente:
        return await cliente.get("/opcional", headers=cabeceras)


async def test_claims_opcionales_sin_token_es_visitante_y_con_token_valido_trae_los_claims(
    app: FastAPI,
) -> None:
    assert (await _opcional(app, None)).json() == {"claims": None}
    assert (await _opcional(app, firmar())).json()["claims"]["sub"] == SUB


@pytest.mark.parametrize(
    "token",
    [
        "no-es-un-jwt",
        firmar(exp=time.time() - 10),
        firmar(OTRA_CLAVE),
        firmar(sub="no-es-uuid"),
        con_cabecera("RS256"),
        firmar_con("secreto-hmac-de-32-bytes-o-mas-1234", "HS256"),
        firmar_con(None, "none"),
    ],
    ids=["basura", "caducado", "firma_ajena", "sub_no_uuid", "alg_rsa", "hs256", "none"],
)
async def test_claims_opcionales_con_token_invalido_es_401_no_visitante(
    app: FastAPI, token: str
) -> None:
    r = await _opcional(app, token)
    assert r.status_code == 401 and r.json()["error"]["codigo"] == "no_autenticado"


async def test_obtener_token_entrega_el_token_crudo_solo_si_los_claims_son_validos(
    app: FastAPI,
) -> None:
    bueno = firmar()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as cliente:
        r = await cliente.get("/token", headers={"Authorization": f"Bearer {bueno}"})
        assert r.json() == {"token": bueno}
        malo = await cliente.get(
            "/token", headers={"Authorization": f"Bearer {con_cabecera('HS256')}"}
        )
        assert malo.status_code == 401
        assert (await cliente.get("/token")).status_code == 401
