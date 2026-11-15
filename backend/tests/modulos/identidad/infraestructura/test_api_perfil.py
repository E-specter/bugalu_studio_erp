import base64
import json
import time
from collections.abc import Callable
from typing import Any

import jwt
import psycopg
import pytest
from cryptography.hazmat.primitives.asymmetric import ec
from fastapi import FastAPI
from httpx import AsyncClient

from bugalu.compartido.autenticacion import obtener_resolutor_clave
from bugalu.compartido.configuracion import Configuracion
from tests.conftest import UsuarioDePrueba

pytestmark = pytest.mark.integracion


def _con(token: str | None) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"} if token else {}


async def test_200_devuelve_el_perfil_del_usuario(
    cliente: AsyncClient, crear_usuario: Callable[[], UsuarioDePrueba]
) -> None:
    a = crear_usuario()
    r = await cliente.get("/api/v1/perfil", headers=_con(a.token))
    assert r.status_code == 200
    assert r.json() == {
        "id": str(a.id),
        "correo": a.correo,
        "correo_confirmado": False,
        "nombre": None,
        "telefono": None,
        "nombre_artistico": None,
        "rol": "cliente",
        "especialidad": None,
    }


async def test_401_sin_token(cliente: AsyncClient) -> None:
    r = await cliente.get("/api/v1/perfil")
    assert r.status_code == 401
    assert r.json() == {
        "error": {"codigo": "no_autenticado", "mensaje": "Falta el token de acceso."}
    }


async def test_401_token_manipulado(
    cliente: AsyncClient, crear_usuario: Callable[[], UsuarioDePrueba]
) -> None:
    cabecera, carga, firma = crear_usuario().token.split(".")
    datos: dict[str, Any] = json.loads(base64.urlsafe_b64decode(carga + "=="))
    datos["sub"] = "00000000-0000-0000-0000-0000000000ad"
    carga_falsa = base64.urlsafe_b64encode(json.dumps(datos).encode()).rstrip(b"=").decode()
    r = await cliente.get("/api/v1/perfil", headers=_con(f"{cabecera}.{carga_falsa}.{firma}"))
    assert r.status_code == 401


async def test_401_token_caducado(
    app: FastAPI, cliente: AsyncClient, configuracion: Configuracion
) -> None:
    clave = ec.generate_private_key(ec.SECP256R1())
    app.dependency_overrides[obtener_resolutor_clave] = lambda: lambda _t: clave.public_key()
    caducado = jwt.encode(
        {
            "sub": "00000000-0000-0000-0000-00000000000a",
            "aud": "authenticated",
            "iss": configuracion.emisor_jwt,
            "exp": time.time() - 60,
        },
        clave,
        algorithm="ES256",
    )
    r = await cliente.get("/api/v1/perfil", headers=_con(caducado))
    assert r.status_code == 401


async def test_404_si_el_usuario_no_tiene_perfil(
    cliente: AsyncClient,
    crear_usuario: Callable[[], UsuarioDePrueba],
    configuracion: Configuracion,
) -> None:
    a = crear_usuario()
    with psycopg.connect(configuracion.url_base_datos_admin) as conexion:
        conexion.execute("delete from public.usuario where id = %s", (a.id,))
    r = await cliente.get("/api/v1/perfil", headers=_con(a.token))
    assert r.status_code == 404
    assert r.json()["error"]["codigo"] == "perfil_no_encontrado"


def test_el_contrato_openapi_declara_401_404_y_503(app: FastAPI) -> None:
    respuestas = app.openapi()["paths"]["/api/v1/perfil"]["get"]["responses"]
    assert {"200", "401", "404", "503"} <= set(respuestas)
