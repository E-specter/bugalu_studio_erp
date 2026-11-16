"""API de RF-06 (CA-01 a CA-03): transiciones de la base vistas por la API, con un aviso."""

from collections.abc import Callable, Iterator
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
def pasada(sql: Ejecutar, reservar: Callable[..., str]) -> Iterator[Callable[..., str]]:
    """Reserva confirmada con el reloj simulado: `desde`/`hasta` son horas respecto de ahora.

    Se crea en 2027 (sin solapes) y se mueve al pasado; al final se borra por id.
    """
    ids: list[str] = []

    def crear(usuario: UsuarioDePrueba, desde: int, hasta: int, estado: str = "confirmada") -> str:
        id_ = reservar(usuario.id, "2027-07-01T10:00:00-05:00", "2027-07-01T12:00:00-05:00", estado)
        ids.append(id_)
        sql(
            "update public.reserva set precio = %s::jsonb, "
            "inicio = date_trunc('hour', now()) + make_interval(hours => %s), "
            "fin = date_trunc('hour', now()) + make_interval(hours => %s), "
            "fin_buffer = date_trunc('hour', now()) + make_interval(hours => %s, mins => 30), "
            "vence_pago = now() + interval '1 day' where id = %s",
            PRECIO,
            desde,
            hasta,
            hasta,
            UUID(id_),
        )
        sql(
            "insert into public.cuota (id_reserva, hito, monto) values (%s, 'al_terminar', 40)",
            UUID(id_),
        )
        return id_

    yield crear
    for id_ in ids:
        sql("delete from public.reserva where id = %s", UUID(id_))


async def _estado(cliente: AsyncClient, usuario: UsuarioDePrueba, id_: str) -> str:
    r = await cliente.get(f"{RESERVAS}/{id_}", headers=con(usuario))
    assert r.status_code == 200, r.text
    return str(r.json()["estado"])


async def test_la_confirmada_pasa_a_en_curso_y_luego_a_finalizada_vista_por_la_api(
    cliente: AsyncClient, cliente_a: UsuarioDePrueba, pasada: Callable[..., str], sql: Ejecutar
) -> None:
    en_su_hora = pasada(cliente_a, -1, 7)
    terminada = pasada(cliente_a, -9, -2)
    sql("select public.avanzar_reservas()")
    assert await _estado(cliente, cliente_a, en_su_hora) == "en_curso"
    assert await _estado(cliente, cliente_a, terminada) == "finalizada"
    mias = (await cliente.get(f"{RESERVAS}/mias", headers=con(cliente_a))).json()
    assert {r["estado"] for r in mias} == {"en_curso", "finalizada"}
    # la reserva en curso ya no se cancela y nunca da 500
    r = await cliente.post(f"{RESERVAS}/{en_su_hora}/cancelar", headers=con(cliente_a))
    assert r.status_code == 409 and r.json()["error"]["codigo"] == "no_cancelable"


async def test_la_pre_reservada_no_avanza_aunque_haya_pasado_su_hora(
    cliente: AsyncClient, cliente_a: UsuarioDePrueba, pasada: Callable[..., str], sql: Ejecutar
) -> None:
    id_ = pasada(cliente_a, -3, -2, "pre_reservada")
    sql("select public.avanzar_reservas()")
    assert await _estado(cliente, cliente_a, id_) == "pre_reservada"


async def test_al_finalizar_con_saldo_se_avisa_una_sola_vez(
    cliente: AsyncClient, cliente_a: UsuarioDePrueba, pasada: Callable[..., str], sql: Ejecutar
) -> None:
    id_ = pasada(cliente_a, -3, -2)
    for _ in range(3):
        sql("select public.avanzar_reservas()")
    avisos: list[Any] = sql(
        "select destinatario, datos ->> 'saldo' from public.notificacion "
        "where tipo = 'reserva_finalizada_saldo' and datos ->> 'id_reserva' = %s",
        id_,
    )
    assert avisos == [(cliente_a.correo, "40.00")]
