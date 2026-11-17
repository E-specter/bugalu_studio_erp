"""RF-05: las cuotas de la reserva traen su estado, si son pagables y sus pagos (RLS real)."""

from collections.abc import Callable
from typing import Any

import pytest
from httpx import AsyncClient

from tests.conftest import UsuarioDePrueba
from tests.modulos.pagos.infraestructura.test_api_pagos import PAGOS, pagar
from tests.modulos.reservas.infraestructura.conftest import Ejecutar, con

pytestmark = pytest.mark.integracion

Cuota = Callable[..., str]


async def _reserva(
    cliente: AsyncClient, usuario: UsuarioDePrueba, id_cuota: str, sql: Ejecutar
) -> Any:
    id_reserva = sql("select id_reserva from public.cuota where id = %s", id_cuota)[0][0]
    r = await cliente.get(f"/api/v1/reservas/{id_reserva}", headers=con(usuario))
    assert r.status_code == 200, r.text
    return r.json()


async def test_cuota_pendiente_es_pagable_y_sin_pagos(
    cliente: AsyncClient, cliente_a: UsuarioDePrueba, cuota_de: Cuota, sql: Ejecutar
) -> None:
    cuota = cuota_de(cliente_a, "pre_reservada")
    reserva = await _reserva(cliente, cliente_a, cuota, sql)
    assert reserva["pago_por_validar"] is False
    assert reserva["cuotas"][0] | {"id": None} == {
        "id": None,
        "hito": "al_reservar",
        "monto": "25.00",
        "estado": "pendiente",
        "pagable": True,
        "pagos": [],
        "pagado": "0.00",
    }


async def test_con_un_pago_en_validacion_la_cuota_no_es_pagable_y_trae_el_pago(
    cliente: AsyncClient, cliente_a: UsuarioDePrueba, cuota_de: Cuota, sql: Ejecutar
) -> None:
    cuota = cuota_de(cliente_a, "pre_reservada")
    pago = (await pagar(cliente, cliente_a, cuota, numero_operacion="ab-1234")).json()
    reserva = await _reserva(cliente, cliente_a, cuota, sql)
    assert reserva["pago_por_validar"] is True
    [c] = reserva["cuotas"]
    assert (c["estado"], c["pagable"]) == ("en_validacion", False)
    assert c["pagos"] == [
        {
            "id": pago["id"],
            "estado": "pendiente_validacion",
            "metodo": "yape",
            "monto": "25.00",
            "numero_operacion": "AB-1234",
            "motivo_rechazo": None,
            "registrado_en": pago["registrado_en"],
        }
    ]
    mias = (await cliente.get("/api/v1/reservas/mias", headers=con(cliente_a))).json()
    assert [r["pago_por_validar"] for r in mias] == [True]


async def test_un_rechazo_deja_la_cuota_pendiente_pagable_y_con_el_motivo(
    cliente: AsyncClient,
    cliente_a: UsuarioDePrueba,
    administrador: UsuarioDePrueba,
    cuota_de: Cuota,
    sql: Ejecutar,
) -> None:
    cuota = cuota_de(cliente_a, "pre_reservada")
    pago = (await pagar(cliente, cliente_a, cuota)).json()
    await cliente.post(
        f"{PAGOS}/{pago['id']}/rechazar",
        json={"motivo": "Monto errado"},
        headers=con(administrador),
    )
    reserva = await _reserva(cliente, cliente_a, cuota, sql)
    [c] = reserva["cuotas"]
    assert (c["estado"], c["pagable"], reserva["pago_por_validar"]) == ("pendiente", True, False)
    assert [(p["estado"], p["motivo_rechazo"]) for p in c["pagos"]] == [
        ("rechazado", "Monto errado")
    ]


async def test_aprobada_la_cuota_queda_pagada_y_no_pagable(
    cliente: AsyncClient,
    cliente_a: UsuarioDePrueba,
    administrador: UsuarioDePrueba,
    cuota_de: Cuota,
    sql: Ejecutar,
) -> None:
    cuota = cuota_de(cliente_a, "pre_reservada")
    pago = (await pagar(cliente, cliente_a, cuota)).json()
    await cliente.post(f"{PAGOS}/{pago['id']}/aprobar", headers=con(administrador))
    [c] = (await _reserva(cliente, cliente_a, cuota, sql))["cuotas"]
    assert (c["estado"], c["pagable"], c["pagos"][0]["estado"]) == ("pagada", False, "aprobado")


@pytest.mark.parametrize(
    ("estado", "pagable"),
    [("pre_reservada", False), ("confirmada", True), ("en_curso", True), ("cancelada", False)],
)
async def test_la_cuota_al_terminar_solo_es_pagable_con_la_reserva_confirmada_o_posterior(
    cliente: AsyncClient,
    cliente_a: UsuarioDePrueba,
    cuota_de: Cuota,
    sql: Ejecutar,
    estado: str,
    pagable: bool,
) -> None:
    cuota = cuota_de(cliente_a, estado)
    id_reserva = sql("select id_reserva from public.cuota where id = %s", cuota)[0][0]
    sql("delete from public.cuota where id = %s", cuota)
    sql(
        "insert into public.cuota (id_reserva, hito, monto) values (%s, 'al_terminar', 25)",
        id_reserva,
    )
    [c] = (await cliente.get(f"/api/v1/reservas/{id_reserva}", headers=con(cliente_a))).json()[
        "cuotas"
    ]
    assert (c["hito"], c["pagable"]) == ("al_terminar", pagable)


async def test_la_cuota_al_reservar_de_una_reserva_cancelada_no_es_pagable(
    cliente: AsyncClient, cliente_a: UsuarioDePrueba, cuota_de: Cuota, sql: Ejecutar
) -> None:
    cuota = cuota_de(cliente_a, "cancelada")
    [c] = (await _reserva(cliente, cliente_a, cuota, sql))["cuotas"]
    assert c["pagable"] is False
