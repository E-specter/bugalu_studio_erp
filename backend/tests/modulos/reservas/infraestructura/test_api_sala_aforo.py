"""RF-03 ampliacion: aforo e ITSE por sala (GET y PATCH /salas, stack local con RLS real)."""

import base64
import json
import time
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from typing import Any

import jwt
import pytest
from fastapi import FastAPI
from httpx import AsyncClient

from tests.conftest import UsuarioDePrueba
from tests.modulos.reservas.infraestructura.conftest import Ejecutar, con

pytestmark = pytest.mark.integracion

OK = {"aforo": 12, "itse_certificado": "ITSE-001-2026", "itse_vence": "2099-12-31"}
LEER = "select aforo, itse_certificado, itse_vence from public.sala_tecnica where id = %s"
LIMPIAR = (
    "update public.sala_tecnica set aforo = null, itse_certificado = null, itse_vence = null "
    "where id = %s"
)


@pytest.fixture(autouse=True)
def sala_sin_aforo(sql: Ejecutar, sala: str) -> Iterator[None]:
    sql(LIMPIAR, sala)
    yield
    sql(LIMPIAR, sala)


def _url(sala: str) -> str:
    return f"/api/v1/salas/{sala}"


def _hoy_lima() -> datetime:
    return datetime.now(UTC) - timedelta(hours=5)


async def test_una_sala_sin_datos_devuelve_aforo_e_itse_nulos(cliente: AsyncClient) -> None:
    [sala] = (await cliente.get("/api/v1/salas")).json()
    assert set(sala) == {"id", "nombre", "sede", "aforo", "itse"}
    assert sala["aforo"] is None and sala["itse"] is None


async def test_el_administrador_guarda_y_el_publico_lo_ve(
    cliente: AsyncClient, sala: str, administrador: UsuarioDePrueba
) -> None:
    r = await cliente.patch(_url(sala), json=OK, headers=con(administrador))
    esperado = {"certificado": "ITSE-001-2026", "vence": "2099-12-31"}
    assert r.status_code == 200
    assert r.json()["id"] == sala and r.json()["aforo"] == 12 and r.json()["itse"] == esperado
    [publica] = (await cliente.get("/api/v1/salas")).json()
    assert publica["aforo"] == 12 and publica["itse"] == esperado


async def test_hoy_en_lima_es_un_vencimiento_valido(
    cliente: AsyncClient, sala: str, administrador: UsuarioDePrueba
) -> None:
    hoy = _hoy_lima().date().isoformat()
    r = await cliente.patch(_url(sala), json=OK | {"itse_vence": hoy}, headers=con(administrador))
    assert r.status_code == 200


async def test_un_vencimiento_pasado_es_422_itse_vencido_y_no_guarda(
    cliente: AsyncClient, sala: str, administrador: UsuarioDePrueba, sql: Ejecutar
) -> None:
    ayer = (_hoy_lima().date() - timedelta(days=1)).isoformat()
    r = await cliente.patch(_url(sala), json=OK | {"itse_vence": ayer}, headers=con(administrador))
    assert r.status_code == 422 and r.json()["error"]["codigo"] == "itse_vencido"
    assert r.json()["error"]["detalles"]["campo"] == "itse_vence"
    assert sql(LEER, sala) == [(None, None, None)]


@pytest.mark.parametrize(
    ("cambio", "campo"),
    [
        ({"aforo": 0}, "aforo"),
        ({"aforo": 201}, "aforo"),
        ({"aforo": -1}, "aforo"),
        ({"aforo": 12.5}, "aforo"),
        ({"aforo": "12"}, "aforo"),
        ({"aforo": "doce"}, "aforo"),
        ({"aforo": True}, "aforo"),
        ({"aforo": None}, "aforo"),
        ({"itse_certificado": ""}, "itse_certificado"),
        ({"itse_certificado": "   "}, "itse_certificado"),
        ({"itse_certificado": "A" * 41}, "itse_certificado"),
        ({"itse_certificado": "A\nB"}, "itse_certificado"),
        ({"itse_certificado": "A\rB"}, "itse_certificado"),
        ({"itse_certificado": 5}, "itse_certificado"),
        ({"itse_certificado": None}, "itse_certificado"),
        ({"itse_vence": "31/12/2099"}, "itse_vence"),
        ({"itse_vence": "2099-02-30"}, "itse_vence"),
        ({"itse_vence": "2099-12-31T00:00:00"}, "itse_vence"),
        ({"itse_vence": 4102358400}, "itse_vence"),
        ({"itse_vence": None}, "itse_vence"),
        ({"extra": 1}, "extra"),
    ],
)
async def test_datos_invalidos_son_422_con_el_campo_y_no_guardan(
    cliente: AsyncClient,
    sala: str,
    administrador: UsuarioDePrueba,
    sql: Ejecutar,
    cambio: dict[str, Any],
    campo: str,
) -> None:
    r = await cliente.patch(_url(sala), json=OK | cambio, headers=con(administrador))
    assert r.status_code == 422 and r.json()["error"]["codigo"] == "datos_invalidos"
    assert r.json()["error"]["detalles"]["campo"] == campo
    assert sql(LEER, sala) == [(None, None, None)]


@pytest.mark.parametrize("faltante", sorted(OK))
async def test_los_tres_campos_son_obligatorios(
    cliente: AsyncClient, sala: str, administrador: UsuarioDePrueba, faltante: str
) -> None:
    cuerpo = {k: v for k, v in OK.items() if k != faltante}
    r = await cliente.patch(_url(sala), json=cuerpo, headers=con(administrador))
    assert r.status_code == 422 and r.json()["error"]["detalles"]["campo"] == faltante


async def test_un_cuerpo_que_no_es_objeto_es_422(
    cliente: AsyncClient, sala: str, administrador: UsuarioDePrueba
) -> None:
    r = await cliente.patch(_url(sala), json=[1], headers=con(administrador))
    assert r.status_code == 422 and r.json()["error"]["codigo"] == "datos_invalidos"


async def test_una_sala_inexistente_es_404(
    cliente: AsyncClient, administrador: UsuarioDePrueba
) -> None:
    r = await cliente.patch(
        _url("00000000-0000-0000-0000-000000000000"), json=OK, headers=con(administrador)
    )
    assert r.status_code == 404 and r.json()["error"]["codigo"] == "no_encontrado"


async def test_un_id_que_no_es_uuid_es_422(
    cliente: AsyncClient, administrador: UsuarioDePrueba
) -> None:
    r = await cliente.patch(_url("no-es-uuid"), json=OK, headers=con(administrador))
    assert r.status_code == 422 and r.json()["error"]["codigo"] == "datos_invalidos"


async def test_sin_token_es_401_y_la_fila_queda_intacta(
    cliente: AsyncClient, sala: str, sql: Ejecutar
) -> None:
    r = await cliente.patch(_url(sala), json=OK)
    assert r.status_code == 401 and r.json()["error"]["codigo"] == "no_autenticado"
    assert sql(LEER, sala) == [(None, None, None)]


def _con_alg(token: str, alg: str) -> str:
    _, resto = token.split(".", 1)
    nueva = json.dumps({"alg": alg, "typ": "JWT"}).encode()
    return base64.urlsafe_b64encode(nueva).rstrip(b"=").decode() + "." + resto


async def test_tokens_manipulados_son_401_nunca_500(
    cliente: AsyncClient, sala: str, administrador: UsuarioDePrueba, sql: Ejecutar
) -> None:
    caducado = jwt.encode(
        {"sub": str(administrador.id), "aud": "authenticated", "exp": time.time() - 60},
        "x" * 32,
        algorithm="HS256",
    )
    for token in (
        _con_alg(administrador.token, "HS256"),
        _con_alg(administrador.token, "none"),
        caducado,
        "basura",
    ):
        r = await cliente.patch(_url(sala), json=OK, headers={"Authorization": f"Bearer {token}"})
        assert r.status_code == 401 and r.json()["error"]["codigo"] == "no_autenticado"
    assert sql(LEER, sala) == [(None, None, None)]


async def test_cliente_y_personal_reciben_403_y_la_fila_queda_intacta(
    cliente: AsyncClient,
    sala: str,
    cliente_a: UsuarioDePrueba,
    personal: UsuarioDePrueba,
    sql: Ejecutar,
) -> None:
    for quien in (cliente_a, personal):
        r = await cliente.patch(_url(sala), json=OK, headers=con(quien))
        assert r.status_code == 403 and r.json()["error"]["codigo"] == "sin_permiso"
    assert sql(LEER, sala) == [(None, None, None)]


async def test_el_certificado_se_guarda_sin_espacios_en_los_bordes(
    cliente: AsyncClient, sala: str, administrador: UsuarioDePrueba
) -> None:
    r = await cliente.patch(
        _url(sala), json=OK | {"itse_certificado": "  ITSE-9  "}, headers=con(administrador)
    )
    assert r.status_code == 200 and r.json()["itse"]["certificado"] == "ITSE-9"


async def test_openapi_declara_los_codigos_de_patch_salas(app: FastAPI) -> None:
    respuestas = app.openapi()["paths"]["/api/v1/salas/{id_sala}"]["patch"]["responses"]
    for codigo in ("200", "401", "403", "404", "422", "503"):
        assert codigo in respuestas
