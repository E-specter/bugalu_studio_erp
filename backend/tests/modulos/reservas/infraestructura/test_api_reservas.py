"""API de RF-03: salas, disponibilidad, franjas, cierres y parametros (stack local con RLS real)."""

from collections.abc import Callable
from datetime import UTC, datetime, timedelta, timezone
from typing import Any

import pytest
from fastapi import FastAPI
from httpx import AsyncClient

from tests.conftest import UsuarioDePrueba
from tests.modulos.reservas.infraestructura.conftest import Ejecutar, con

pytestmark = pytest.mark.integracion

LIMA = timezone(timedelta(hours=-5))
DIA = {"desde": "2027-03-01T00:00:00-05:00", "hasta": "2027-03-02T00:00:00-05:00"}
Crear = Callable[..., str]


def tramo(dia: int, h1: int, h2: int, mes: int = 3) -> dict[str, str]:
    return {
        "inicio": datetime(2027, mes, dia, h1, tzinfo=LIMA).isoformat(),
        "fin": datetime(2027, mes, dia, h2, tzinfo=LIMA).isoformat(),
    }


async def disponibilidad(
    cliente: AsyncClient, sala: str, cabeceras: dict[str, str] | None = None, **rango: str
) -> Any:
    return await cliente.get(
        "/api/v1/disponibilidad", params={"sala": sala, **(rango or DIA)}, headers=cabeceras
    )


# --- salas ---------------------------------------------------------------------------------------


async def test_las_salas_son_publicas_y_traen_la_de_la_molina(cliente: AsyncClient) -> None:
    r = await cliente.get("/api/v1/salas")
    assert r.status_code == 200
    [sala] = r.json()
    assert set(sala) == {"id", "nombre", "sede", "aforo", "itse"} and sala["sede"] == "La Molina"


# --- disponibilidad: visibilidad ----------------------------------------------------------------


@pytest.fixture
def escenario(franja: Crear, reservar: Crear, cliente_a: UsuarioDePrueba) -> str:
    """Franja 08-12 y una reserva confirmada de la cliente A de 09:00 a 10:00 (buffer a 10:30)."""
    franja("2027-03-01 08:00-05", "2027-03-01 12:00-05")
    return reservar(cliente_a.id, "2027-03-01 09:00-05", "2027-03-01 10:00-05")


async def test_el_visitante_ve_ocupado_sin_datos_de_nadie(
    cliente: AsyncClient, sala: str, escenario: str, cliente_a: UsuarioDePrueba
) -> None:
    r = await disponibilidad(cliente, sala)
    assert r.status_code == 200
    cuerpo = r.json()
    assert set(cuerpo) == {"limites", "franjas", "ocupados", "cierres", "dias"}
    [franja] = cuerpo["franjas"]
    assert set(franja) == {"id", "inicio", "fin"}
    [ocupado] = cuerpo["ocupados"]
    assert set(ocupado) == {"inicio", "fin", "propia"} and ocupado["propia"] is False
    assert datetime.fromisoformat(ocupado["fin"]) - datetime.fromisoformat(ocupado["inicio"]) == (
        timedelta(minutes=90)
    )
    assert cuerpo["dias"] == [{"fecha": "2027-03-01", "minutos_libres": 90}]
    for secreto in (escenario, "Ana Torres", cliente_a.correo, "R-20", "Ensayo"):
        assert secreto not in r.text


async def test_el_cliente_ve_propia_solo_en_sus_reservas_y_sin_detalle(
    cliente: AsyncClient,
    sala: str,
    escenario: str,
    cliente_a: UsuarioDePrueba,
    cliente_b: UsuarioDePrueba,
) -> None:
    a = (await disponibilidad(cliente, sala, con(cliente_a))).json()["ocupados"]
    b = (await disponibilidad(cliente, sala, con(cliente_b))).json()["ocupados"]
    assert [o["propia"] for o in a] == [True] and [o["propia"] for o in b] == [False]
    assert all("detalle" not in o for o in a + b)


async def test_personal_y_administrador_ven_el_detalle_de_cada_reserva(
    cliente: AsyncClient,
    sala: str,
    escenario: str,
    personal: UsuarioDePrueba,
    administrador: UsuarioDePrueba,
) -> None:
    for quien in (personal, administrador):
        [o] = (await disponibilidad(cliente, sala, con(quien))).json()["ocupados"]
        assert o["propia"] is False
        assert o["detalle"] == {
            "id_reserva": escenario,
            "cliente": "Ana Torres",
            "servicio": "Ensayo",
            "estado": "confirmada",
            "pago_por_validar": False,
        }


async def test_un_token_invalido_en_la_disponibilidad_es_401_no_visitante(
    cliente: AsyncClient, sala: str
) -> None:
    r = await disponibilidad(cliente, sala, {"Authorization": "Bearer basura"})
    assert r.status_code == 401 and r.json()["error"]["codigo"] == "no_autenticado"


async def test_una_pre_reservada_vencida_cuenta_como_libre_y_una_vigente_no(
    cliente: AsyncClient,
    sala: str,
    franja: Crear,
    reservar: Crear,
    cliente_a: UsuarioDePrueba,
    cliente_b: UsuarioDePrueba,
) -> None:
    franja("2027-03-01 08:00-05", "2027-03-01 12:00-05")
    reservar(
        cliente_a.id, "2027-03-01 09:00-05", "2027-03-01 10:00-05", "pre_reservada", "2020-01-01"
    )
    r = (await disponibilidad(cliente, sala)).json()
    assert r["ocupados"] == [] and r["dias"][0]["minutos_libres"] == 210
    reservar(
        cliente_b.id, "2027-03-01 10:30-05", "2027-03-01 11:00-05", "pre_reservada", "2099-01-01"
    )
    r = (await disponibilidad(cliente, sala)).json()
    assert len(r["ocupados"]) == 1


async def test_los_limites_siguen_los_parametros_de_anticipacion(
    cliente: AsyncClient, sala: str, sql: Ejecutar
) -> None:
    ahora = datetime.now(UTC)
    limites = (await disponibilidad(cliente, sala)).json()["limites"]
    desde, hasta = (datetime.fromisoformat(limites[k]) for k in ("desde", "hasta"))
    assert abs(desde - (ahora + timedelta(hours=2))) < timedelta(minutes=1)
    assert abs(hasta - (ahora + timedelta(weeks=100))) < timedelta(minutes=1)


async def test_una_franja_fuera_de_los_limites_no_da_minutos_libres(
    cliente: AsyncClient, sala: str, franja: Crear, sql: Ejecutar
) -> None:
    franja("2027-03-01 08:00-05", "2027-03-01 12:00-05")
    sql("update public.parametro set valor = 1 where clave = 'anticipacion_maxima_semanas'")
    r = (await disponibilidad(cliente, sala)).json()
    assert r["dias"] == [{"fecha": "2027-03-01", "minutos_libres": 0}]
    assert len(r["franjas"]) == 1  # la franja se sigue mostrando


async def test_un_cierre_se_informa_con_id_y_descuenta_minutos(
    cliente: AsyncClient, sala: str, franja: Crear, sql: Ejecutar
) -> None:
    franja("2027-03-01 08:00-05", "2027-03-01 12:00-05")
    sql(
        "insert into public.cierre_sala (id_sala, inicio, fin, motivo) "
        "values (%s, '2027-03-01 10:00-05', '2027-03-01 11:00-05', 'Mantenimiento')",
        sala,
    )
    r = (await disponibilidad(cliente, sala)).json()
    [cierre] = r["cierres"]
    assert set(cierre) == {"id", "inicio", "fin", "motivo"} and cierre["motivo"] == "Mantenimiento"
    assert r["dias"][0]["minutos_libres"] == 120


async def test_el_dia_se_cuenta_en_hora_de_lima(
    cliente: AsyncClient, sala: str, franja: Crear
) -> None:
    franja("2027-03-01 23:00-05", "2027-03-02 02:00-05")  # 04:00 a 07:00 UTC del dia 2
    r = await disponibilidad(
        cliente, sala, desde="2027-03-01T00:00:00-05:00", hasta="2027-03-03T00:00:00-05:00"
    )
    assert r.json()["dias"] == [
        {"fecha": "2027-03-01", "minutos_libres": 60},
        {"fecha": "2027-03-02", "minutos_libres": 90},
    ]


# --- disponibilidad: rangos y entradas invalidas -------------------------------------------------


async def test_rango_de_42_dias_es_valido_y_de_43_o_invertido_es_422(
    cliente: AsyncClient, sala: str
) -> None:
    ok = await disponibilidad(
        cliente, sala, desde="2027-03-01T00:00:00-05:00", hasta="2027-04-12T00:00:00-05:00"
    )
    assert ok.status_code == 200 and len(ok.json()["dias"]) == 42
    for desde, hasta in (
        ("2027-03-01T00:00:00-05:00", "2027-04-13T00:00:00-05:00"),
        ("2027-03-02T00:00:00-05:00", "2027-03-01T00:00:00-05:00"),
        ("2027-03-01T00:00:00-05:00", "2027-03-01T00:00:00-05:00"),
    ):
        r = await disponibilidad(cliente, sala, desde=desde, hasta=hasta)
        assert r.status_code == 422 and r.json()["error"]["codigo"] == "rango_invalido"


@pytest.mark.parametrize(
    "parametros",
    [
        {"desde": "2027-03-01T00:00:00", "hasta": "2027-03-02T00:00:00"},  # sin zona
        {"desde": "ayer"},
        {"desde": "0001-01-01T00:00:00+14:00", "hasta": "0001-01-02T00:00:00+14:00"},
        {"desde": "9999-12-30T00:00:00-05:00", "hasta": "9999-12-31T00:00:00-05:00"},
        {"hasta": None},
        {"sala": None},
        {"sala": "no-es-uuid"},
        {"desde": "2027-03-01T00:00:00-05:00\x00"},
    ],
)
async def test_entradas_invalidas_de_disponibilidad_son_422_nunca_500(
    cliente: AsyncClient, sala: str, parametros: dict[str, str | None]
) -> None:
    consulta = {k: v for k, v in {"sala": sala, **DIA, **parametros}.items() if v is not None}
    r = await cliente.get("/api/v1/disponibilidad", params=consulta)
    assert r.status_code == 422 and r.json()["error"]["codigo"] == "datos_invalidos"


async def test_una_sala_inexistente_es_404(cliente: AsyncClient) -> None:
    r = await disponibilidad(cliente, "00000000-0000-0000-0000-000000000000")
    assert r.status_code == 404 and r.json()["error"]["codigo"] == "no_encontrado"


# --- sugerencia de franjas -----------------------------------------------------------------------


async def test_la_sugerencia_desplaza_la_ultima_semana_publicada(
    cliente: AsyncClient, sala: str, franja: Crear, administrador: UsuarioDePrueba
) -> None:
    pedir = lambda semana: cliente.get(  # noqa: E731
        "/api/v1/franjas/sugerencia",
        params={"sala": sala, "semana": semana},
        headers=con(administrador),
    )
    assert (await pedir("2027-W10")).json() == []
    franja("2027-03-01 08:00-05", "2027-03-01 12:00-05")
    franja("2027-03-03 14:00-05", "2027-03-03 20:00-05")
    r = await pedir("2027-W10")
    assert r.status_code == 200
    assert [(x["inicio"], x["fin"]) for x in r.json()] == [
        ("2027-03-08T13:00:00Z", "2027-03-08T17:00:00Z"),
        ("2027-03-10T19:00:00Z", "2027-03-11T01:00:00Z"),
    ]
    assert (await pedir("2027-W09")).json() == []  # nada publicado antes de esa semana


@pytest.mark.parametrize(
    "semana", ["2027-W53", "2027-W00", "abc", "2027-W9", "", "9999-W52", "1999-W52", "2101-W01"]
)
async def test_la_sugerencia_con_semana_invalida_es_422(
    cliente: AsyncClient, sala: str, administrador: UsuarioDePrueba, semana: str
) -> None:
    r = await cliente.get(
        "/api/v1/franjas/sugerencia",
        params={"sala": sala, "semana": semana},
        headers=con(administrador),
    )
    assert r.status_code == 422
    assert r.json()["error"]["detalles"]["campo"] == "semana"


async def test_la_sugerencia_es_solo_del_administrador(
    cliente: AsyncClient, sala: str, cliente_a: UsuarioDePrueba, personal: UsuarioDePrueba
) -> None:
    url, params = "/api/v1/franjas/sugerencia", {"sala": sala, "semana": "2027-W10"}
    assert (await cliente.get(url, params=params)).status_code == 401
    for quien in (cliente_a, personal):
        r = await cliente.get(url, params=params, headers=con(quien))
        assert r.status_code == 403 and r.json()["error"]["codigo"] == "sin_permiso"


# --- publicar franjas ----------------------------------------------------------------------------


def cuerpo_franjas(sala: str, *tramos: dict[str, str]) -> dict[str, Any]:
    return {"id_sala": sala, "franjas": list(tramos)}


async def test_el_administrador_publica_un_lote_de_franjas(
    cliente: AsyncClient, sala: str, administrador: UsuarioDePrueba, sql: Ejecutar
) -> None:
    r = await cliente.post(
        "/api/v1/franjas",
        json=cuerpo_franjas(sala, tramo(1, 8, 12), tramo(2, 8, 12)),
        headers=con(administrador),
    )
    assert r.status_code == 201
    assert [set(f) for f in r.json()] == [{"id", "id_sala", "inicio", "fin"}] * 2
    assert sql("select count(*) from public.franja_sala where inicio >= '2027-01-01'") == [(2,)]
    [(publicador,)] = sql(
        "select distinct id_publicador from public.franja_sala where inicio >= '2027-01-01'"
    )
    assert publicador == administrador.id


async def test_franjas_solapadas_son_409_y_el_lote_no_deja_nada(
    cliente: AsyncClient, sala: str, administrador: UsuarioDePrueba, franja: Crear, sql: Ejecutar
) -> None:
    franja("2027-03-01 08:00-05", "2027-03-01 12:00-05")
    contiguo = tramo(1, 12, 14)
    solapado = tramo(1, 11, 13)
    r = await cliente.post(
        "/api/v1/franjas",
        json=cuerpo_franjas(sala, tramo(2, 8, 10), solapado),
        headers=con(administrador),
    )
    assert r.status_code == 409 and r.json()["error"]["codigo"] == "franja_solapada"
    assert sql("select count(*) from public.franja_sala where inicio >= '2027-01-01'") == [(1,)]
    # contigua si; solapadas entre si dentro del mismo lote no
    assert (
        await cliente.post(
            "/api/v1/franjas", json=cuerpo_franjas(sala, contiguo), headers=con(administrador)
        )
    ).status_code == 201
    r = await cliente.post(
        "/api/v1/franjas",
        json=cuerpo_franjas(sala, tramo(3, 8, 10), tramo(3, 9, 11)),
        headers=con(administrador),
    )
    assert r.status_code == 409 and r.json()["error"]["codigo"] == "franja_solapada"
    assert sql("select count(*) from public.franja_sala where inicio >= '2027-01-01'") == [(2,)]


@pytest.mark.parametrize(
    "franjas",
    [
        [{"inicio": "2027-03-01T08:15:00-05:00", "fin": "2027-03-01T12:00:00-05:00"}],
        [{"inicio": "2027-03-01T08:00:00-05:00", "fin": "2027-03-01T12:20:00-05:00"}],
        [{"inicio": "2027-03-01T08:00:30-05:00", "fin": "2027-03-01T12:00:00-05:00"}],
        [{"inicio": "2027-03-01T12:00:00-05:00", "fin": "2027-03-01T08:00:00-05:00"}],
        [{"inicio": "2027-03-01T08:00:00-05:00", "fin": "2027-03-01T08:00:00-05:00"}],
        [{"inicio": "2027-03-01T08:00:00", "fin": "2027-03-01T12:00:00"}],
        [{"inicio": "2027-03-01T08:00:00-05:00"}],
        [{"inicio": "2027-03-01T08:00:00-05:00", "fin": "2027-03-01T12:00:00-05:00", "x": 1}],
        [],
    ],
)
async def test_franjas_invalidas_son_422_con_su_campo_y_no_escriben(
    cliente: AsyncClient,
    sala: str,
    administrador: UsuarioDePrueba,
    sql: Ejecutar,
    franjas: list[dict[str, Any]],
) -> None:
    r = await cliente.post(
        "/api/v1/franjas", json={"id_sala": sala, "franjas": franjas}, headers=con(administrador)
    )
    assert r.status_code == 422 and r.json()["error"]["codigo"] == "datos_invalidos"
    assert r.json()["error"]["detalles"]["campo"].startswith("franjas")
    assert sql("select count(*) from public.franja_sala where inicio >= '2027-01-01'") == [(0,)]


async def test_publicar_franjas_con_sala_inexistente_es_404(
    cliente: AsyncClient, administrador: UsuarioDePrueba
) -> None:
    r = await cliente.post(
        "/api/v1/franjas",
        json=cuerpo_franjas("00000000-0000-0000-0000-000000000000", tramo(1, 8, 12)),
        headers=con(administrador),
    )
    assert r.status_code == 404


async def test_publicar_franjas_sin_ser_administrador_es_401_o_403_y_no_escribe(
    cliente: AsyncClient,
    sala: str,
    cliente_a: UsuarioDePrueba,
    personal: UsuarioDePrueba,
    sql: Ejecutar,
) -> None:
    cuerpo = cuerpo_franjas(sala, tramo(1, 8, 12))
    assert (await cliente.post("/api/v1/franjas", json=cuerpo)).status_code == 401
    for quien in (cliente_a, personal):
        r = await cliente.post("/api/v1/franjas", json=cuerpo, headers=con(quien))
        assert r.status_code == 403 and r.json()["error"]["codigo"] == "sin_permiso"
    assert sql("select count(*) from public.franja_sala where inicio >= '2027-01-01'") == [(0,)]


# --- retirar franja ------------------------------------------------------------------------------


async def test_se_retira_una_franja_sin_reservas(
    cliente: AsyncClient, administrador: UsuarioDePrueba, franja: Crear, sql: Ejecutar
) -> None:
    id_franja = franja("2027-03-01 08:00-05", "2027-03-01 12:00-05")
    r = await cliente.delete(f"/api/v1/franjas/{id_franja}", headers=con(administrador))
    assert r.status_code == 204 and r.content == b""
    assert sql("select count(*) from public.franja_sala where id = %s", id_franja) == [(0,)]
    r = await cliente.delete(f"/api/v1/franjas/{id_franja}", headers=con(administrador))
    assert r.status_code == 404


async def test_no_se_retira_una_franja_con_reservas_vigentes_pero_si_con_canceladas_o_vencidas(
    cliente: AsyncClient,
    administrador: UsuarioDePrueba,
    cliente_a: UsuarioDePrueba,
    franja: Crear,
    reservar: Crear,
    sql: Ejecutar,
) -> None:
    id_franja = franja("2027-03-01 08:00-05", "2027-03-01 12:00-05")
    vigente = reservar(cliente_a.id, "2027-03-01 09:00-05", "2027-03-01 10:00-05")
    r = await cliente.delete(f"/api/v1/franjas/{id_franja}", headers=con(administrador))
    assert r.status_code == 409 and r.json()["error"]["codigo"] == "franja_con_reservas"
    assert sql("select count(*) from public.franja_sala where id = %s", id_franja) == [(1,)]
    sql(
        "update public.reserva set estado = 'cancelada', motivo_cancelacion = 'cliente' "
        "where id = %s",
        vigente,
    )
    reservar(
        cliente_a.id, "2027-03-01 10:30-05", "2027-03-01 11:00-05", "pre_reservada", "2020-01-01"
    )
    r = await cliente.delete(f"/api/v1/franjas/{id_franja}", headers=con(administrador))
    assert r.status_code == 204


async def test_se_retira_una_franja_con_reservas_enlazadas_canceladas_o_vencidas(
    cliente: AsyncClient,
    administrador: UsuarioDePrueba,
    cliente_a: UsuarioDePrueba,
    franja: Crear,
    reservar: Crear,
    sql: Ejecutar,
) -> None:
    id_franja = franja("2027-03-01 08:00-05", "2027-03-01 12:00-05")
    vigente = reservar(
        cliente_a.id, "2027-03-01 09:00-05", "2027-03-01 10:00-05", id_franja=id_franja
    )
    url = f"/api/v1/franjas/{id_franja}"
    r = await cliente.delete(url, headers=con(administrador))
    assert r.status_code == 409 and r.json()["error"]["codigo"] == "franja_con_reservas"
    sql(
        "update public.reserva set estado = 'cancelada', motivo_cancelacion = 'cliente' "
        "where id = %s",
        vigente,
    )
    vencida = reservar(
        cliente_a.id,
        "2027-03-01 10:30-05",
        "2027-03-01 11:00-05",
        "pre_reservada",
        "2020-01-01",
        id_franja,
    )
    r = await cliente.delete(url, headers=con(administrador))
    assert r.status_code == 204
    assert sql("select id_franja from public.reserva where id = %s", vencida) == [(None,)]
    assert sql("select count(*) from public.reserva where id = %s", vigente) == [(1,)]


async def test_retirar_franja_sin_ser_administrador_deja_la_fila_intacta(
    cliente: AsyncClient,
    cliente_a: UsuarioDePrueba,
    personal: UsuarioDePrueba,
    franja: Crear,
    sql: Ejecutar,
) -> None:
    id_franja = franja("2027-03-01 08:00-05", "2027-03-01 12:00-05")
    antes = sql("select * from public.franja_sala where id = %s", id_franja)
    url = f"/api/v1/franjas/{id_franja}"
    assert (await cliente.delete(url)).status_code == 401
    for quien in (cliente_a, personal):
        assert (await cliente.delete(url, headers=con(quien))).status_code == 403
    assert sql("select * from public.franja_sala where id = %s", id_franja) == antes
    assert (
        await cliente.delete("/api/v1/franjas/no-uuid", headers=con(cliente_a))
    ).status_code == 422


# --- cierres -------------------------------------------------------------------------------------


async def test_el_administrador_cierra_y_reabre(
    cliente: AsyncClient, sala: str, administrador: UsuarioDePrueba, sql: Ejecutar
) -> None:
    r = await cliente.post(
        "/api/v1/cierres",
        json={"id_sala": sala, **tramo(1, 8, 20), "motivo": "  Feriado  "},
        headers=con(administrador),
    )
    assert r.status_code == 201
    cierre = r.json()
    assert set(cierre) == {"id", "id_sala", "inicio", "fin", "motivo"}
    assert cierre["motivo"] == "Feriado"
    assert sql("select id_autor from public.cierre_sala where id = %s", cierre["id"]) == [
        (administrador.id,)
    ]
    r = await cliente.delete(f"/api/v1/cierres/{cierre['id']}", headers=con(administrador))
    assert r.status_code == 204
    r = await cliente.delete(f"/api/v1/cierres/{cierre['id']}", headers=con(administrador))
    assert r.status_code == 404


async def test_un_cierre_sobre_reservas_vigentes_es_409_y_las_lista(
    cliente: AsyncClient,
    sala: str,
    administrador: UsuarioDePrueba,
    cliente_a: UsuarioDePrueba,
    cliente_b: UsuarioDePrueba,
    reservar: Crear,
    sql: Ejecutar,
) -> None:
    id_a = reservar(cliente_a.id, "2027-03-01 09:00-05", "2027-03-01 10:00-05")
    reservar(cliente_b.id, "2027-03-02 09:00-05", "2027-03-02 10:00-05")  # otro dia: no cuenta
    r = await cliente.post(
        "/api/v1/cierres",
        json={"id_sala": sala, **tramo(1, 8, 20), "motivo": "Mantenimiento"},
        headers=con(administrador),
    )
    assert r.status_code == 409
    error = r.json()["error"]
    assert error["codigo"] == "cierre_con_reservas"
    [reserva] = error["detalles"]["reservas"]
    assert set(reserva) == {"id", "folio", "inicio", "cliente"}
    assert reserva["id"] == id_a and reserva["cliente"] == "Ana Torres"
    assert reserva["folio"].startswith("R-") and reserva["inicio"].endswith("-05:00")
    assert sql("select count(*) from public.cierre_sala where inicio >= '2027-01-01'") == [(0,)]


async def test_un_cierre_no_se_rechaza_por_una_reserva_cancelada(
    cliente: AsyncClient,
    sala: str,
    administrador: UsuarioDePrueba,
    cliente_a: UsuarioDePrueba,
    reservar: Crear,
) -> None:
    reservar(cliente_a.id, "2027-03-01 09:00-05", "2027-03-01 10:00-05", "cancelada")
    r = await cliente.post(
        "/api/v1/cierres",
        json={"id_sala": sala, **tramo(1, 8, 20), "motivo": "Feriado"},
        headers=con(administrador),
    )
    assert r.status_code == 201


@pytest.mark.parametrize(
    "cambios",
    [
        {"motivo": "Mal\x00motivo"},
        {"motivo": "Mal\x07motivo"},
        {"motivo": "Linea\nnueva"},
        {"motivo": "   "},
        {"motivo": ""},
        {"motivo": "x" * 201},
        {"inicio": "2027-03-01T20:00:00-05:00", "fin": "2027-03-01T08:00:00-05:00"},
        {"inicio": "2027-03-01T08:00:00", "fin": "2027-03-01T20:00:00"},
        {"extra": 1},
    ],
)
async def test_cierres_invalidos_son_422_y_no_escriben(
    cliente: AsyncClient,
    sala: str,
    administrador: UsuarioDePrueba,
    sql: Ejecutar,
    cambios: dict[str, Any],
) -> None:
    cuerpo = {"id_sala": sala, **tramo(1, 8, 20), "motivo": "Feriado", **cambios}
    r = await cliente.post("/api/v1/cierres", json=cuerpo, headers=con(administrador))
    assert r.status_code == 422 and r.json()["error"]["codigo"] == "datos_invalidos"
    assert "campo" in r.json()["error"]["detalles"]
    assert sql("select count(*) from public.cierre_sala where inicio >= '2027-01-01'") == [(0,)]


async def test_cierres_sin_ser_administrador_no_cambian_nada(
    cliente: AsyncClient,
    sala: str,
    cliente_a: UsuarioDePrueba,
    personal: UsuarioDePrueba,
    sql: Ejecutar,
) -> None:
    cuerpo = {"id_sala": sala, **tramo(1, 8, 20), "motivo": "Feriado"}
    assert (await cliente.post("/api/v1/cierres", json=cuerpo)).status_code == 401
    for quien in (cliente_a, personal):
        assert (
            await cliente.post("/api/v1/cierres", json=cuerpo, headers=con(quien))
        ).status_code == 403
    id_cierre = str(
        sql(
            "insert into public.cierre_sala (id_sala, inicio, fin, motivo) "
            "values (%s, '2027-03-05 08:00-05', '2027-03-05 20:00-05', 'Feriado') returning id",
            sala,
        )[0][0]
    )
    antes = sql("select * from public.cierre_sala where id = %s", id_cierre)
    assert (await cliente.delete(f"/api/v1/cierres/{id_cierre}")).status_code == 401
    for quien in (cliente_a, personal):
        r = await cliente.delete(f"/api/v1/cierres/{id_cierre}", headers=con(quien))
        assert r.status_code == 403
    assert sql("select * from public.cierre_sala where id = %s", id_cierre) == antes
    assert sql("select count(*) from public.cierre_sala where inicio >= '2027-01-01'") == [(1,)]


# --- parametros ----------------------------------------------------------------------------------

PARAMETROS = {
    "dias_limite_pago",
    "horas_limite_pago",
    "anticipacion_minima_horas",
    "anticipacion_maxima_semanas",
    "porcentaje_adelanto",
    "horas_nivel_1",
    "horas_nivel_2",
    "porcentaje_penalizacion_nivel_2",
    "minutos_tolerancia_inasistencia",
    "dias_vigencia_credito",
    "reprogramaciones_nivel_1",
    "reprogramaciones_nivel_2",
}


async def test_el_administrador_lee_y_ajusta_los_parametros(
    cliente: AsyncClient, administrador: UsuarioDePrueba
) -> None:
    r = await cliente.get("/api/v1/parametros", headers=con(administrador))
    assert r.status_code == 200 and set(r.json()) == PARAMETROS
    assert r.json()["anticipacion_minima_horas"] == 2 and r.json()["dias_limite_pago"] == 3
    r = await cliente.patch(
        "/api/v1/parametros",
        json={"horas_limite_pago": 2, "anticipacion_minima_horas": 4},
        headers=con(administrador),
    )  # RF-20: horas_limite_pago es sensible y no aplica nada, ni lo no sensible que trae
    assert r.status_code == 428
    assert r.json()["error"]["detalles"] == {"campos": ["horas_limite_pago"]}
    actuales = await cliente.get("/api/v1/parametros", headers=con(administrador))
    assert actuales.json()["anticipacion_minima_horas"] == 2
    r = await cliente.patch(
        "/api/v1/parametros",
        json={"horas_limite_pago": 1, "anticipacion_minima_horas": 4},
        headers=con(administrador),
    )
    assert r.status_code == 200
    assert r.json()["horas_limite_pago"] == 1 and r.json()["anticipacion_minima_horas"] == 4
    assert r.json()["dias_limite_pago"] == 3  # lo no enviado no cambia
    otra = await cliente.get("/api/v1/parametros", headers=con(administrador))
    assert otra.json() == r.json()


@pytest.mark.parametrize(
    "cuerpo",
    [
        {"dias_limite_pago": 0},
        {"dias_limite_pago": -1},
        {"horas_limite_pago": "3"},
        {"horas_limite_pago": True},
        {"horas_limite_pago": 1.5},
        {"horas_limite_pago": None},
        {"anticipacion_maxima_semanas": 10**12},
        {"otro": 1},
    ],
)
async def test_parametros_invalidos_son_422_con_su_campo_y_no_cambian(
    cliente: AsyncClient, administrador: UsuarioDePrueba, cuerpo: dict[str, Any]
) -> None:
    antes = (await cliente.get("/api/v1/parametros", headers=con(administrador))).json()
    r = await cliente.patch("/api/v1/parametros", json=cuerpo, headers=con(administrador))
    assert r.status_code == 422 and r.json()["error"]["codigo"] == "datos_invalidos"
    assert r.json()["error"]["detalles"]["campo"] in cuerpo | {"cuerpo": 0}
    assert (await cliente.get("/api/v1/parametros", headers=con(administrador))).json() == antes


async def test_parametros_solo_del_administrador_y_sin_cambios_si_no_lo_es(
    cliente: AsyncClient,
    cliente_a: UsuarioDePrueba,
    personal: UsuarioDePrueba,
    sql: Ejecutar,
) -> None:
    antes = sql("select clave, valor from public.parametro order by 1")
    assert (await cliente.get("/api/v1/parametros")).status_code == 401
    assert (
        await cliente.patch("/api/v1/parametros", json={"dias_limite_pago": 9})
    ).status_code == 401
    for quien in (cliente_a, personal):
        assert (await cliente.get("/api/v1/parametros", headers=con(quien))).status_code == 403
        r = await cliente.patch(
            "/api/v1/parametros", json={"dias_limite_pago": 9}, headers=con(quien)
        )
        assert r.status_code == 403 and r.json()["error"]["codigo"] == "sin_permiso"
    assert sql("select clave, valor from public.parametro order by 1") == antes


# --- OpenAPI -------------------------------------------------------------------------------------

CONTRATO = {
    ("get", "/api/v1/salas"): {503},
    ("get", "/api/v1/disponibilidad"): {401, 404, 422, 503},
    ("get", "/api/v1/franjas/sugerencia"): {401, 403, 404, 422, 503},
    ("post", "/api/v1/franjas"): {401, 403, 404, 409, 422, 503},
    ("delete", "/api/v1/franjas/{id_franja}"): {401, 403, 404, 409, 422, 503},
    ("post", "/api/v1/cierres"): {401, 403, 404, 409, 422, 503},
    ("delete", "/api/v1/cierres/{id_cierre}"): {401, 403, 404, 422, 503},
    ("get", "/api/v1/parametros"): {401, 403, 503},
    ("patch", "/api/v1/parametros"): {401, 403, 422, 503},
    ("patch", "/api/v1/salas/{id_sala}"): {401, 403, 404, 422, 503},
}


def test_openapi_declara_los_codigos_del_contrato_con_respuesta_error(app: FastAPI) -> None:
    rutas = app.openapi()["paths"]
    for (metodo, ruta), codigos in CONTRATO.items():
        respuestas = rutas[ruta][metodo]["responses"]
        for codigo in codigos:
            esquema = respuestas[str(codigo)]["content"]["application/json"]["schema"]
            assert esquema == {"$ref": "#/components/schemas/RespuestaError"}, (
                metodo,
                ruta,
                codigo,
            )
    assert rutas["/api/v1/franjas"]["post"]["responses"]["201"]
    assert rutas["/api/v1/cierres"]["post"]["responses"]["201"]
    assert rutas["/api/v1/franjas/{id_franja}"]["delete"]["responses"]["204"]
    assert rutas["/api/v1/cierres/{id_cierre}"]["delete"]["responses"]["204"]
