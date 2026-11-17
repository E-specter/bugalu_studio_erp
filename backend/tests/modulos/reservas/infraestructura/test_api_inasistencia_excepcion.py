"""RF-18 (parte A): inasistencia (CA-11) y caso excepcional (CA-12) con la RLS real."""

from collections.abc import Callable, Iterator
from typing import Any
from uuid import UUID

import pytest
from httpx import AsyncClient

from tests.conftest import UsuarioDePrueba
from tests.modulos.reservas.infraestructura.conftest import Ejecutar, con

pytestmark = pytest.mark.integracion

RESERVAS = "/api/v1/reservas"
PRECIO = '{"lineas": [], "recargos": [], "total": "200", "anticipo": "100"}'


@pytest.fixture
def reserva_ahora(sql: Ejecutar, sala: str) -> Iterator[Callable[..., str]]:
    """Reserva de total 200 con el adelanto pagado, cerca de ahora (se borra al terminar)."""
    creadas: list[str] = []

    def crear(usuario: UsuarioDePrueba, horas: int = -1, estado: str = "confirmada") -> str:
        id_ = str(
            sql(
                "insert into public.reserva (id_cliente, id_sala, id_servicio, inicio, fin, total, "
                "estado, vence_pago, precio, creada_en) select %s, %s, se.id, "
                "date_trunc('hour', now()) + %s * interval '1 hour', "
                "date_trunc('hour', now()) + %s * interval '1 hour' + interval '2 hours', 200, %s, "
                "'2099-01-01', %s::jsonb, now() - interval '30 days' "
                "from public.servicio se where se.nombre = 'Ensayo' returning id",
                usuario.id,
                sala,
                horas,
                horas,
                estado,
                PRECIO,
            )[0][0]
        )
        sql(
            "insert into public.cuota (id_reserva, hito, monto, estado, pagado) values "
            "(%s, 'al_reservar', 100, 'pagada', 100), (%s, 'al_terminar', 100, 'pendiente', 0)",
            UUID(id_),
            UUID(id_),
        )
        creadas.append(id_)
        return id_

    yield crear
    for id_ in creadas:
        sql("delete from public.reserva where id = %s", UUID(id_))


def codigo(r: Any) -> str:
    return str(r.json()["error"]["codigo"])


async def test_el_personal_marca_la_inasistencia_y_se_retiene_lo_pagado(
    cliente: AsyncClient,
    cliente_a: UsuarioDePrueba,
    personal: UsuarioDePrueba,
    reserva_ahora: Callable[..., str],
    sql: Ejecutar,
) -> None:
    id_ = reserva_ahora(cliente_a)
    r = await cliente.post(f"{RESERVAS}/{id_}/inasistencia", headers=con(personal))
    assert r.status_code == 200, r.text
    reserva = r.json()
    assert reserva["estado"] == "no_asistio"
    c = reserva["cancelacion"]
    assert (c["por"], c["nivel"], c["pagado"], c["retenido"], c["credito"]) == (
        "inasistencia",
        None,
        "100.00",
        "100.00",
        "0.00",
    )
    assert c["registrada_por"]["id"] == str(personal.id)
    assert {q["hito"]: q["estado"] for q in reserva["cuotas"]} == {
        "al_reservar": "pagada",
        "al_terminar": "anulada",
    }
    assert sql("select count(*) from public.credito") == [(0,)]
    assert (
        await cliente.post(f"{RESERVAS}/{id_}/inasistencia", headers=con(personal))
    ).status_code == 409


async def test_inasistencia_errores_y_permisos(
    cliente: AsyncClient,
    cliente_a: UsuarioDePrueba,
    cliente_b: UsuarioDePrueba,
    personal: UsuarioDePrueba,
    reserva_ahora: Callable[..., str],
    sql: Ejecutar,
) -> None:
    id_ = reserva_ahora(cliente_a)
    url = f"{RESERVAS}/{id_}/inasistencia"
    assert (await cliente.post(url)).status_code == 401
    for quien in (cliente_a, cliente_b):  # ni el dueno
        r = await cliente.post(url, headers=con(quien))
        assert (r.status_code, codigo(r)) == (403, "sin_permiso")
    assert sql("select estado from public.reserva where id = %s", UUID(id_)) == [("confirmada",)]
    r = await cliente.post(f"{RESERVAS}/{UUID(int=3)}/inasistencia", headers=con(personal))
    assert r.status_code == 404
    futura = reserva_ahora(cliente_a, 3)
    r = await cliente.post(f"{RESERVAS}/{futura}/inasistencia", headers=con(personal))
    assert (r.status_code, codigo(r)) == (409, "tolerancia_no_cumplida")
    final = reserva_ahora(cliente_a, -5, "finalizada")
    r = await cliente.post(f"{RESERVAS}/{final}/inasistencia", headers=con(personal))
    assert (r.status_code, codigo(r)) == (409, "no_aplicable")


async def test_excepcion_convierte_lo_retenido_en_credito_una_sola_vez(
    cliente: AsyncClient,
    cliente_a: UsuarioDePrueba,
    personal: UsuarioDePrueba,
    administrador: UsuarioDePrueba,
    reserva_ahora: Callable[..., str],
    sql: Ejecutar,
) -> None:
    id_ = reserva_ahora(cliente_a)
    await cliente.post(f"{RESERVAS}/{id_}/inasistencia", headers=con(personal))
    url = f"{RESERVAS}/{id_}/excepcion"
    motivo = {"motivo": "El estudio abrio tarde ese dia"}
    for quien in (cliente_a, personal):
        assert (await cliente.post(url, json=motivo, headers=con(quien))).status_code == 403
    assert (await cliente.post(url, json=motivo)).status_code == 401
    for malo in (
        {"motivo": "corto"},
        {"motivo": "x" * 501},
        {},
        {"motivo": "valido de sobra", "x": 1},
    ):
        r = await cliente.post(url, json=malo, headers=con(administrador))
        assert (r.status_code, codigo(r)) == (422, "datos_invalidos"), malo
    r = await cliente.post(url, json=motivo, headers=con(administrador))
    assert r.status_code == 200, r.text
    c = r.json()["cancelacion"]
    assert (c["retenido"], c["credito"]) == ("0.00", "100.00")
    assert c["excepcion"]["motivo"] == motivo["motivo"]
    assert c["excepcion"]["por"]["id"] == str(administrador.id) and c["excepcion"]["en"]
    assert sql("select tipo, saldo from public.credito") == [("excepcion", 100)]
    # El cliente ve la excepcion pero no quien la hizo.
    v = (await cliente.get(f"{RESERVAS}/{id_}", headers=con(cliente_a))).json()
    assert v["cancelacion"]["excepcion"]["por"] is None
    r = await cliente.post(url, json=motivo, headers=con(administrador))
    assert (r.status_code, codigo(r)) == (409, "excepcion_ya_aplicada")


async def test_excepcion_no_aplicable_a_una_reserva_viva(
    cliente: AsyncClient,
    cliente_a: UsuarioDePrueba,
    administrador: UsuarioDePrueba,
    reserva_ahora: Callable[..., str],
) -> None:
    id_ = reserva_ahora(cliente_a)
    r = await cliente.post(
        f"{RESERVAS}/{id_}/excepcion",
        json={"motivo": "Motivo suficientemente largo"},
        headers=con(administrador),
    )
    assert (r.status_code, codigo(r)) == (409, "excepcion_no_aplicable")
    r = await cliente.post(
        f"{RESERVAS}/{UUID(int=4)}/excepcion",
        json={"motivo": "Motivo suficientemente largo"},
        headers=con(administrador),
    )
    assert r.status_code == 404
