import time
from collections.abc import Iterator
from typing import Annotated, Any

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import ec
from fastapi import Depends, FastAPI
from httpx import ASGITransport, AsyncClient

from bugalu.compartido.autenticacion import obtener_claims, obtener_resolutor_clave
from bugalu.compartido.manejadores_http import registrar_manejadores

CLAVE = ec.generate_private_key(ec.SECP256R1())
OTRA_CLAVE = ec.generate_private_key(ec.SECP256R1())
ISS = "http://127.0.0.1:45621/auth/v1"


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
    claims = {"sub": "u1", "aud": "authenticated", "iss": ISS, "exp": time.time() + 60} | cambios
    return jwt.encode({k: v for k, v in claims.items() if v is not None}, clave, algorithm="ES256")


async def pedir(app: FastAPI, token: str | None) -> Any:
    cabeceras = {"Authorization": f"Bearer {token}"} if token else {}
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as cliente:
        return await cliente.get("/protegido", headers=cabeceras)


async def test_token_valido_devuelve_los_claims(app: FastAPI) -> None:
    r = await pedir(app, firmar())
    assert r.status_code == 200 and r.json()["sub"] == "u1"


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
    ],
    ids=["sin_token", "basura", "caducado", "firma_ajena", "audiencia", "emisor", "sin_sub"],
)
async def test_token_ausente_o_invalido_es_401_con_formato_unico(
    app: FastAPI, token: str | None
) -> None:
    r = await pedir(app, token)
    assert r.status_code == 401
    assert r.json()["error"]["codigo"] == "no_autenticado"
    assert r.headers["www-authenticate"] == "Bearer"
