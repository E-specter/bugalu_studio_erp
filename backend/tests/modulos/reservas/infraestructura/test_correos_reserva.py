"""RF-04 CA-06: los avisos de la bandeja llegan por SMTP (Mailpit del stack local)."""

import os
from collections.abc import Callable, Iterator
from decimal import Decimal
from typing import Any

import httpx
import pytest
from fastapi import FastAPI
from httpx import AsyncClient

from bugalu.compartido.configuracion import Configuracion
from bugalu.modulos.notificaciones.dominio.redaccion import formatear_soles
from bugalu.modulos.notificaciones.infraestructura.entrada.ejecucion import enviar_una_vez
from tests.conftest import UsuarioDePrueba
from tests.modulos.reservas.infraestructura.conftest import Ejecutar, con
from tests.modulos.reservas.infraestructura.test_api_reservar import (  # noqa: F401
    catalogo,
    dia,
)
from tests.modulos.reservas.infraestructura.test_api_reservar import (
    reservar as reservar_por_api,
)

pytestmark = pytest.mark.integracion

MAILPIT = os.environ.get("URL_MAILPIT", "http://127.0.0.1:45624") + "/api/v1"


@pytest.fixture
def correos_de(request: pytest.FixtureRequest) -> Iterator[Callable[[str], list[dict[str, Any]]]]:
    """Mensajes de Mailpit para un destinatario; los borra al terminar."""
    destinatarios: list[str] = []

    def buscar(correo: str) -> list[dict[str, Any]]:
        destinatarios.append(correo)
        r = httpx.get(f"{MAILPIT}/search", params={"query": f"to:{correo}"})
        return [  # type: ignore[no-any-return]
            httpx.get(f"{MAILPIT}/message/{m['ID']}").json() for m in r.json()["messages"]
        ]

    yield buscar
    for correo in destinatarios:
        httpx.request("DELETE", f"{MAILPIT}/search", params={"query": f"to:{correo}"})


async def test_la_reserva_creada_llega_con_folio_y_fecha_limite(
    app: FastAPI,
    cliente: AsyncClient,
    configuracion: Configuracion,
    dia: str,  # noqa: F811
    sala: str,
    catalogo: dict[str, str],  # noqa: F811
    cliente_a: UsuarioDePrueba,
    correos_de: Callable[[str], list[dict[str, Any]]],
    sql: Ejecutar,
) -> None:
    r = await reservar_por_api(cliente, cliente_a, sala, catalogo["Grabación de voces"])
    assert r.status_code == 201
    assert await enviar_una_vez(app.state.pool, configuracion) == 1
    [correo] = correos_de(cliente_a.correo)
    assert r.json()["folio"] in correo["Subject"]
    assert r.json()["folio"] in correo["Text"]
    assert "Fecha límite de pago" in correo["Text"] and "caducará" in correo["Text"]
    assert "10 de marzo de 2027" in correo["Text"]
    assert "Datos para pagar" in correo["Text"]  # metodos activos de la semilla
    assert sql("select enviada_en is not null from public.notificacion") == [(True,)]


async def test_la_reserva_caducada_avisa_que_el_horario_se_libero(
    app: FastAPI,
    configuracion: Configuracion,
    cliente_a: UsuarioDePrueba,
    reservar: Callable[..., str],
    correos_de: Callable[[str], list[dict[str, Any]]],
    sql: Ejecutar,
) -> None:
    id_ = reservar(
        cliente_a.id, "2027-03-01 09:00-05", "2027-03-01 10:00-05", "pre_reservada", "2020-01-01"
    )
    assert sql("select public.caducar_reservas()") == [(1,)]
    assert await enviar_una_vez(app.state.pool, configuracion) == 1
    [correo] = correos_de(cliente_a.correo)
    [(folio,)] = sql("select folio from public.reserva where id = %s", id_)
    assert folio in correo["Subject"] and "liberó" in correo["Text"]


async def test_el_saldo_al_finalizar_y_las_cancelaciones_llegan_por_correo(
    app: FastAPI,
    cliente: AsyncClient,
    configuracion: Configuracion,
    cliente_a: UsuarioDePrueba,
    administrador: UsuarioDePrueba,
    reservar: Callable[..., str],
    correos_de: Callable[[str], list[dict[str, Any]]],
    sql: Ejecutar,
    request: pytest.FixtureRequest,
) -> None:
    # Saldo al finalizar: reserva ya terminada (tiempo simulado) con la cuota al_terminar pendiente.
    terminada = reservar(
        cliente_a.id, "2027-03-02 09:00-05", "2027-03-02 10:00-05", "confirmada", "2099-01-01"
    )
    # fuera de 2027: la limpieza automatica no la alcanza
    request.addfinalizer(lambda: sql("delete from public.reserva where id = %s", terminada))
    sql(
        "update public.reserva set inicio = '2020-01-01 09:00-05', fin = '2020-01-01 10:00-05', "
        "fin_buffer = '2020-01-01 10:30-05' where id = %s",
        terminada,
    )
    sql(
        "insert into public.cuota (id_reserva, hito, monto) values (%s, 'al_terminar', 1250)",
        terminada,
    )
    sql("select public.avanzar_reservas()")
    # Cancelada por el estudio (con nota) y por el cliente (aviso a administradores).
    por_estudio = reservar(
        cliente_a.id, "2027-03-03 09:00-05", "2027-03-03 10:00-05", "pre_reservada", "2099-01-01"
    )
    por_cliente = reservar(
        cliente_a.id, "2027-03-04 09:00-05", "2027-03-04 10:00-05", "pre_reservada", "2099-01-01"
    )
    sql(
        "update public.reserva set precio = %s::jsonb where id in (%s, %s)",
        '{"lineas": [], "recargos": [], "total": "50", "anticipo": "25"}',
        por_estudio,
        por_cliente,
    )
    r = await cliente.post(
        f"/api/v1/reservas/{por_estudio}/cancelar",
        json={"nota": "Averia en la sala"},
        headers=con(administrador),
    )
    assert r.status_code == 200, r.text
    r = await cliente.post(f"/api/v1/reservas/{por_cliente}/cancelar", headers=con(cliente_a))
    assert r.status_code == 200, r.text
    while await enviar_una_vez(app.state.pool, configuracion):  # varios administradores: >1 lote
        pass

    textos = [c["Text"] for c in correos_de(cliente_a.correo)]
    saldo = next(t for t in textos if "saldo pendiente" in t)
    assert formatear_soles(Decimal(1250)) in saldo
    assert "Datos para pagar" in saldo
    assert any("Nota del estudio: Averia en la sala" in t for t in textos)
    [aviso] = [
        c for c in correos_de(administrador.correo) if "cancelada por el cliente" in c["Subject"]
    ]
    assert "Ana Torres" in aviso["Text"] and "4 de marzo de 2027" in aviso["Text"]
