"""RF-20 (1/2): GET /impuestos y el desglose de IGV en la simulacion (stack local, RLS real)."""

from collections.abc import Callable, Iterator
from datetime import datetime, timedelta, timezone
from decimal import ROUND_HALF_UP, Decimal
from typing import Any

import pytest
from httpx import AsyncClient

from bugalu.modulos.catalogo.dominio.precio import desglosar_igv_incluido

pytestmark = pytest.mark.integracion

Sql = Callable[..., list[tuple[Any, ...]]]
LIMA = timezone(timedelta(hours=-5))
D = Decimal
CENTIMO = D("0.01")


@pytest.fixture(autouse=True)
def impuestos_y_adelanto_intactos(sql: Sql) -> Iterator[None]:
    yield
    sql(
        "update public.configuracion_impuestos set porcentaje_igv = 18.00, "
        "precios_incluyen_igv = true"
    )
    sql("update public.parametro set valor = 50 where clave = 'porcentaje_adelanto'")


async def _simular(cliente: AsyncClient, sql: Sql) -> dict[str, Any]:
    servicios = {s["nombre"]: s["id"] for s in (await cliente.get("/api/v1/servicios")).json()}
    r = await cliente.post(
        "/api/v1/simulaciones",
        json={
            "id_sala": str(sql("select id from public.sala_tecnica limit 1")[0][0]),
            "id_servicio": servicios["Grabación de voces"],
            "inicio": datetime(2026, 12, 9, 10, tzinfo=LIMA).isoformat(),
            "fin": datetime(2026, 12, 9, 12, tzinfo=LIMA).isoformat(),
            "especialistas": [],
        },
    )
    assert r.status_code == 200, r.text
    body: dict[str, Any] = r.json()
    return body


async def test_get_impuestos_es_publico_y_devuelve_texto_decimal(cliente: AsyncClient) -> None:
    r = await cliente.get("/api/v1/impuestos", headers={"Authorization": "Bearer basura"})
    assert r.status_code == 200
    assert r.json() == {"porcentaje_igv": "18.00", "precios_incluyen_igv": True}


async def test_get_impuestos_refleja_la_base(cliente: AsyncClient, sql: Sql) -> None:
    sql(
        "update public.configuracion_impuestos set porcentaje_igv = 7.50, "
        "precios_incluyen_igv = false"
    )
    assert (await cliente.get("/api/v1/impuestos")).json() == {
        "porcentaje_igv": "7.50",
        "precios_incluyen_igv": False,
    }


async def test_la_simulacion_trae_el_desglose_de_igv_incluido(
    cliente: AsyncClient, sql: Sql
) -> None:
    s = await _simular(cliente, sql)
    total = D(s["total"])
    base, igv = desglosar_igv_incluido(total, D("18.00"))
    assert s["impuesto"] == {
        "nombre": "IGV",
        "porcentaje": "18.00",
        "incluido": True,
        "base": str(base),
        "monto": str(igv),
    }
    assert base + igv == total


async def test_sin_igv_incluido_el_total_suma_el_igv_y_el_anticipo_sale_del_total(
    cliente: AsyncClient, sql: Sql
) -> None:
    incluido = await _simular(cliente, sql)
    sql("update public.configuracion_impuestos set precios_incluyen_igv = false")
    s = await _simular(cliente, sql)
    assert s["impuesto"]["incluido"] is False
    assert s["impuesto"]["base"] == incluido["total"]  # las lineas son las mismas, ahora netas
    assert D(s["total"]) == D(s["impuesto"]["base"]) + D(s["impuesto"]["monto"])
    assert D(s["anticipo"]) == (D(s["total"]) / 2).quantize(CENTIMO, rounding=ROUND_HALF_UP)


async def test_el_anticipo_sale_del_parametro_de_adelanto(cliente: AsyncClient, sql: Sql) -> None:
    sql("update public.parametro set valor = 30 where clave = 'porcentaje_adelanto'")
    s = await _simular(cliente, sql)
    assert D(s["anticipo"]) == (D(s["total"]) * 30 / 100).quantize(CENTIMO, rounding=ROUND_HALF_UP)


async def test_la_simulacion_expone_el_porcentaje_de_adelanto_como_texto(
    cliente: AsyncClient, sql: Sql
) -> None:
    assert (await _simular(cliente, sql))["porcentaje_adelanto"] == "50.00"
    sql("update public.parametro set valor = 30 where clave = 'porcentaje_adelanto'")
    assert (await _simular(cliente, sql))["porcentaje_adelanto"] == "30.00"
