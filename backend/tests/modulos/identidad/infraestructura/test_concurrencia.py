"""Carreras reales entre dos transacciones (dos conexiones `bugalu_api`, READ COMMITTED)."""

import asyncio
import json
import threading
import time
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from typing import Any
from uuid import UUID

import psycopg
import pytest
from httpx import AsyncClient

from bugalu.compartido.configuracion import Configuracion
from tests.conftest import UsuarioDePrueba

pytestmark = pytest.mark.integracion

CrearUsuario = Callable[[], UsuarioDePrueba]
PonerRol = Callable[[UsuarioDePrueba, str, str | None], None]


@contextmanager
def _dos_administradores(
    crear: CrearUsuario, poner_rol: PonerRol, configuracion: Configuracion
) -> Iterator[tuple[UsuarioDePrueba, UsuarioDePrueba]]:
    """Deja solo a dos administradores de prueba y restaura a los reales al salir."""
    a, b = crear(), crear()
    poner_rol(a, "administrador", None)
    poner_rol(b, "administrador", None)
    with psycopg.connect(configuracion.url_base_datos_admin) as conexion:
        reales = [
            fila[0]
            for fila in conexion.execute(
                "update public.usuario set rol = 'cliente' "
                "where rol = 'administrador' and id <> all(%s) returning id",
                ([a.id, b.id],),
            )
        ]
    try:
        yield a, b
    finally:
        # Ascender no choca con el trigger del ultimo administrador.
        with psycopg.connect(configuracion.url_base_datos_admin) as conexion:
            conexion.execute(
                "update public.usuario set rol = 'administrador' where id = any(%s)", (reales,)
            )


def _como(conexion: psycopg.Connection[Any], quien: UsuarioDePrueba) -> None:
    conexion.execute("set local role authenticated")
    conexion.execute(
        "select set_config('request.jwt.claims', %s, true)", (json.dumps({"sub": str(quien.id)}),)
    )


def _administradores(configuracion: Configuracion, ids: list[UUID]) -> int:
    with psycopg.connect(configuracion.url_base_datos_admin) as conexion:
        fila = conexion.execute(
            "select count(*) from public.usuario where rol = 'administrador' and id = any(%s)",
            (ids,),
        ).fetchone()
    assert fila
    return int(fila[0])


def test_dos_administradores_que_se_quitan_el_rol_a_la_vez_no_dejan_cero(
    crear_usuario: CrearUsuario, poner_rol: PonerRol, configuracion: Configuracion
) -> None:
    with _dos_administradores(crear_usuario, poner_rol, configuracion) as (a, b):
        errores: list[str] = []
        with (
            psycopg.connect(configuracion.url_base_datos) as primera,
            psycopg.connect(configuracion.url_base_datos) as segunda,
        ):
            _como(primera, a)
            primera.execute("select public.asignar_rol(%s, 'cliente', null)", (b.id,))

            def segunda_transaccion() -> None:
                try:
                    _como(segunda, b)
                    segunda.execute("select public.asignar_rol(%s, 'cliente', null)", (a.id,))
                    segunda.commit()
                except psycopg.Error as error:
                    errores.append(error.sqlstate or "")
                    segunda.rollback()

            hilo = threading.Thread(target=segunda_transaccion)
            hilo.start()
            time.sleep(1)  # la segunda corre mientras la primera sigue abierta
            primera.commit()
            hilo.join(timeout=10)

        assert errores == ["BG001"]
        assert _administradores(configuracion, [a.id, b.id]) == 1


async def test_dos_administradores_que_aprueban_a_la_vez_la_misma_solicitud_solo_una_vale(
    cliente: AsyncClient,
    crear_usuario: CrearUsuario,
    poner_rol: PonerRol,
    configuracion: Configuracion,
) -> None:
    admin1, admin2, solicitante = crear_usuario(), crear_usuario(), crear_usuario()
    poner_rol(admin1, "administrador", None)
    poner_rol(admin2, "administrador", None)
    h = {"Authorization": f"Bearer {solicitante.token}"}
    creada = await cliente.post("/api/v1/solicitudes-acceso", headers=h, json={"especialidad": "x"})
    ruta = f"/api/v1/solicitudes-acceso/{creada.json()['id']}/aprobar"
    cuerpo = {"rol": "personal", "especialidad": "ingenieria"}
    respuestas = await asyncio.gather(
        *(
            cliente.post(ruta, headers={"Authorization": f"Bearer {u.token}"}, json=cuerpo)
            for u in (admin1, admin2)
        )
    )
    assert sorted(r.status_code for r in respuestas) == [200, 409]
    with psycopg.connect(configuracion.url_base_datos_admin) as conexion:
        fila = conexion.execute(
            "select count(*) filter (where estado = 'aprobada'), count(*) "
            "from public.solicitud_acceso where id_usuario = %s",
            (solicitante.id,),
        ).fetchone()
    assert fila == (1, 1)


def test_la_prueba_restaura_a_los_administradores_reales(
    crear_usuario: CrearUsuario, poner_rol: PonerRol, configuracion: Configuracion
) -> None:
    real = crear_usuario()
    poner_rol(real, "administrador", None)
    with _dos_administradores(crear_usuario, poner_rol, configuracion):
        assert _administradores(configuracion, [real.id]) == 0
    assert _administradores(configuracion, [real.id]) == 1
