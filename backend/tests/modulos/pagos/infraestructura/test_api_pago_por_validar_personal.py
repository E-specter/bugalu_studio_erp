"""RF-06 (CA-05): el personal ve que hay un pago por validar, nunca el pago (RLS real)."""

from collections.abc import Callable
from typing import Any

import pytest
from httpx import AsyncClient

from tests.conftest import UsuarioDePrueba
from tests.modulos.pagos.infraestructura.test_api_pagos import pagar
from tests.modulos.reservas.infraestructura.conftest import Ejecutar, con

pytestmark = pytest.mark.integracion


async def _ocupados(cliente: AsyncClient, sala: str, quien: UsuarioDePrueba | None) -> list[Any]:
    r = await cliente.get(
        "/api/v1/disponibilidad",
        params={
            "sala": sala,
            "desde": "2027-05-01T00:00:00-05:00",
            "hasta": "2027-05-20T00:00:00-05:00",
        },
        headers=con(quien) if quien else None,
    )
    assert r.status_code == 200, r.text
    return list(r.json()["ocupados"])


async def test_personal_y_administrador_ven_pago_por_validar_sin_datos_de_pago(
    cliente: AsyncClient,
    cliente_a: UsuarioDePrueba,
    personal: UsuarioDePrueba,
    administrador: UsuarioDePrueba,
    cuota_de: Callable[..., str],
    sala: str,
    sql: Ejecutar,
) -> None:
    sin_pago = cuota_de(cliente_a, "pre_reservada")
    con_pago = cuota_de(cliente_a, "pre_reservada")
    assert (await pagar(cliente, cliente_a, con_pago)).status_code == 201
    id_con = str(sql("select id_reserva from public.cuota where id = %s", con_pago)[0][0])
    id_sin = str(sql("select id_reserva from public.cuota where id = %s", sin_pago)[0][0])

    for quien in (personal, administrador):
        marcas = {
            str(o["detalle"]["id_reserva"]): o["detalle"]["pago_por_validar"]
            for o in await _ocupados(cliente, sala, quien)
        }
        assert marcas == {id_con: True, id_sin: False}

    # el personal sabe que hay un pago, pero no ve monto, operacion ni captura
    r = await cliente.get(f"/api/v1/reservas/{id_con}", headers=con(personal))
    assert r.status_code == 200 and r.json()["pago_por_validar"] is True
    assert all(c["pagos"] == [] for c in r.json()["cuotas"])
    assert "PRUEBA-" not in r.text
    r = await cliente.get(
        "/api/v1/reservas",
        params={"desde": "2027-05-01T00:00:00-05:00", "hasta": "2027-05-20T00:00:00-05:00"},
        headers=con(personal),
    )
    assert {x["id"]: x["pago_por_validar"] for x in r.json()} == {id_con: True, id_sin: False}
    assert (
        await cliente.get(
            "/api/v1/pagos", params={"estado": "pendiente_validacion"}, headers=con(personal)
        )
    ).status_code == 403

    # el cliente y el visitante no reciben detalle
    for quien in (cliente_a, None):
        assert all("detalle" not in o for o in await _ocupados(cliente, sala, quien))
