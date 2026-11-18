"""`obtener_claims_o_visitante`: el alta publica trata un token invalido como sin sesion (RF-16)."""

import time
from collections.abc import Iterator
from typing import Annotated, Any

import pytest
from cryptography.hazmat.primitives.asymmetric import ec
from fastapi import Depends, FastAPI
from httpx import ASGITransport, AsyncClient

from bugalu.compartido.autenticacion import obtener_claims_o_visitante, obtener_resolutor_clave
from bugalu.compartido.configuracion import Configuracion, obtener_configuracion
from bugalu.compartido.manejadores_http import registrar_manejadores
from tests.compartido.test_autenticacion import (
    CLAVE,
    OTRA_CLAVE,
    SUB,
    con_cabecera,
    firmar,
    firmar_con,
)


@pytest.fixture
def app() -> Iterator[FastAPI]:
    app = FastAPI()
    registrar_manejadores(app)

    @app.get("/alta")
    def alta(
        claims: Annotated[dict[str, Any] | None, Depends(obtener_claims_o_visitante)],
    ) -> dict[str, Any]:
        return {"claims": claims}

    app.dependency_overrides[obtener_resolutor_clave] = lambda: lambda _t: CLAVE.public_key()
    yield app


async def _pedir(app: FastAPI, token: str | None) -> Any:
    cabeceras = {"Authorization": f"Bearer {token}"} if token else {}
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
        return await c.get("/alta", headers=cabeceras)


async def test_un_token_valido_trae_los_claims_y_sin_token_es_visitante(app: FastAPI) -> None:
    assert (await _pedir(app, firmar())).json()["claims"]["sub"] == SUB
    assert (await _pedir(app, None)).json() == {"claims": None}


@pytest.mark.parametrize(
    "token",
    [
        "no-es-un-jwt",
        firmar(exp=time.time() - 10),
        firmar(OTRA_CLAVE),
        firmar(sub="no-es-uuid"),
        con_cabecera("RS256"),
        con_cabecera("HS256"),
        firmar_con("secreto-hmac-de-32-bytes-o-mas-1234", "HS256"),
        firmar_con(None, "none"),
        firmar_con(ec.generate_private_key(ec.SECP256R1()), "ES256"),
    ],
    ids=[
        "basura", "caducado", "firma_ajena", "sub_no_uuid", "alg_rsa", "alg_hs256_en_cabecera",
        "hs256", "none", "otra_clave_ec",
    ],
)  # fmt: skip
async def test_un_token_invalido_es_visitante_no_401(app: FastAPI, token: str) -> None:
    r = await _pedir(app, token)
    assert (r.status_code, r.json()) == (200, {"claims": None})


async def test_si_no_se_puede_verificar_el_token_es_503_y_no_visitante(app: FastAPI) -> None:
    del app.dependency_overrides[obtener_resolutor_clave]
    app.dependency_overrides[obtener_configuracion] = lambda: Configuracion(
        url_base_datos="x",
        url_supabase="http://127.0.0.1:1",  # puerto cerrado
    )
    r = await _pedir(app, firmar())
    assert (r.status_code, r.json()["error"]["codigo"]) == (503, "autenticacion_no_disponible")
