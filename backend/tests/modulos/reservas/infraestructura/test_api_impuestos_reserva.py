"""RF-20 (1/2): la reserva guarda IGV y parametros al crearse y un cambio posterior no la altera."""

from collections.abc import Callable, Iterator
from decimal import ROUND_HALF_UP, Decimal
from typing import Any

import pytest
from httpx import AsyncClient

from tests.conftest import UsuarioDePrueba
from tests.modulos.reservas.infraestructura.conftest import Ejecutar, con

pytestmark = pytest.mark.integracion

RESERVAS = "/api/v1/reservas"
INICIO, FIN = "2027-03-10T10:00:00-05:00", "2027-03-10T12:00:00-05:00"
D = Decimal
APLICADOS = {
    "porcentaje_igv": "18.00",
    "precios_incluyen_igv": True,
    "horas_limite_pago": 1,
    "horas_nivel_1": 48,
    "horas_nivel_2": 24,
    "porcentaje_adelanto": 50,
}


@pytest.fixture(autouse=True)
def impuestos_intactos(sql: Ejecutar) -> Iterator[None]:
    yield
    sql(
        "update public.configuracion_impuestos set porcentaje_igv = 18.00, "
        "precios_incluyen_igv = true"
    )


@pytest.fixture
def dia(franja: Callable[[str, str], str]) -> str:
    return franja("2027-03-10 08:00-05", "2027-03-10 20:00-05")


async def _reservar(
    cliente: AsyncClient, usuario: UsuarioDePrueba, sql: Ejecutar, sala: str
) -> Any:
    voces = sql("select id from public.servicio where nombre = 'Grabación de voces'")[0][0]
    return await cliente.post(
        RESERVAS,
        json={
            "id_sala": sala,
            "id_servicio": str(voces),
            "inicio": INICIO,
            "fin": FIN,
            "version_condiciones": "1.0.0",
        },
        headers=con(usuario),
    )


async def test_la_reserva_guarda_el_desglose_y_los_parametros_aplicados(
    cliente: AsyncClient, dia: str, sala: str, cliente_a: UsuarioDePrueba, sql: Ejecutar
) -> None:
    r = await _reservar(cliente, cliente_a, sql, sala)
    assert r.status_code == 201, r.text
    precio = r.json()["precio"]
    assert precio["impuesto"]["nombre"] == "IGV" and precio["impuesto"]["incluido"] is True
    assert D(precio["impuesto"]["base"]) + D(precio["impuesto"]["monto"]) == D(precio["total"])
    guardados = sql("select parametros_aplicados from public.reserva where id = %s", r.json()["id"])
    assert guardados == [(APLICADOS,)]


async def test_el_anticipo_de_la_reserva_sale_del_parametro_de_adelanto(
    cliente: AsyncClient, dia: str, sala: str, cliente_a: UsuarioDePrueba, sql: Ejecutar
) -> None:
    sql("update public.parametro set valor = 30 where clave = 'porcentaje_adelanto'")
    r = await _reservar(cliente, cliente_a, sql, sala)
    assert r.status_code == 201, r.text
    total = D(r.json()["precio"]["total"])
    cuotas = {c["hito"]: D(c["monto"]) for c in r.json()["cuotas"]}
    assert cuotas["al_reservar"] == (total * 30 / 100).quantize(D("0.01"), rounding=ROUND_HALF_UP)
    assert cuotas["al_reservar"] + cuotas["al_terminar"] == total
    guardados = sql("select parametros_aplicados from public.reserva where id = %s", r.json()["id"])
    assert guardados[0][0]["porcentaje_adelanto"] == 30


async def test_cambiar_el_igv_no_altera_el_desglose_de_una_reserva_existente(
    cliente: AsyncClient, dia: str, sala: str, cliente_a: UsuarioDePrueba, sql: Ejecutar
) -> None:
    creada = (await _reservar(cliente, cliente_a, sql, sala)).json()
    sql(
        "update public.configuracion_impuestos set porcentaje_igv = 5.00, "
        "precios_incluyen_igv = false"
    )
    leida = await cliente.get(f"{RESERVAS}/{creada['id']}", headers=con(cliente_a))
    assert leida.status_code == 200
    assert leida.json()["precio"] == creada["precio"]
    mias = await cliente.get(f"{RESERVAS}/mias", headers=con(cliente_a))
    assert mias.json()[0]["precio"]["impuesto"]["porcentaje"] == "18.00"


async def test_una_reserva_anterior_a_rf20_se_muestra_con_18_incluido_y_no_cambia(
    cliente: AsyncClient,
    cliente_a: UsuarioDePrueba,
    reservar: Callable[..., str],
    sql: Ejecutar,
) -> None:
    id_reserva = reservar(cliente_a.id, "2027-06-01T10:00:00-05:00", "2027-06-01T12:00:00-05:00")
    # Como las de antes de RF-20: precio sin `impuesto` y parametros completados por la migracion.
    sql(
        "update public.reserva set precio = %s::jsonb where id = %s",
        '{"lineas": [], "recargos": [], "total": "150.00", "anticipo": "75.00"}',
        id_reserva,
    )
    sql(
        "update public.configuracion_impuestos set porcentaje_igv = 5.00, "
        "precios_incluyen_igv = false"
    )
    r = await cliente.get(f"{RESERVAS}/{id_reserva}", headers=con(cliente_a))
    assert r.status_code == 200, r.text
    assert r.json()["precio"]["impuesto"] == {
        "nombre": "IGV",
        "porcentaje": "18.00",
        "incluido": True,
        "base": "127.12",
        "monto": "22.88",
    }
    assert r.json()["precio"]["porcentaje_adelanto"] == "50.00"
