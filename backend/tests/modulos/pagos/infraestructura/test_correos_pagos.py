"""RF-05 CA-07: los avisos de pago llegan por SMTP (Mailpit del stack local)."""

from collections.abc import Callable
from typing import Any

import pytest
from fastapi import FastAPI
from httpx import AsyncClient

from bugalu.compartido.configuracion import Configuracion
from tests.conftest import UsuarioDePrueba
from tests.modulos.pagos.infraestructura.test_api_pagos import PAGOS, pagar
from tests.modulos.reservas.infraestructura.conftest import Ejecutar, con
from tests.modulos.reservas.infraestructura.test_correos_reserva import (  # noqa: F401
    correos_de,
    enviar_solo_a,
)

pytestmark = pytest.mark.integracion

Correos = Callable[[str], list[dict[str, Any]]]


async def test_aprobar_avisa_al_cliente_que_su_reserva_esta_confirmada(
    app: FastAPI,
    cliente: AsyncClient,
    configuracion: Configuracion,
    cliente_a: UsuarioDePrueba,
    administrador: UsuarioDePrueba,
    cuota_de: Callable[..., str],
    correos_de: Correos,  # noqa: F811
    sql: Ejecutar,
) -> None:
    pago = (await pagar(cliente, cliente_a, cuota_de(cliente_a, "pre_reservada"))).json()
    r = await cliente.post(f"{PAGOS}/{pago['id']}/aprobar", headers=con(administrador))
    assert r.status_code == 200, r.text
    await enviar_solo_a(app, configuracion, sql, cliente_a.correo, administrador.correo)
    [correo] = correos_de(cliente_a.correo)
    assert pago["reserva"]["folio"] in correo["Subject"]
    assert "S/ 25,00" in correo["Text"]
    assert "tu reserva está confirmada" in correo["Text"]
    [aviso] = correos_de(administrador.correo)  # `pago_registrado` al administrador
    assert pago["numero_operacion"] in aviso["Text"] and "coincide con la cuota" in aviso["Text"]


async def test_rechazar_avisa_el_motivo_al_cliente(
    app: FastAPI,
    cliente: AsyncClient,
    configuracion: Configuracion,
    cliente_a: UsuarioDePrueba,
    administrador: UsuarioDePrueba,
    cuota_de: Callable[..., str],
    correos_de: Correos,  # noqa: F811
    sql: Ejecutar,
) -> None:
    pago = (await pagar(cliente, cliente_a, cuota_de(cliente_a, "pre_reservada"))).json()
    await cliente.post(
        f"{PAGOS}/{pago['id']}/rechazar",
        json={"motivo": "Monto errado"},
        headers=con(administrador),
    )
    await enviar_solo_a(app, configuracion, sql, cliente_a.correo, administrador.correo)
    [correo] = correos_de(cliente_a.correo)
    assert "Monto errado" in correo["Text"] and "otro pago" in correo["Text"]
