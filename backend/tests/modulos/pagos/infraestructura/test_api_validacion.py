"""API de RF-05 (validacion del administrador): listar, aprobar y rechazar con la base real."""

import asyncio
from collections.abc import Callable
from datetime import datetime, timedelta
from typing import Any

import pytest
from fastapi import FastAPI
from httpx import AsyncClient

from tests.conftest import UsuarioDePrueba
from tests.modulos.pagos.infraestructura.test_api_pagos import PAGOS, codigo, pagar
from tests.modulos.reservas.infraestructura.conftest import Ejecutar, con

pytestmark = pytest.mark.integracion

Cuota = Callable[..., str]


async def _registrar(
    cliente: AsyncClient, usuario: UsuarioDePrueba, cuota_de: Cuota, estado: str = "confirmada"
) -> dict[str, Any]:
    r = await pagar(cliente, usuario, cuota_de(usuario, estado), monto="30")
    assert r.status_code == 201, r.text
    return dict(r.json())


async def _listar(
    cliente: AsyncClient, admin: UsuarioDePrueba, estado: str | None = None
) -> list[dict[str, Any]]:
    r = await cliente.get(PAGOS, params={"estado": estado} if estado else None, headers=con(admin))
    assert r.status_code == 200, r.text
    return list(r.json())


def _estado_de(sql: Ejecutar, id_pago: str) -> tuple[str, str, str]:
    fila = sql(
        "select p.estado, c.estado, r.estado from public.comprobante_pago p "
        "join public.cuota c on c.id = p.id_cuota join public.reserva r on r.id = c.id_reserva "
        "where p.id = %s",
        id_pago,
    )[0]
    return (fila[0], fila[1], fila[2])


# --- listar --------------------------------------------------------------------------------------


async def test_lista_los_pendientes_del_mas_antiguo_al_mas_reciente_con_cliente(
    cliente: AsyncClient,
    cliente_a: UsuarioDePrueba,
    administrador: UsuarioDePrueba,
    cuota_de: Cuota,
) -> None:
    uno = await _registrar(cliente, cliente_a, cuota_de)
    dos = await _registrar(cliente, cliente_a, cuota_de)
    mios = [p for p in await _listar(cliente, administrador) if p["id"] in (uno["id"], dos["id"])]
    assert [p["id"] for p in mios] == [uno["id"], dos["id"]]
    assert mios[0]["estado"] == "pendiente_validacion"
    assert mios[0]["monto_coincide"] is False
    assert mios[0]["cliente"] == {"id": str(cliente_a.id), "nombre": "Ana Torres"}


async def test_los_validados_van_por_validado_en_descendente(
    cliente: AsyncClient,
    cliente_a: UsuarioDePrueba,
    administrador: UsuarioDePrueba,
    cuota_de: Cuota,
) -> None:
    uno = await _registrar(cliente, cliente_a, cuota_de)
    dos = await _registrar(cliente, cliente_a, cuota_de)
    for pago in (uno, dos):  # `dos` se valida despues: va primero
        r = await cliente.post(f"{PAGOS}/{pago['id']}/aprobar", headers=con(administrador))
        assert r.status_code == 200, r.text
    aprobados = await _listar(cliente, administrador, "aprobado")
    ids = [p["id"] for p in aprobados if p["id"] in (uno["id"], dos["id"])]
    assert ids == [dos["id"], uno["id"]]
    assert all(
        p["estado"] == "rechazado" for p in await _listar(cliente, administrador, "rechazado")
    )


async def test_listar_exige_administrador_y_estado_valido(
    cliente: AsyncClient, cliente_a: UsuarioDePrueba, administrador: UsuarioDePrueba
) -> None:
    r = await cliente.get(PAGOS, headers=con(cliente_a))
    assert (r.status_code, codigo(r)) == (403, "sin_permiso")
    r = await cliente.get(PAGOS, params={"estado": "otro"}, headers=con(administrador))
    assert (r.status_code, codigo(r)) == (422, "datos_invalidos")
    assert (await cliente.get(PAGOS)).status_code == 401


# --- aprobar -------------------------------------------------------------------------------------


async def test_aprobar_al_reservar_confirma_la_reserva_y_detiene_la_caducidad(
    cliente: AsyncClient,
    cliente_a: UsuarioDePrueba,
    administrador: UsuarioDePrueba,
    cuota_de: Cuota,
    sql: Ejecutar,
) -> None:
    pago = await _registrar(cliente, cliente_a, cuota_de, "pre_reservada")
    r = await cliente.post(f"{PAGOS}/{pago['id']}/aprobar", headers=con(administrador))
    assert r.status_code == 200, r.text
    assert r.json()["estado"] == "aprobado"
    assert r.json()["validado_en"] is not None
    assert r.json()["reserva"]["estado"] == "confirmada"
    assert _estado_de(sql, pago["id"]) == ("aprobado", "pagada", "confirmada")
    sql("update public.reserva set vence_pago = '2020-01-01' where id = %s", pago["reserva"]["id"])
    assert sql("select public.caducar_reservas()") == [(0,)]


async def test_aprobar_un_pago_ya_validado_es_409(
    cliente: AsyncClient,
    cliente_a: UsuarioDePrueba,
    administrador: UsuarioDePrueba,
    cuota_de: Cuota,
) -> None:
    pago = await _registrar(cliente, cliente_a, cuota_de)
    url = f"{PAGOS}/{pago['id']}"
    assert (await cliente.post(f"{url}/aprobar", headers=con(administrador))).status_code == 200
    for accion, cuerpo in (("aprobar", None), ("rechazar", {"motivo": "tarde"})):
        r = await cliente.post(f"{url}/{accion}", json=cuerpo, headers=con(administrador))
        assert (r.status_code, codigo(r)) == (409, "pago_ya_validado")


async def test_dos_aprobaciones_o_una_aprobacion_y_un_rechazo_simultaneos_son_200_y_409(
    cliente: AsyncClient,
    cliente_a: UsuarioDePrueba,
    administrador: UsuarioDePrueba,
    cuota_de: Cuota,
) -> None:
    for segunda in ("aprobar", "rechazar"):
        pago = await _registrar(cliente, cliente_a, cuota_de)
        url = f"{PAGOS}/{pago['id']}"
        a, b = await asyncio.gather(
            cliente.post(f"{url}/aprobar", headers=con(administrador)),
            cliente.post(f"{url}/{segunda}", json={"motivo": "x"}, headers=con(administrador)),
        )
        assert sorted([a.status_code, b.status_code]) == [200, 409], (a.text, b.text)


async def test_un_cliente_no_valida_y_la_fila_queda_intacta(
    cliente: AsyncClient, cliente_a: UsuarioDePrueba, cuota_de: Cuota, sql: Ejecutar
) -> None:
    pago = await _registrar(cliente, cliente_a, cuota_de)
    url = f"{PAGOS}/{pago['id']}"
    for accion in ("aprobar", "rechazar"):
        r = await cliente.post(f"{url}/{accion}", json={"motivo": "x"}, headers=con(cliente_a))
        assert (r.status_code, codigo(r)) == (403, "sin_permiso")
    assert _estado_de(sql, pago["id"])[0] == "pendiente_validacion"
    assert (await cliente.post(f"{url}/aprobar")).status_code == 401


async def test_validar_un_pago_inexistente_es_404(
    cliente: AsyncClient, administrador: UsuarioDePrueba
) -> None:
    inexistente = f"{PAGOS}/00000000-0000-0000-0000-00000000dead"
    for accion in ("aprobar", "rechazar"):
        r = await cliente.post(
            f"{inexistente}/{accion}", json={"motivo": "x"}, headers=con(administrador)
        )
        assert (r.status_code, codigo(r)) == (404, "no_encontrado")


async def test_pago_de_reserva_cancelada_se_aprueba_sin_reabrirla(
    cliente: AsyncClient,
    cliente_a: UsuarioDePrueba,
    administrador: UsuarioDePrueba,
    cuota_de: Cuota,
    sql: Ejecutar,
) -> None:
    pago = await _registrar(cliente, cliente_a, cuota_de, "pre_reservada")
    sql(
        "update public.reserva set estado = 'cancelada', motivo_cancelacion = 'administrador' "
        "where id = %s",
        pago["reserva"]["id"],
    )
    assert any(p["id"] == pago["id"] for p in await _listar(cliente, administrador))
    r = await cliente.post(f"{PAGOS}/{pago['id']}/aprobar", headers=con(administrador))
    assert r.status_code == 200, r.text
    assert _estado_de(sql, pago["id"]) == ("aprobado", "pagada", "cancelada")


# --- rechazar ------------------------------------------------------------------------------------


async def test_rechazar_devuelve_el_plazo_y_permite_registrar_otro_pago(
    cliente: AsyncClient,
    cliente_a: UsuarioDePrueba,
    administrador: UsuarioDePrueba,
    cuota_de: Cuota,
    sql: Ejecutar,
) -> None:
    pago = await _registrar(cliente, cliente_a, cuota_de, "pre_reservada")
    sql(
        "update public.reserva set vence_pago = now() + interval '1 minute' where id = %s",
        pago["reserva"]["id"],
    )
    r = await cliente.post(
        f"{PAGOS}/{pago['id']}/rechazar",
        json={"motivo": "  Monto errado "},
        headers=con(administrador),
    )
    assert r.status_code == 200, r.text
    assert (r.json()["estado"], r.json()["motivo_rechazo"]) == ("rechazado", "Monto errado")
    assert _estado_de(sql, pago["id"]) == ("rechazado", "pendiente", "pre_reservada")
    horas = sql("select valor from public.parametro where clave = 'horas_limite_pago'")[0][0]
    vence: datetime = sql(
        "select vence_pago from public.reserva where id = %s", pago["reserva"]["id"]
    )[0][0]
    ahora: datetime = sql("select now()")[0][0]
    assert vence >= ahora + timedelta(hours=horas) - timedelta(minutes=5)  # RN-18
    otro = await pagar(cliente, cliente_a, pago["cuota"]["id"])
    assert otro.status_code == 201, otro.text


@pytest.mark.parametrize("motivo", ["", "   ", "x" * 301, "a\x00b", "a\x07b"])
async def test_motivo_invalido_es_422_con_campo_y_no_cambia_el_pago(
    cliente: AsyncClient,
    cliente_a: UsuarioDePrueba,
    administrador: UsuarioDePrueba,
    cuota_de: Cuota,
    sql: Ejecutar,
    motivo: str,
) -> None:
    pago = await _registrar(cliente, cliente_a, cuota_de)
    r = await cliente.post(
        f"{PAGOS}/{pago['id']}/rechazar", json={"motivo": motivo}, headers=con(administrador)
    )
    assert (r.status_code, codigo(r)) == (422, "datos_invalidos")
    assert r.json()["error"]["detalles"]["campo"] == "motivo"
    assert _estado_de(sql, pago["id"])[0] == "pendiente_validacion"


async def test_el_motivo_de_300_caracteres_se_acepta(
    cliente: AsyncClient,
    cliente_a: UsuarioDePrueba,
    administrador: UsuarioDePrueba,
    cuota_de: Cuota,
) -> None:
    pago = await _registrar(cliente, cliente_a, cuota_de)
    r = await cliente.post(
        f"{PAGOS}/{pago['id']}/rechazar", json={"motivo": "x" * 300}, headers=con(administrador)
    )
    assert r.status_code == 200, r.text


async def test_openapi_declara_respuesta_error_en_la_validacion(app: FastAPI) -> None:
    esquema = app.openapi()["paths"]
    esperados = {
        ("get", "/api/v1/pagos"): {"200", "401", "403", "422", "503"},
        ("post", "/api/v1/pagos/{id_pago}/aprobar"): {"200", "401", "403", "404", "409", "503"},
        ("post", "/api/v1/pagos/{id_pago}/rechazar"): {
            "200",
            "401",
            "403",
            "404",
            "409",
            "422",
            "503",
        },
    }
    for (metodo, ruta), codigos in esperados.items():
        respuestas = esquema[ruta][metodo]["responses"]
        assert codigos <= set(respuestas), (ruta, set(respuestas))
        for c in codigos - {"200"}:
            assert respuestas[c]["content"]["application/json"]["schema"]["$ref"].endswith(
                "RespuestaError"
            ), (ruta, c)
