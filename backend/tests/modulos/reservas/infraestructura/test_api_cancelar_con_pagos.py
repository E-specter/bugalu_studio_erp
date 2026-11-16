"""API de RF-06 (CA-04): cancelar con nota, avisos y visibilidad de la nota (RLS real)."""

from collections.abc import Callable
from typing import Any
from uuid import UUID

import pytest
from httpx import AsyncClient

from tests.conftest import UsuarioDePrueba
from tests.modulos.reservas.infraestructura.conftest import Ejecutar, con

pytestmark = pytest.mark.integracion

RESERVAS = "/api/v1/reservas"
PRECIO = '{"lineas": [], "recargos": [], "total": "50", "anticipo": "25"}'


@pytest.fixture
def reserva_de(sql: Ejecutar, reservar: Callable[..., str]) -> Callable[..., str]:
    """Reserva (2027) del cliente con su cuota `al_reservar`, pagada o no."""
    dias = iter(range(1, 28))

    def crear(usuario: UsuarioDePrueba, estado: str = "pre_reservada", pagada: bool = False) -> str:
        dia = next(dias)
        id_ = reservar(
            usuario.id,
            f"2027-06-{dia:02d}T10:00:00-05:00",
            f"2027-06-{dia:02d}T12:00:00-05:00",
            estado,
        )
        sql("update public.reserva set precio = %s::jsonb where id = %s", PRECIO, UUID(id_))
        sql(
            "insert into public.cuota (id_reserva, hito, monto, estado) "
            "values (%s, 'al_reservar', 25, %s)",
            UUID(id_),
            "pagada" if pagada else "pendiente",
        )
        return id_

    return crear


def codigo(r: Any) -> str:
    return str(r.json()["error"]["codigo"])


async def test_el_administrador_cancela_con_pagos_con_nota_y_avisa_al_cliente(
    cliente: AsyncClient,
    cliente_a: UsuarioDePrueba,
    administrador: UsuarioDePrueba,
    reserva_de: Callable[..., str],
    sql: Ejecutar,
) -> None:
    id_ = reserva_de(cliente_a, "confirmada", pagada=True)
    r = await cliente.post(
        f"{RESERVAS}/{id_}/cancelar",
        json={"nota": "  Reembolso de S/ 25 por yape  "},
        headers=con(administrador),
    )
    assert r.status_code == 200, r.text
    assert (r.json()["estado"], r.json()["motivo_cancelacion"]) == ("cancelada", "administrador")
    assert r.json()["nota_cancelacion"] == "Reembolso de S/ 25 por yape"
    [(destinatario, datos)] = sql(
        "select destinatario, datos from public.notificacion "
        "where tipo = 'reserva_cancelada_estudio'"
    )
    assert destinatario == cliente_a.correo and datos["nota"] == "Reembolso de S/ 25 por yape"


async def test_la_nota_la_ven_el_dueno_y_el_administrador_pero_no_el_personal_ni_otros(
    cliente: AsyncClient,
    cliente_a: UsuarioDePrueba,
    cliente_b: UsuarioDePrueba,
    administrador: UsuarioDePrueba,
    personal: UsuarioDePrueba,
    reserva_de: Callable[..., str],
) -> None:
    id_ = reserva_de(cliente_a, pagada=True)
    await cliente.post(
        f"{RESERVAS}/{id_}/cancelar", json={"nota": "Se devuelve todo"}, headers=con(administrador)
    )
    for quien in (cliente_a, administrador):
        r = await cliente.get(f"{RESERVAS}/{id_}", headers=con(quien))
        assert r.json()["nota_cancelacion"] == "Se devuelve todo"
    r = await cliente.get(f"{RESERVAS}/{id_}", headers=con(personal))
    assert r.status_code == 200 and r.json()["nota_cancelacion"] is None
    r = await cliente.get(f"{RESERVAS}/{id_}", headers=con(cliente_b))
    assert r.status_code == 403
    r = await cliente.get(f"{RESERVAS}/mias", headers=con(cliente_a))
    assert [x["nota_cancelacion"] for x in r.json()] == ["Se devuelve todo"]


async def test_sin_pagos_la_nota_es_opcional_y_sin_cuerpo_sigue_funcionando(
    cliente: AsyncClient,
    cliente_a: UsuarioDePrueba,
    administrador: UsuarioDePrueba,
    reserva_de: Callable[..., str],
) -> None:
    sin_cuerpo, vacio, con_nota = (reserva_de(cliente_a) for _ in range(3))
    r = await cliente.post(f"{RESERVAS}/{sin_cuerpo}/cancelar", headers=con(administrador))
    assert r.status_code == 200 and r.json()["nota_cancelacion"] is None
    r = await cliente.post(f"{RESERVAS}/{vacio}/cancelar", json={}, headers=con(cliente_a))
    assert r.status_code == 200 and r.json()["nota_cancelacion"] is None
    r = await cliente.post(
        f"{RESERVAS}/{con_nota}/cancelar", json={"nota": "Cambio de planes"}, headers=con(cliente_a)
    )
    assert r.status_code == 200 and r.json()["nota_cancelacion"] == "Cambio de planes"


async def test_cuando_cancela_el_cliente_avisa_a_los_administradores(
    cliente: AsyncClient,
    cliente_a: UsuarioDePrueba,
    administrador: UsuarioDePrueba,
    reserva_de: Callable[..., str],
    sql: Ejecutar,
) -> None:
    id_ = reserva_de(cliente_a)
    r = await cliente.post(f"{RESERVAS}/{id_}/cancelar", headers=con(cliente_a))
    assert r.status_code == 200
    assert sql("select 1 from public.notificacion where tipo = 'reserva_cancelada_estudio'") == []
    avisos = sql(
        "select destinatario, datos ->> 'cliente' from public.notificacion "
        "where tipo = 'reserva_cancelada_cliente'"
    )
    assert (administrador.correo, "Ana Torres") in avisos
    assert all(d != cliente_a.correo for d, _ in avisos)


@pytest.mark.parametrize(
    "cuerpo",
    [
        {"nota": "x" * 301},
        {"nota": "   "},
        {"nota": ""},
        {"nota": "con\x07control"},
        {"nota": 5},
        {"nota": None},
        {"otro": "campo"},
        [],
    ],
)
async def test_nota_invalida_da_422_y_no_cancela(
    cliente: AsyncClient,
    cliente_a: UsuarioDePrueba,
    administrador: UsuarioDePrueba,
    reserva_de: Callable[..., str],
    sql: Ejecutar,
    cuerpo: Any,
) -> None:
    id_ = reserva_de(cliente_a, pagada=True)
    r = await cliente.post(f"{RESERVAS}/{id_}/cancelar", json=cuerpo, headers=con(administrador))
    assert r.status_code == 422 and codigo(r) == "datos_invalidos", r.text
    assert sql("select estado from public.reserva where id = %s", UUID(id_)) == [("pre_reservada",)]


async def test_un_cuerpo_que_no_es_json_da_422_y_nunca_500(
    cliente: AsyncClient,
    cliente_a: UsuarioDePrueba,
    reserva_de: Callable[..., str],
) -> None:
    id_ = reserva_de(cliente_a)
    r = await cliente.post(
        f"{RESERVAS}/{id_}/cancelar",
        content=b"{no es json",
        headers={**con(cliente_a), "Content-Type": "application/json"},
    )
    assert r.status_code == 422 and codigo(r) == "datos_invalidos"
