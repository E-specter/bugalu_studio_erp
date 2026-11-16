"""Carrera entre registrar un pago sin confirmar y cancelar o caducar la reserva (RN-18, RN-20)."""

import json
import time
from collections.abc import Callable, Iterator
from concurrent.futures import Future, ThreadPoolExecutor
from contextlib import contextmanager
from uuid import UUID

import psycopg
import pytest
from httpx import AsyncClient

from bugalu.compartido.configuracion import Configuracion
from tests.conftest import UsuarioDePrueba
from tests.modulos.pagos.infraestructura.conftest import operacion
from tests.modulos.pagos.infraestructura.test_api_pagos import codigo, pagar
from tests.modulos.reservas.infraestructura.conftest import Ejecutar

pytestmark = pytest.mark.integracion

Cuota = Callable[..., str]


def _como(conexion: psycopg.Connection, usuario: UsuarioDePrueba) -> None:
    conexion.execute("set local role authenticated")
    claims = json.dumps({"sub": str(usuario.id), "role": "authenticated"})
    conexion.execute("select set_config('request.jwt.claims', %s, true)", (claims,))
    conexion.execute("set local lock_timeout = '15s'")


@pytest.fixture
def pago_sin_confirmar(
    configuracion: Configuracion,
) -> Iterator[Callable[[UsuarioDePrueba, str], psycopg.Connection]]:
    """Transaccion abierta con el comprobante ya insertado y sin commit."""
    abiertas: list[psycopg.Connection] = []

    def abrir(usuario: UsuarioDePrueba, cuota: str) -> psycopg.Connection:
        conexion = psycopg.connect(configuracion.url_base_datos_admin)
        abiertas.append(conexion)
        _como(conexion, usuario)
        conexion.execute(
            "insert into public.comprobante_pago (id_cuota, id_cliente, metodo, monto, "
            "numero_operacion, ruta_captura, tipo_captura) "
            "values (%s, %s, 'yape', 25, %s, %s, 'image/png')",
            (UUID(cuota), usuario.id, operacion(), f"{usuario.id}/{operacion()}.png"),
        )
        return conexion

    yield abrir
    for conexion in abiertas:
        conexion.close()


@contextmanager
def _hilo() -> Iterator[ThreadPoolExecutor]:
    with ThreadPoolExecutor(max_workers=1) as pool:
        yield pool


def _cancelar(
    configuracion: Configuracion, usuario: UsuarioDePrueba, reserva: str, nota: str | None
) -> str:
    with psycopg.connect(configuracion.url_base_datos_admin) as c:
        _como(c, usuario)
        try:
            c.execute("select public.cancelar_reserva(%s, %s)", (UUID(reserva), nota))
        except psycopg.errors.RaiseException as error:
            return str(error).strip()
        return "ok"


def _caducar(configuracion: Configuracion) -> int:
    with psycopg.connect(configuracion.url_base_datos_admin) as c:
        return int(c.execute("select public.caducar_reservas()").fetchone()[0])  # type: ignore[index]


def _espera(futuro: Future[object]) -> None:
    time.sleep(1.5)
    assert not futuro.done(), "la operacion no espero a que se confirmara el pago"


def _reserva(sql: Ejecutar, cuota: str) -> str:
    return str(sql("select id_reserva from public.cuota where id = %s", UUID(cuota))[0][0])


def _estado(sql: Ejecutar, reserva: str) -> tuple[str, str | None]:
    f = sql("select estado, motivo_cancelacion from public.reserva where id = %s", UUID(reserva))
    return (f[0][0], f[0][1])


def _vigente(sql: Ejecutar, cuota: str, plazo: str = "1 hour") -> str:
    reserva = _reserva(sql, cuota)
    sql(
        f"update public.reserva set vence_pago = now() + interval '{plazo}' where id = %s",
        UUID(reserva),
    )
    return reserva


def test_cancelar_del_cliente_espera_al_pago_y_recibe_tiene_pagos(
    configuracion: Configuracion,
    cliente_a: UsuarioDePrueba,
    cuota_de: Cuota,
    sql: Ejecutar,
    pago_sin_confirmar: Callable[[UsuarioDePrueba, str], psycopg.Connection],
) -> None:
    cuota = cuota_de(cliente_a, "pre_reservada")
    reserva = _vigente(sql, cuota)
    pago = pago_sin_confirmar(cliente_a, cuota)
    with _hilo() as hilo:
        cancelacion = hilo.submit(_cancelar, configuracion, cliente_a, reserva, None)
        _espera(cancelacion)
        pago.commit()
        assert "tiene_pagos" in cancelacion.result(20)
    assert _estado(sql, reserva) == ("pre_reservada", None)
    assert sql("select estado from public.comprobante_pago")[0][0] == "pendiente_validacion"


def test_caducar_reservas_espera_al_pago_y_no_caduca_la_reserva(
    configuracion: Configuracion,
    cliente_a: UsuarioDePrueba,
    cuota_de: Cuota,
    sql: Ejecutar,
    pago_sin_confirmar: Callable[[UsuarioDePrueba, str], psycopg.Connection],
) -> None:
    cuota = cuota_de(cliente_a, "pre_reservada")
    reserva = _vigente(sql, cuota, "3 seconds")
    pago = pago_sin_confirmar(cliente_a, cuota)  # su transaccion empezo con el plazo aun vigente
    time.sleep(3.2)
    with _hilo() as hilo:
        caducidad = hilo.submit(_caducar, configuracion)
        _espera(caducidad)
        pago.commit()
        assert caducidad.result(20) == 0
    assert _estado(sql, reserva) == ("pre_reservada", None)


def test_el_administrador_que_cancela_espera_al_pago_y_exige_la_nota(
    configuracion: Configuracion,
    cliente_a: UsuarioDePrueba,
    administrador: UsuarioDePrueba,
    cuota_de: Cuota,
    sql: Ejecutar,
    pago_sin_confirmar: Callable[[UsuarioDePrueba, str], psycopg.Connection],
) -> None:
    cuota = cuota_de(cliente_a, "pre_reservada")
    reserva = _vigente(sql, cuota)
    pago = pago_sin_confirmar(cliente_a, cuota)
    with _hilo() as hilo:
        cancelacion = hilo.submit(_cancelar, configuracion, administrador, reserva, None)
        _espera(cancelacion)
        pago.commit()
        assert "nota_requerida" in cancelacion.result(20)
    assert _estado(sql, reserva) == ("pre_reservada", None)
    assert _cancelar(configuracion, administrador, reserva, "Pago duplicado") == "ok"
    assert _estado(sql, reserva) == ("cancelada", "administrador")


async def test_con_el_plazo_vencido_el_pago_es_409_y_la_reserva_caduca_despues(
    cliente: AsyncClient,
    configuracion: Configuracion,
    cliente_a: UsuarioDePrueba,
    cuota_de: Cuota,
    sql: Ejecutar,
) -> None:
    cuota = cuota_de(cliente_a, "pre_reservada")
    reserva = _vigente(sql, cuota, "-1 minute")
    r = await pagar(cliente, cliente_a, cuota)
    assert (r.status_code, codigo(r)) == (409, "cuota_no_pagable")
    assert sql("select count(*) from public.comprobante_pago")[0][0] == 0
    assert _caducar(configuracion) == 1
    assert _estado(sql, reserva) == ("cancelada", "caducada")


def _avanzar(configuracion: Configuracion) -> int:
    with psycopg.connect(configuracion.url_base_datos_admin) as c:
        return int(c.execute("select public.avanzar_reservas()").fetchone()[0])  # type: ignore[index]


def test_avanzar_reservas_espera_al_pago_del_saldo_y_no_avisa_del_saldo(
    configuracion: Configuracion,
    cliente_a: UsuarioDePrueba,
    cuota_de: Cuota,
    sql: Ejecutar,
    pago_sin_confirmar: Callable[[UsuarioDePrueba, str], psycopg.Connection],
) -> None:
    # La reserva ya termino; el cliente paga el saldo (`al_terminar`) y su pago aun no se confirma
    # cuando el cron avanza. Al confirmarse, la finalizacion no debe encolar "saldo pendiente".
    cuota = cuota_de(cliente_a, "en_curso")
    reserva = _reserva(sql, cuota)
    original = sql("select inicio, fin from public.reserva where id = %s", UUID(reserva))[0]
    sql("update public.cuota set hito = 'al_terminar' where id = %s", UUID(cuota))
    sql(
        "update public.reserva set inicio = date_trunc('hour', now()) - interval '3 hours', "
        "fin = date_trunc('hour', now()) - interval '1 hour' where id = %s",  # medias horas exactas
        UUID(reserva),
    )
    pago = pago_sin_confirmar(cliente_a, cuota)
    with _hilo() as hilo:
        avance = hilo.submit(_avanzar, configuracion)
        _espera(avance)
        pago.commit()
        assert avance.result(20) == 1
    assert _estado(sql, reserva)[0] == "finalizada"
    sql(  # de vuelta a 2027: la limpieza de las pruebas borra por anio
        "update public.reserva set inicio = %s, fin = %s where id = %s", *original, UUID(reserva)
    )
    assert sql(
        "select count(*) from public.notificacion where tipo = 'reserva_finalizada_saldo' "
        "and datos->>'id_reserva' = %s",
        reserva,
    ) == [(0,)]
