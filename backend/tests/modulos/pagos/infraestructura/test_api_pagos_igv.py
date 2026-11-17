"""RF-20 (1/2): el pago trae su desglose de IGV con el porcentaje guardado en su reserva."""

import pytest
from httpx import AsyncClient

from tests.conftest import UsuarioDePrueba
from tests.modulos.pagos.infraestructura.test_api_pagos import PAGOS, Cuota, pagar
from tests.modulos.reservas.infraestructura.conftest import Ejecutar, con

pytestmark = pytest.mark.integracion


async def test_el_pago_trae_el_igv_con_el_porcentaje_guardado_en_su_reserva(
    cliente: AsyncClient, cliente_a: UsuarioDePrueba, cuota_de: Cuota, sql: Ejecutar
) -> None:
    cuota = cuota_de(cliente_a)
    sql(  # la reserva se creo con 10 %: el IGV vigente (18 %) no cuenta
        "update public.reserva set parametros_aplicados = jsonb_set(parametros_aplicados, "
        "'{porcentaje_igv}', '\"10.00\"') "
        "where id = (select id_reserva from public.cuota where id = %s)",
        cuota,
    )
    r = await pagar(cliente, cliente_a, cuota)
    assert r.status_code == 201, r.text
    assert r.json()["impuesto"] == {"porcentaje": "10.00", "base": "22.73", "monto": "2.27"}
    leido = await cliente.get(f"{PAGOS}/{r.json()['id']}", headers=con(cliente_a))
    assert leido.json()["impuesto"] == r.json()["impuesto"]


async def test_el_pago_de_una_reserva_al_18_desglosa_25_en_21_19_y_3_81(
    cliente: AsyncClient, cliente_a: UsuarioDePrueba, cuota_de: Cuota
) -> None:
    r = await pagar(cliente, cliente_a, cuota_de(cliente_a))
    assert r.json()["impuesto"] == {"porcentaje": "18.00", "base": "21.19", "monto": "3.81"}
