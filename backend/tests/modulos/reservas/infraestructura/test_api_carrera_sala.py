"""B3: reservar, cerrar y retirar franja se serializan por sala (bloqueo consultivo)."""

import asyncio
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from typing import Any

import psycopg
import pytest
from httpx import AsyncClient

from bugalu.compartido.configuracion import Configuracion
from tests.conftest import UsuarioDePrueba
from tests.modulos.reservas.infraestructura.conftest import Ejecutar, con

pytestmark = pytest.mark.integracion

Crear = Callable[..., str]
INICIO, FIN = "2027-04-05T10:00:00-05:00", "2027-04-05T12:00:00-05:00"


@contextmanager
def sala_bloqueada(configuracion: Configuracion, sala: str) -> Iterator[Callable[[], None]]:
    """Otra transaccion con el bloqueo de la sala; devuelve la funcion que lo suelta."""
    conexion = psycopg.connect(configuracion.url_base_datos_admin)
    conexion.execute("select pg_advisory_xact_lock(hashtextextended(%s, 0))", (sala,))
    try:
        yield conexion.commit
    finally:
        conexion.close()


@pytest.fixture
def voces(sql: Ejecutar) -> str:
    return str(sql("select id from public.servicio where nombre = 'Grabación de voces'")[0][0])


@pytest.fixture
def peticion(
    cliente: AsyncClient,
    sala: str,
    voces: str,
    franja: Crear,
    cliente_a: UsuarioDePrueba,
    administrador: UsuarioDePrueba,
) -> dict[str, Callable[[], Any]]:
    id_franja = franja("2027-04-05 08:00-05", "2027-04-05 20:00-05")
    cierre = {"id_sala": sala, "inicio": INICIO, "fin": FIN, "motivo": "Mantenimiento"}
    reserva = {
        "id_sala": sala,
        "id_servicio": voces,
        "inicio": INICIO,
        "fin": FIN,
        "especialistas": [],
    }
    return {
        "reservar": lambda: cliente.post("/api/v1/reservas", json=reserva, headers=con(cliente_a)),
        "cerrar": lambda: cliente.post("/api/v1/cierres", json=cierre, headers=con(administrador)),
        "retirar": lambda: cliente.delete(
            f"/api/v1/franjas/{id_franja}", headers=con(administrador)
        ),
    }


@pytest.mark.parametrize("operacion", ["reservar", "cerrar", "retirar"])
async def test_cada_operacion_espera_el_bloqueo_de_la_sala(
    operacion: str,
    peticion: dict[str, Callable[[], Any]],
    configuracion: Configuracion,
    sala: str,
) -> None:
    with sala_bloqueada(configuracion, sala) as soltar:
        tarea = asyncio.ensure_future(peticion[operacion]())
        await asyncio.sleep(1.5)
        esperaba = not tarea.done()
        soltar()
        respuesta = await asyncio.wait_for(tarea, 10)
    assert esperaba, "la operacion no espero el bloqueo de la sala"
    assert respuesta.status_code in (201, 204), respuesta.text


async def test_reservar_y_cerrar_a_la_vez_nunca_dejan_una_reserva_vigente_dentro_del_cierre(
    peticion: dict[str, Callable[[], Any]], sql: Ejecutar, sala: str
) -> None:
    for _ in range(12):
        rs = await asyncio.gather(peticion["reservar"](), peticion["cerrar"]())
        assert all(r.status_code in (201, 409, 422) for r in rs), [r.text for r in rs]
        dentro = sql(
            "select count(*) from public.reserva r "
            "join public.cierre_sala c on c.id_sala = r.id_sala "
            "and tstzrange(c.inicio, c.fin) && tstzrange(r.inicio, r.fin_buffer) "
            "where r.estado <> 'cancelada' and r.inicio >= '2027-01-01' and r.inicio < '2028-01-01'"
        )
        assert dentro == [(0,)]
        sql("delete from public.reserva where inicio >= '2027-01-01' and inicio < '2028-01-01'")
        sql("delete from public.cierre_sala where inicio >= '2027-01-01' and inicio < '2028-01-01'")


async def test_reservar_no_espera_a_un_patch_de_especialistas_en_curso(
    peticion: dict[str, Callable[[], Any]], configuracion: Configuracion, voces: str
) -> None:
    from uuid import UUID

    from bugalu.modulos.catalogo.infraestructura.salida.repositorio_postgres import (
        RepositorioCatalogoPostgres,
    )

    # Transaccion abierta con el bloqueo del servicio que toma el PATCH (sin commit).
    async with await psycopg.AsyncConnection.connect(configuracion.url_base_datos_admin) as c:
        await RepositorioCatalogoPostgres(c).reemplazar_especialistas_por_defecto(UUID(voces), [])
        respuesta = await asyncio.wait_for(peticion["reservar"](), 5)
        await c.rollback()
    assert respuesta.status_code == 201, respuesta.text
