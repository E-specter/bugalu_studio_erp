"""Textos rotos (NUL, controles, sustitutos, separadores) en cada entrada: 422, nunca 500."""

import json
from collections.abc import Callable
from typing import Any
from uuid import UUID

import pytest
from httpx import AsyncClient

from tests.conftest import UsuarioDePrueba
from tests.modulos.pagos.infraestructura.conftest import PNG, operacion
from tests.modulos.pagos.infraestructura.test_api_datos_pago import (
    CONTACTO,
    INSTRUCCIONES,
    cuatro,
    estado_restaurado,  # noqa: F401 - fixture autouse que restaura datos para pagar y contacto
)
from tests.modulos.pagos.infraestructura.test_api_pagos import PAGOS, codigo, pagar
from tests.modulos.reservas.infraestructura.conftest import Ejecutar, con

pytestmark = pytest.mark.integracion

Cuota = Callable[..., str]
RESERVAS = "/api/v1/reservas"

ROTOS = [
    "a\x00b",
    "a\x01b",
    "a\x08b",
    "a\x0bb",
    "a\x1fb",
    "a\x7fb",
    "a\x80b",
    "a\x85b",
    "a\x9fb",
    "a b",
    "a b",
    "a\ud800b",
    "a\udfffb",
    "\ud800",
]
# httpx no puede codificar un sustituto suelto en un multipart: esos van como bytes crudos abajo.
CODIFICABLES = [v for v in ROTOS if not any(0xD800 <= ord(c) <= 0xDFFF for c in v)]


def _json(cuerpo: Any, usuario: UsuarioDePrueba) -> dict[str, Any]:
    # ensure_ascii escribe el sustituto suelto como "\ud800", tal como lo manda un cliente real.
    return {
        "content": json.dumps(cuerpo).encode(),
        "headers": {**con(usuario), "Content-Type": "application/json"},
    }


def _rechazado(r: Any, campo: str) -> None:
    assert r.status_code == 422, r.text
    assert codigo(r) == "datos_invalidos"
    assert r.json()["error"]["detalles"]["campo"] == campo


async def _pago(cliente: AsyncClient, usuario: UsuarioDePrueba, cuota_de: Cuota) -> str:
    r = await pagar(cliente, usuario, cuota_de(usuario), monto="30")
    assert r.status_code == 201, r.text
    return str(r.json()["id"])


@pytest.mark.parametrize("motivo", ROTOS)
async def test_motivo_de_rechazo_roto_es_422_y_no_cambia_el_pago(
    cliente: AsyncClient,
    cliente_a: UsuarioDePrueba,
    administrador: UsuarioDePrueba,
    cuota_de: Cuota,
    sql: Ejecutar,
    motivo: str,
) -> None:
    id_pago = await _pago(cliente, cliente_a, cuota_de)
    r = await cliente.post(
        f"{PAGOS}/{id_pago}/rechazar", **_json({"motivo": motivo}, administrador)
    )
    _rechazado(r, "motivo")
    assert sql("select estado from public.comprobante_pago where id = %s", UUID(id_pago)) == [
        ("pendiente_validacion",)
    ]


async def test_crlf_en_el_motivo_se_normaliza_a_salto_de_linea(
    cliente: AsyncClient,
    cliente_a: UsuarioDePrueba,
    administrador: UsuarioDePrueba,
    cuota_de: Cuota,
) -> None:
    id_pago = await _pago(cliente, cliente_a, cuota_de)
    r = await cliente.post(
        f"{PAGOS}/{id_pago}/rechazar", **_json({"motivo": "uno\r\ndos"}, administrador)
    )
    assert r.status_code == 200, r.text
    assert r.json()["motivo_rechazo"] == "uno\ndos"


@pytest.mark.parametrize("nota", ROTOS)
async def test_nota_de_cancelacion_rota_es_422_y_no_cancela(
    cliente: AsyncClient,
    cliente_a: UsuarioDePrueba,
    administrador: UsuarioDePrueba,
    cuota_de: Cuota,
    sql: Ejecutar,
    nota: str,
) -> None:
    cuota = cuota_de(cliente_a, "pre_reservada")
    reserva = sql("select id_reserva from public.cuota where id = %s", UUID(cuota))[0][0]
    r = await cliente.post(f"{RESERVAS}/{reserva}/cancelar", **_json({"nota": nota}, administrador))
    _rechazado(r, "nota")
    assert sql("select estado from public.reserva where id = %s", reserva) == [("pre_reservada",)]


@pytest.mark.parametrize("texto", ROTOS)
async def test_texto_de_datos_para_pagar_roto_es_422_y_no_cambia_nada(
    cliente: AsyncClient, administrador: UsuarioDePrueba, sql: Ejecutar, texto: str
) -> None:
    antes = sql("select metodo, texto, activo from public.instruccion_pago order by metodo")
    r = await cliente.put(INSTRUCCIONES, **_json(cuatro(yape={"texto": texto}), administrador))
    _rechazado(r, "texto")
    assert sql("select metodo, texto, activo from public.instruccion_pago order by metodo") == antes


@pytest.mark.parametrize("texto", ROTOS)
async def test_texto_de_contacto_roto_es_422_y_no_cambia_nada(
    cliente: AsyncClient, administrador: UsuarioDePrueba, sql: Ejecutar, texto: str
) -> None:
    antes = sql("select texto from public.contacto_estudio")
    r = await cliente.put(CONTACTO, **_json({"texto": texto}, administrador))
    _rechazado(r, "texto")
    assert sql("select texto from public.contacto_estudio") == antes


async def test_cuerpo_json_con_utf8_invalido_es_422(
    cliente: AsyncClient,
    cliente_a: UsuarioDePrueba,
    administrador: UsuarioDePrueba,
    cuota_de: Cuota,
    sql: Ejecutar,
) -> None:
    id_pago = await _pago(cliente, cliente_a, cuota_de)
    contacto = sql("select texto from public.contacto_estudio")
    cabeceras = {**con(administrador), "Content-Type": "application/json"}
    r = await cliente.post(
        f"{PAGOS}/{id_pago}/rechazar", content=b'{"motivo": "a\xffb"}', headers=cabeceras
    )
    assert r.status_code == 422, r.text
    assert codigo(r) == "datos_invalidos"
    r = await cliente.put(CONTACTO, content=b'{"texto": "a\xffb"}', headers=cabeceras)
    assert r.status_code == 422, r.text
    assert codigo(r) == "datos_invalidos"
    assert sql("select estado from public.comprobante_pago where id = %s", UUID(id_pago)) == [
        ("pendiente_validacion",)
    ]
    assert sql("select texto from public.contacto_estudio") == contacto


@pytest.mark.parametrize("valor", CODIFICABLES)
@pytest.mark.parametrize("campo", ["metodo", "monto", "numero_operacion"])
async def test_campos_de_pagos_rotos_son_422_y_no_registran_nada(
    cliente: AsyncClient,
    cliente_a: UsuarioDePrueba,
    cuota_de: Cuota,
    sql: Ejecutar,
    campo: str,
    valor: str,
) -> None:
    r = await pagar(cliente, cliente_a, cuota_de(cliente_a), **{campo: valor})
    _rechazado(r, campo)
    assert sql("select count(*) from public.comprobante_pago")[0][0] == 0


async def test_id_cuota_roto_es_422(
    cliente: AsyncClient, cliente_a: UsuarioDePrueba, cuota_de: Cuota
) -> None:
    cuota_de(cliente_a)
    r = await pagar(cliente, cliente_a, "a\x00b")
    _rechazado(r, "id_cuota")


def _multipart(partes: dict[str, bytes], archivo: bytes = PNG) -> tuple[bytes, dict[str, str]]:
    comilla = bytes([34])
    limite = b"BUGALU-LIMITE"
    cuerpo = b""
    for nombre, valor in partes.items():
        cuerpo += (
            b"--"
            + limite
            + b"\r\nContent-Disposition: form-data; name="
            + comilla
            + nombre.encode()
            + comilla
            + b"\r\n\r\n"
            + valor
            + b"\r\n"
        )
    cuerpo += (
        b"--"
        + limite
        + b"\r\nContent-Disposition: form-data; name="
        + comilla
        + b"captura"
        + comilla
        + b"; filename="
        + comilla
        + b"c.png"
        + comilla
        + b"\r\nContent-Type: image/png\r\n\r\n"
        + archivo
        + b"\r\n--"
        + limite
        + b"--\r\n"
    )
    return cuerpo, {"Content-Type": "multipart/form-data; boundary=BUGALU-LIMITE"}


@pytest.mark.parametrize("campo", ["metodo", "monto", "numero_operacion", "id_cuota"])
@pytest.mark.parametrize("basura", [b"a\xffb", b"\xed\xa0\x80", b"\xc0\xaf"])
async def test_multipart_con_utf8_invalido_o_sustituto_es_422(
    cliente: AsyncClient,
    cliente_a: UsuarioDePrueba,
    cuota_de: Cuota,
    sql: Ejecutar,
    campo: str,
    basura: bytes,
) -> None:
    partes = {
        "id_cuota": cuota_de(cliente_a).encode(),
        "metodo": b"yape",
        "monto": b"25.00",
        "numero_operacion": operacion().encode(),
        campo: basura,
    }
    cuerpo, cabeceras = _multipart(partes)
    r = await cliente.post(PAGOS, content=cuerpo, headers={**con(cliente_a), **cabeceras})
    assert r.status_code == 422, r.text
    assert codigo(r) == "datos_invalidos"
    assert sql("select count(*) from public.comprobante_pago")[0][0] == 0
