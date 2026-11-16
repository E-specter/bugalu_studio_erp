"""API de RF-05 (datos para pagar y contacto del estudio): RLS real, estado restaurado."""

from collections.abc import Iterator
from typing import Any

import pytest
from fastapi import FastAPI
from httpx import AsyncClient

from tests.conftest import UsuarioDePrueba
from tests.modulos.pagos.infraestructura.test_api_pagos import codigo
from tests.modulos.reservas.infraestructura.conftest import Ejecutar, con

pytestmark = pytest.mark.integracion

INSTRUCCIONES = "/api/v1/instrucciones-pago"
CONTACTO = "/api/v1/contacto-estudio"
METODOS = ["transferencia", "yape", "plin", "tarjeta"]


@pytest.fixture(autouse=True)
def estado_restaurado(sql: Ejecutar) -> Iterator[None]:
    filas = sql("select metodo, texto, activo from public.instruccion_pago")
    contacto = sql("select texto from public.contacto_estudio")[0][0]
    yield
    for metodo, texto, activo in filas:
        sql(
            "update public.instruccion_pago set texto = %s, activo = %s where metodo = %s",
            texto,
            activo,
            metodo,
        )
    sql("update public.contacto_estudio set texto = %s", contacto)


def cuatro(**cambios: dict[str, Any]) -> list[dict[str, Any]]:
    base = {m: {"metodo": m, "texto": f"Datos de {m}", "activo": True} for m in METODOS}
    for metodo, cambio in cambios.items():
        base[metodo].update(cambio)
    return [base[m] for m in METODOS]


async def test_el_administrador_reemplaza_los_cuatro_y_el_cliente_solo_ve_los_activos(
    cliente: AsyncClient, cliente_a: UsuarioDePrueba, administrador: UsuarioDePrueba
) -> None:
    nuevos = cuatro(
        plin={"texto": "", "activo": False}, tarjeta={"texto": "Linea 1\nLinea 2", "activo": False}
    )
    r = await cliente.put(INSTRUCCIONES, json=nuevos, headers=con(administrador))
    assert r.status_code == 200, r.text
    assert r.json() == nuevos
    assert (await cliente.get(INSTRUCCIONES, headers=con(administrador))).json() == nuevos
    propio = await cliente.get(INSTRUCCIONES, headers=con(cliente_a))
    assert [i["metodo"] for i in propio.json()] == ["transferencia", "yape"]
    assert all(i["activo"] for i in propio.json())


async def test_instrucciones_exigen_sesion_y_solo_el_administrador_escribe(
    cliente: AsyncClient, cliente_a: UsuarioDePrueba, sql: Ejecutar
) -> None:
    assert (await cliente.get(INSTRUCCIONES)).status_code == 401
    assert (await cliente.put(INSTRUCCIONES, json=cuatro())).status_code == 401
    antes = sql("select metodo, texto, activo from public.instruccion_pago order by metodo")
    r = await cliente.put(
        INSTRUCCIONES, json=cuatro(yape={"texto": "robado"}), headers=con(cliente_a)
    )
    assert (r.status_code, codigo(r)) == (403, "sin_permiso")
    assert sql("select metodo, texto, activo from public.instruccion_pago order by metodo") == antes


@pytest.mark.parametrize(
    ("cuerpo", "campo"),
    [
        (cuatro(yape={"texto": "   ", "activo": True}), "texto"),
        (cuatro(yape={"texto": "x" * 1001}), "texto"),
        (cuatro(yape={"texto": "a\x00b"}), "texto"),
        (cuatro()[:3], "metodo"),
        (cuatro() + [cuatro()[0]], "metodo"),
        ([*cuatro()[:3], {"metodo": "yape", "texto": "x", "activo": True}], "metodo"),
        ([*cuatro()[:3], {"metodo": "efectivo", "texto": "x", "activo": True}], "metodo"),
    ],
)
async def test_instrucciones_invalidas_son_422_con_campo_y_no_cambian_nada(
    cliente: AsyncClient,
    administrador: UsuarioDePrueba,
    sql: Ejecutar,
    cuerpo: list[dict[str, Any]],
    campo: str,
) -> None:
    antes = sql("select metodo, texto, activo from public.instruccion_pago order by metodo")
    r = await cliente.put(INSTRUCCIONES, json=cuerpo, headers=con(administrador))
    assert (r.status_code, codigo(r)) == (422, "datos_invalidos"), r.text
    assert r.json()["error"]["detalles"]["campo"] == campo
    assert sql("select metodo, texto, activo from public.instruccion_pago order by metodo") == antes


async def test_mil_caracteres_se_aceptan(
    cliente: AsyncClient, administrador: UsuarioDePrueba
) -> None:
    r = await cliente.put(
        INSTRUCCIONES, json=cuatro(yape={"texto": "x" * 1000}), headers=con(administrador)
    )
    assert r.status_code == 200, r.text


async def test_contacto_lo_lee_cualquiera_y_lo_edita_el_administrador(
    cliente: AsyncClient, cliente_a: UsuarioDePrueba, administrador: UsuarioDePrueba
) -> None:
    r = await cliente.put(
        CONTACTO, json={"texto": "Escribenos al 999 111 222"}, headers=con(administrador)
    )
    assert (r.status_code, r.json()) == (200, {"texto": "Escribenos al 999 111 222"})
    leido = await cliente.get(CONTACTO, headers=con(cliente_a))
    assert (leido.status_code, leido.json()) == (200, {"texto": "Escribenos al 999 111 222"})
    assert (await cliente.get(CONTACTO)).status_code == 401


async def test_contacto_ajeno_invalido_y_sin_sesion(
    cliente: AsyncClient, cliente_a: UsuarioDePrueba, administrador: UsuarioDePrueba
) -> None:
    r = await cliente.put(CONTACTO, json={"texto": "hack"}, headers=con(cliente_a))
    assert (r.status_code, codigo(r)) == (403, "sin_permiso")
    assert (await cliente.put(CONTACTO, json={"texto": "x"})).status_code == 401
    for texto in ("x" * 501, "a\x00b"):
        r = await cliente.put(CONTACTO, json={"texto": texto}, headers=con(administrador))
        assert (r.status_code, codigo(r)) == (422, "datos_invalidos")
        assert r.json()["error"]["detalles"]["campo"] == "texto"
    ok = await cliente.put(CONTACTO, json={"texto": "x" * 500}, headers=con(administrador))
    assert ok.status_code == 200


async def test_openapi_declara_respuesta_error_en_datos_de_pago(app: FastAPI) -> None:
    esquema = app.openapi()["paths"]
    esperados = {
        ("get", "/api/v1/instrucciones-pago"): {"200", "401", "503"},
        ("put", "/api/v1/instrucciones-pago"): {"200", "401", "403", "422", "503"},
        ("get", "/api/v1/contacto-estudio"): {"200", "401", "503"},
        ("put", "/api/v1/contacto-estudio"): {"200", "401", "403", "422", "503"},
    }
    for (metodo, ruta), codigos in esperados.items():
        respuestas = esquema[ruta][metodo]["responses"]
        assert codigos <= set(respuestas), (ruta, set(respuestas))
        for c in codigos - {"200"}:
            assert respuestas[c]["content"]["application/json"]["schema"]["$ref"].endswith(
                "RespuestaError"
            ), (ruta, c)
