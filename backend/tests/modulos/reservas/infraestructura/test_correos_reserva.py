"""RF-04 CA-06: los avisos de la bandeja llegan por SMTP (Mailpit del stack local)."""

import os
from collections.abc import Callable, Iterator
from typing import Any

import httpx
import pytest
from fastapi import FastAPI
from httpx import AsyncClient

from bugalu.compartido.configuracion import Configuracion
from bugalu.modulos.notificaciones.infraestructura.entrada.ejecucion import enviar_una_vez
from tests.conftest import UsuarioDePrueba
from tests.modulos.reservas.infraestructura.conftest import Ejecutar
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
