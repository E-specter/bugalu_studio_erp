"""RF-18 ronda 2 (A): reprogramar cotiza con los parametros guardados de la reserva (RF-20)."""

from collections.abc import Callable, Iterator
from decimal import Decimal
from uuid import UUID

import pytest
from httpx import AsyncClient

from tests.conftest import UsuarioDePrueba
from tests.modulos.reservas.infraestructura.conftest import Ejecutar, con

pytestmark = pytest.mark.integracion

RESERVAS = "/api/v1/reservas"
INICIO, FIN = "2027-03-10T10:00:00-05:00", "2027-03-10T12:00:00-05:00"
NUEVO = "2027-03-10T14:00:00-05:00"


@pytest.fixture(autouse=True)
def impuestos_intactos(sql: Ejecutar) -> Iterator[None]:
    yield
    sql(
        "update public.configuracion_impuestos set porcentaje_igv = 18.00, "
        "precios_incluyen_igv = true"
    )


@pytest.fixture
async def reserva_con_igv_18(
    cliente: AsyncClient,
    cliente_a: UsuarioDePrueba,
    sala: str,
    franja: Callable[[str, str], str],
    sql: Ejecutar,
) -> str:
    """Reserva creada con IGV 18 % incluido, confirmada, y luego el estudio cambia el IGV."""
    franja("2027-03-10 08:00-05", "2027-03-10 20:00-05")
    voces = sql("select id from public.servicio where nombre = 'Grabación de voces'")[0][0]
    r = await cliente.post(
        RESERVAS,
        json={
            "id_sala": sala,
            "id_servicio": str(voces),
            "inicio": INICIO,
            "fin": FIN,
            "version_condiciones": "1.0.0",
        },
        headers=con(cliente_a),
    )
    assert r.status_code == 201, r.text
    id_ = r.json()["id"]
    sql(
        "update public.cuota set estado = 'pagada', pagado = monto "
        "where id_reserva = %s and hito = 'al_reservar'",
        UUID(id_),
    )
    sql(
        "update public.reserva set estado = 'confirmada', creada_en = now() - interval '30 days' "
        "where id = %s",
        UUID(id_),
    )
    sql(
        "update public.configuracion_impuestos set porcentaje_igv = 5.00, "
        "precios_incluyen_igv = false"
    )
    return str(id_)


def _desglose_coherente(precio: dict[str, object]) -> bool:
    imp = precio["impuesto"]
    assert isinstance(imp, dict)
    return Decimal(imp["base"]) + Decimal(imp["monto"]) == Decimal(str(precio["total"]))


async def test_simular_reprogramacion_usa_el_igv_guardado_en_la_reserva(
    cliente: AsyncClient, cliente_a: UsuarioDePrueba, reserva_con_igv_18: str
) -> None:
    r = await cliente.post(
        f"{RESERVAS}/{reserva_con_igv_18}/reprogramar/simular",
        json={"inicio": NUEVO},
        headers=con(cliente_a),
    )
    assert r.status_code == 200, r.text
    imp = r.json()["precio"]["impuesto"]
    assert (imp["porcentaje"], imp["incluido"]) == ("18.00", True)
    assert _desglose_coherente(r.json()["precio"])


async def test_reprogramar_guarda_un_precio_con_el_igv_de_la_reserva(
    cliente: AsyncClient,
    cliente_a: UsuarioDePrueba,
    reserva_con_igv_18: str,
    sql: Ejecutar,
) -> None:
    vista = (
        await cliente.post(
            f"{RESERVAS}/{reserva_con_igv_18}/reprogramar/simular",
            json={"inicio": NUEVO},
            headers=con(cliente_a),
        )
    ).json()
    r = await cliente.post(
        f"{RESERVAS}/{reserva_con_igv_18}/reprogramar",
        json={"inicio": NUEVO, "nivel_esperado": 1, "total_esperado": vista["precio"]["total"]},
        headers=con(cliente_a),
    )
    assert r.status_code == 200, r.text
    imp = r.json()["precio"]["impuesto"]
    assert (imp["porcentaje"], imp["incluido"]) == ("18.00", True)
    assert _desglose_coherente(r.json()["precio"])
    fila = sql(
        "select parametros_aplicados ->> 'porcentaje_igv' from public.reserva where id = %s",
        UUID(reserva_con_igv_18),
    )
    assert fila == [("18.00",)]
