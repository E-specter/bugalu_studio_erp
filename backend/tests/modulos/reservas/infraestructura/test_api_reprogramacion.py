"""RF-18 parte B: reprogramar con niveles (CA-08 a CA-10) y eleccion tras el estudio."""

import asyncio
import base64
import json
from collections.abc import Callable
from decimal import Decimal
from typing import Any
from uuid import UUID

import psycopg
import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from bugalu.compartido.configuracion import Configuracion, obtener_configuracion
from bugalu.main import crear_app
from tests.conftest import UsuarioDePrueba
from tests.modulos.reservas.infraestructura.conftest import Ejecutar, con

pytestmark = pytest.mark.integracion

RESERVAS = "/api/v1/reservas"
PRECIO = '{"lineas": [], "recargos": [], "total": "200", "anticipo": "100"}'
# Los plazos guardados mandan: con estos, una reserva de 2027 cae en el nivel que se pide.
PLAZOS = {1: (48, 24), 2: (10_000_000, 100), 3: (20_000_000, 10_000_000)}
NUEVO = "2027-07-05T10:00:00-05:00"  # lunes, dentro de la franja `nuevo_dia`
CUERPOS: dict[str, dict[str, Any]] = {
    "reprogramar/simular": {"inicio": NUEVO},
    "reprogramar": {"inicio": NUEVO, "nivel_esperado": 1, "total_esperado": "1.00"},
    "eleccion-estudio": {"opcion": "devolucion"},
}
CLAVES_VISTA = {"nivel", "penalizacion", "precio", "saldo", "credito", "reprogramaciones_restantes"}


@pytest.fixture
def reserva_con_pagos(sql: Ejecutar, reservar: Callable[..., str]) -> Callable[..., str]:
    """Reserva (junio de 2027, 10:00 a 12:00) de total 200 con el adelanto pagado (100)."""
    dias = iter(range(1, 28))

    def crear(usuario: UsuarioDePrueba, nivel: int = 1, estado: str = "confirmada") -> str:
        dia = next(dias)
        id_ = reservar(
            usuario.id,
            f"2027-06-{dia:02d}T10:00:00-05:00",
            f"2027-06-{dia:02d}T12:00:00-05:00",
            estado,
        )
        h1, h2 = PLAZOS[nivel]
        sql(
            "update public.reserva set precio = %s::jsonb, total = 200, "
            "creada_en = now() - interval '30 days', "
            "parametros_aplicados = parametros_aplicados || "
            "jsonb_build_object('horas_nivel_1', %s::int, 'horas_nivel_2', %s::int) where id = %s",
            PRECIO,
            h1,
            h2,
            UUID(id_),
        )
        sql(
            "insert into public.cuota (id_reserva, hito, monto, estado, pagado) "
            "values (%s, 'al_reservar', 100, 'pagada', 100), "
            "(%s, 'al_terminar', 100, 'pendiente', 0)",
            UUID(id_),
            UUID(id_),
        )
        return id_

    return crear


@pytest.fixture
def nuevo_dia(franja: Callable[[str, str], str]) -> str:
    return franja("2027-07-05 08:00-05", "2027-07-05 20:00-05")


def codigo(r: Any) -> str:
    return str(r.json()["error"]["codigo"])


def estado_de(sql: Ejecutar, id_: str) -> tuple[Any, ...]:
    return sql(
        "select inicio, estado, total, eleccion_estudio from public.reserva where id = %s",
        UUID(id_),
    )[0]


async def simular(
    cliente: AsyncClient, usuario: UsuarioDePrueba, id_: str, inicio: str = NUEVO
) -> Any:
    return await cliente.post(
        f"{RESERVAS}/{id_}/reprogramar/simular", json={"inicio": inicio}, headers=con(usuario)
    )


async def reprogramar(
    cliente: AsyncClient, usuario: UsuarioDePrueba, id_: str, **cuerpo: Any
) -> Any:
    cuerpo = {"inicio": NUEVO, **cuerpo}
    return await cliente.post(f"{RESERVAS}/{id_}/reprogramar", json=cuerpo, headers=con(usuario))


async def vista_y_total(
    cliente: AsyncClient, usuario: UsuarioDePrueba, id_: str, inicio: str = NUEVO
) -> tuple[dict[str, Any], Decimal]:
    r = await simular(cliente, usuario, id_, inicio)
    assert r.status_code == 200, r.text
    return r.json(), Decimal(r.json()["precio"]["total"])


# --- simular --------------------------------------------------------------------------------


async def test_simular_nivel_1_devuelve_la_vista_sin_cambiar_nada(
    cliente: AsyncClient,
    cliente_a: UsuarioDePrueba,
    reserva_con_pagos: Callable[..., str],
    nuevo_dia: str,
    sql: Ejecutar,
) -> None:
    id_ = reserva_con_pagos(cliente_a, 1)
    antes = estado_de(sql, id_)
    vista, total = await vista_y_total(cliente, cliente_a, id_)
    assert set(vista) == CLAVES_VISTA
    assert (vista["nivel"], vista["penalizacion"]) == (1, "0.00")
    assert vista["saldo"] == str(max(total - 100, Decimal(0)).quantize(Decimal("0.01")))
    assert vista["credito"] == str(max(100 - total, Decimal(0)).quantize(Decimal("0.01")))
    assert vista["reprogramaciones_restantes"] == 1
    assert vista["precio"]["impuesto"]["nombre"] == "IGV"  # el desglose de RF-20
    assert estado_de(sql, id_) == antes
    assert sql("select count(*) from public.reprogramacion") == [(0,)]
    assert sql("select count(*) from public.credito") == [(0,)]


async def test_simular_nivel_2_suma_la_penalizacion_al_saldo(
    cliente: AsyncClient,
    cliente_a: UsuarioDePrueba,
    reserva_con_pagos: Callable[..., str],
    nuevo_dia: str,
) -> None:
    id_ = reserva_con_pagos(cliente_a, 2)
    vista, total = await vista_y_total(cliente, cliente_a, id_)
    assert (vista["nivel"], vista["penalizacion"]) == (2, "50.00")  # 25 % de 200
    assert Decimal(vista["saldo"]) == max(total + 50 - 100, Decimal(0))
    assert vista["reprogramaciones_restantes"] == 0


async def test_simular_con_pagado_mayor_al_precio_nuevo_deja_credito(
    cliente: AsyncClient,
    cliente_a: UsuarioDePrueba,
    reserva_con_pagos: Callable[..., str],
    nuevo_dia: str,
    sql: Ejecutar,
) -> None:
    id_ = reserva_con_pagos(cliente_a, 1)
    sql("update public.cuota set monto = 5000, pagado = 5000 where hito = 'al_reservar'")
    vista, total = await vista_y_total(cliente, cliente_a, id_)
    assert (vista["saldo"], Decimal(vista["credito"])) == ("0.00", 5000 - total)


# --- reprogramar: exito --------------------------------------------------------------------------


async def test_reprogramar_nivel_1_recalcula_el_precio_y_conserva_la_reserva(
    cliente: AsyncClient,
    cliente_a: UsuarioDePrueba,
    reserva_con_pagos: Callable[..., str],
    nuevo_dia: str,
    sql: Ejecutar,
) -> None:
    id_ = reserva_con_pagos(cliente_a, 1)
    folio = sql("select folio from public.reserva where id = %s", UUID(id_))[0][0]
    vista, total = await vista_y_total(cliente, cliente_a, id_)
    r = await reprogramar(cliente, cliente_a, id_, nivel_esperado=1, total_esperado=str(total))
    assert r.status_code == 200, r.text
    reserva = r.json()
    assert (reserva["id"], reserva["folio"], reserva["estado"]) == (id_, folio, "confirmada")
    assert reserva["inicio"] == NUEVO
    assert reserva["fin"] == "2027-07-05T12:00:00-05:00"
    assert reserva["fin_buffer"] == "2027-07-05T12:30:00-05:00"
    assert reserva["precio"] == vista["precio"] and reserva["pagado"] == "100.00"
    assert "cancelacion" not in reserva and "eleccion_estudio" not in reserva
    historial = reserva["reprogramaciones"]
    assert len(historial) == 1
    assert (historial[0]["nivel"], historial[0]["penalizacion"]) == (1, "0.00")
    assert historial[0]["total_anterior"] == "200.00"
    assert Decimal(historial[0]["total_nuevo"]) == total
    assert historial[0]["anterior_inicio"].startswith("2027-06-01T10:00:00")
    saldo = {c["hito"]: c for c in reserva["cuotas"]}["al_terminar"]
    assert Decimal(saldo["monto"]) == Decimal(vista["saldo"])
    avisos = sql(
        "select datos ->> 'folio' from public.notificacion "
        "where tipo = 'reserva_reprogramada' and destinatario = %s",
        cliente_a.correo,
    )
    assert avisos == [(folio,)]


async def test_reprogramar_a_un_precio_menor_pasa_la_diferencia_a_credito(
    cliente: AsyncClient,
    cliente_a: UsuarioDePrueba,
    reserva_con_pagos: Callable[..., str],
    nuevo_dia: str,
    sql: Ejecutar,
) -> None:
    id_ = reserva_con_pagos(cliente_a, 1)
    sql("update public.cuota set monto = 5000, pagado = 5000 where hito = 'al_reservar'")
    _, total = await vista_y_total(cliente, cliente_a, id_)
    r = await reprogramar(cliente, cliente_a, id_, nivel_esperado=1, total_esperado=str(total))
    assert r.status_code == 200, r.text
    saldo = {c["hito"]: c for c in r.json()["cuotas"]}["al_terminar"]
    assert (saldo["monto"], saldo["estado"]) == ("0.00", "pagada")
    assert sql("select tipo, monto, saldo, estado from public.credito") == [
        ("reprogramacion", 5000 - total, 5000 - total, "vigente")
    ]


async def test_reprogramar_nivel_2_cobra_la_penalizacion_en_el_saldo(
    cliente: AsyncClient,
    cliente_a: UsuarioDePrueba,
    reserva_con_pagos: Callable[..., str],
    nuevo_dia: str,
) -> None:
    id_ = reserva_con_pagos(cliente_a, 2)
    vista, total = await vista_y_total(cliente, cliente_a, id_)
    r = await reprogramar(cliente, cliente_a, id_, nivel_esperado=2, total_esperado=str(total))
    assert r.status_code == 200, r.text
    reserva = r.json()
    assert reserva["reprogramaciones"][0]["penalizacion"] == "50.00"
    saldo = {c["hito"]: c for c in reserva["cuotas"]}["al_terminar"]
    assert saldo["monto"] == vista["saldo"] and Decimal(saldo["monto"]) == total - 50


async def test_moverse_30_minutos_se_solapa_con_el_propio_horario(
    cliente: AsyncClient,
    cliente_a: UsuarioDePrueba,
    reserva_con_pagos: Callable[..., str],
    franja: Callable[[str, str], str],
) -> None:
    franja("2027-06-01 08:00-05", "2027-06-01 20:00-05")
    id_ = reserva_con_pagos(cliente_a, 1)
    nuevo = "2027-06-01T10:30:00-05:00"
    _, total = await vista_y_total(cliente, cliente_a, id_, nuevo)
    r = await reprogramar(
        cliente, cliente_a, id_, inicio=nuevo, nivel_esperado=1, total_esperado=str(total)
    )
    assert r.status_code == 200, r.text
    assert (r.json()["inicio"], r.json()["fin_buffer"]) == (
        nuevo,
        "2027-06-01T13:00:00-05:00",
    )


# --- reprogramar: barreras -----------------------------------------------------------------------


async def test_exige_nivel_y_total_esperados_y_devuelve_la_vista_nueva(
    cliente: AsyncClient,
    cliente_a: UsuarioDePrueba,
    reserva_con_pagos: Callable[..., str],
    nuevo_dia: str,
    sql: Ejecutar,
) -> None:
    id_ = reserva_con_pagos(cliente_a, 1)
    antes = estado_de(sql, id_)
    vista, total = await vista_y_total(cliente, cliente_a, id_)
    r = await reprogramar(cliente, cliente_a, id_, nivel_esperado=2, total_esperado=str(total))
    assert (r.status_code, codigo(r)) == (409, "nivel_cambiado")
    detalles = r.json()["error"]["detalles"]
    assert set(detalles) == CLAVES_VISTA and detalles["nivel"] == 1
    assert detalles["precio"] == vista["precio"] and detalles["saldo"] == vista["saldo"]
    r = await reprogramar(cliente, cliente_a, id_, nivel_esperado=1, total_esperado=str(total + 1))
    assert (r.status_code, codigo(r)) == (409, "precio_cambiado")
    assert r.json()["error"]["detalles"]["precio"] == vista["precio"]
    r = await reprogramar(cliente, cliente_a, id_)  # sin ninguno de los dos
    assert (r.status_code, codigo(r)) == (409, "nivel_cambiado")
    assert estado_de(sql, id_) == antes
    assert sql("select count(*) from public.reprogramacion") == [(0,)]


async def test_nivel_3_no_se_reprograma(
    cliente: AsyncClient,
    cliente_a: UsuarioDePrueba,
    reserva_con_pagos: Callable[..., str],
    nuevo_dia: str,
) -> None:
    id_ = reserva_con_pagos(cliente_a, 3)
    for r in (
        await simular(cliente, cliente_a, id_),
        await reprogramar(cliente, cliente_a, id_, nivel_esperado=3, total_esperado="0.00"),
    ):
        assert (r.status_code, codigo(r)) == (409, "reprogramacion_no_permitida")


async def test_solo_una_confirmada_se_reprograma(
    cliente: AsyncClient,
    cliente_a: UsuarioDePrueba,
    reserva_con_pagos: Callable[..., str],
    nuevo_dia: str,
) -> None:
    id_ = reserva_con_pagos(cliente_a, 1, "pre_reservada")
    r = await simular(cliente, cliente_a, id_)
    assert (r.status_code, codigo(r)) == (409, "reprogramacion_no_permitida")


@pytest.mark.parametrize(
    ("nivel", "previas"), [(1, (1, 1)), (2, (2,)), (2, (1, 1))], ids=["total", "nivel_2", "total_2"]
)
async def test_los_limites_de_reprogramaciones(
    cliente: AsyncClient,
    cliente_a: UsuarioDePrueba,
    reserva_con_pagos: Callable[..., str],
    nuevo_dia: str,
    sql: Ejecutar,
    nivel: int,
    previas: tuple[int, ...],
) -> None:
    id_ = reserva_con_pagos(cliente_a, nivel)
    for n in previas:
        sql(
            "insert into public.reprogramacion (id_reserva, anterior_inicio, nuevo_inicio, nivel, "
            "total_anterior, total_nuevo) values (%s, now(), now(), %s, 200, 200)",
            UUID(id_),
            n,
        )
    r = await simular(cliente, cliente_a, id_)
    assert (r.status_code, codigo(r)) == (409, "limite_reprogramaciones")


async def test_el_tramo_ocupado_por_otra_reserva_es_409(
    cliente: AsyncClient,
    cliente_a: UsuarioDePrueba,
    cliente_b: UsuarioDePrueba,
    reserva_con_pagos: Callable[..., str],
    reservar: Callable[..., str],
    nuevo_dia: str,
    sql: Ejecutar,
) -> None:
    id_ = reserva_con_pagos(cliente_a, 1)
    reservar(cliente_b.id, "2027-07-05T11:00:00-05:00", "2027-07-05T13:00:00-05:00")
    antes = estado_de(sql, id_)
    for r in (
        await simular(cliente, cliente_a, id_),
        await reprogramar(cliente, cliente_a, id_, nivel_esperado=1, total_esperado="1.00"),
    ):
        assert (r.status_code, codigo(r)) == (409, "tramo_no_disponible")
    assert estado_de(sql, id_) == antes


async def test_el_horario_nuevo_cumple_las_reglas_de_una_reserva_nueva(
    cliente: AsyncClient,
    cliente_a: UsuarioDePrueba,
    reserva_con_pagos: Callable[..., str],
    nuevo_dia: str,
    sql: Ejecutar,
) -> None:
    id_ = reserva_con_pagos(cliente_a, 1)
    casos = [
        ("2027-07-06T10:00:00-05:00", "fuera_de_franja"),  # sin franja
        ("2027-07-05T07:00:00-05:00", "fuera_de_franja"),  # antes de la franja
        ("2027-07-05T10:15:00-05:00", "duracion_invalida"),  # no es media hora exacta
        ("2031-07-05T10:00:00-05:00", "anticipacion_excesiva"),
        ("2020-07-05T10:00:00-05:00", "anticipacion_insuficiente"),
    ]
    for inicio, esperado in casos:
        for r in (
            await simular(cliente, cliente_a, id_, inicio),
            await reprogramar(cliente, cliente_a, id_, inicio=inicio, nivel_esperado=1),
        ):
            assert (r.status_code, codigo(r)) == (422, esperado), (inicio, r.text)
    r = await simular(cliente, cliente_a, id_, "2027-07-05T10:00:00")  # sin zona
    assert (r.status_code, codigo(r)) == (422, "datos_invalidos")
    assert sql("select count(*) from public.reprogramacion") == [(0,)]


async def test_el_cuerpo_no_trae_nada_mas(
    cliente: AsyncClient,
    cliente_a: UsuarioDePrueba,
    reserva_con_pagos: Callable[..., str],
    nuevo_dia: str,
) -> None:
    id_ = reserva_con_pagos(cliente_a, 1)
    for extra in ({"total": "1.00"}, {"penalizacion": "0.00"}, {"id_sala": str(UUID(int=1))}):
        r = await reprogramar(cliente, cliente_a, id_, nivel_esperado=1, **extra)
        assert (r.status_code, codigo(r)) == (422, "datos_invalidos"), extra


async def test_dos_reprogramaciones_al_mismo_tramo_una_gana_y_la_otra_es_409(
    cliente: AsyncClient,
    cliente_a: UsuarioDePrueba,
    cliente_b: UsuarioDePrueba,
    reserva_con_pagos: Callable[..., str],
    nuevo_dia: str,
    sql: Ejecutar,
) -> None:
    a, b = reserva_con_pagos(cliente_a, 1), reserva_con_pagos(cliente_b, 1)
    _, total = await vista_y_total(cliente, cliente_a, a)
    cuerpo = {"nivel_esperado": 1, "total_esperado": str(total)}
    rs = await asyncio.gather(
        reprogramar(cliente, cliente_a, a, **cuerpo), reprogramar(cliente, cliente_b, b, **cuerpo)
    )
    assert sorted(r.status_code for r in rs) == [200, 409], [r.text for r in rs]
    perdedora = next(r for r in rs if r.status_code == 409)
    assert codigo(perdedora) == "tramo_no_disponible"
    assert sql("select count(*) from public.reprogramacion") == [(1,)]


# --- seguridad -----------------------------------------------------------------------------------


async def test_quien_puede_reprogramar(
    cliente: AsyncClient,
    cliente_a: UsuarioDePrueba,
    cliente_b: UsuarioDePrueba,
    personal: UsuarioDePrueba,
    administrador: UsuarioDePrueba,
    reserva_con_pagos: Callable[..., str],
    nuevo_dia: str,
    sql: Ejecutar,
) -> None:
    id_ = reserva_con_pagos(cliente_a, 1)
    antes = estado_de(sql, id_)
    for ruta, cuerpo in list(CUERPOS.items())[:2]:  # la eleccion se prueba aparte
        url = f"{RESERVAS}/{id_}/{ruta}"
        assert (await cliente.post(url, json=cuerpo)).status_code == 401
        r = await cliente.post(url, json=cuerpo, headers=con(cliente_b))
        assert (r.status_code, codigo(r)) == (404, "no_encontrado")
        for ajeno in (personal, administrador):  # el administrador solo tras el estudio
            r = await cliente.post(url, json=cuerpo, headers=con(ajeno))
            assert (r.status_code, codigo(r)) == (403, "sin_permiso"), ruta
        r = await cliente.post(
            f"{RESERVAS}/{UUID(int=7)}/{ruta}", json=cuerpo, headers=con(cliente_a)
        )
        assert r.status_code == 404
    assert estado_de(sql, id_) == antes
    assert sql("select count(*) from public.reprogramacion") == [(0,)]


async def test_401_con_token_de_alg_cambiado_o_caducado(
    cliente: AsyncClient, cliente_a: UsuarioDePrueba, reserva_con_pagos: Callable[..., str]
) -> None:
    id_ = reserva_con_pagos(cliente_a, 1)
    cabecera, carga, firma = cliente_a.token.split(".")
    datos = json.loads(base64.urlsafe_b64decode(cabecera + "=="))
    falsa = base64.urlsafe_b64encode(json.dumps(datos | {"alg": "HS256"}).encode()).rstrip(b"=")
    otra = base64.urlsafe_b64encode(json.dumps(datos | {"alg": "none"}).encode()).rstrip(b"=")
    for token in (f"{falsa.decode()}.{carga}.{firma}", f"{otra.decode()}.{carga}."):
        for ruta, cuerpo in CUERPOS.items():
            r = await cliente.post(
                f"{RESERVAS}/{id_}/{ruta}",
                json=cuerpo,
                headers={"Authorization": f"Bearer {token}"},
            )
            assert r.status_code == 401, (ruta, r.text)


async def test_503_con_la_base_caida_nunca_500(
    monkeypatch: pytest.MonkeyPatch, cliente_a: UsuarioDePrueba
) -> None:
    monkeypatch.setenv("URL_BASE_DATOS", "postgresql://u:p@127.0.0.1:1/db")
    monkeypatch.setenv("TIMEOUT_POOL_SEGUNDOS", "0.5")
    obtener_configuracion.cache_clear()
    app = crear_app()
    async with (
        app.router.lifespan_context(app),
        AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c,
    ):
        for ruta, cuerpo in CUERPOS.items():
            r = await c.post(
                f"{RESERVAS}/{UUID(int=9)}/{ruta}", json=cuerpo, headers=con(cliente_a)
            )
            assert (r.status_code, codigo(r)) == (503, "base_de_datos_no_disponible"), ruta


def test_openapi_declara_los_codigos_de_reprogramacion(app: FastAPI) -> None:
    rutas = app.openapi()["paths"]
    esperados = {
        "/api/v1/reservas/{id_reserva}/reprogramar/simular": {200, 401, 403, 404, 409, 422, 503},
        "/api/v1/reservas/{id_reserva}/reprogramar": {200, 401, 403, 404, 409, 422, 503},
        "/api/v1/reservas/{id_reserva}/eleccion-estudio": {200, 401, 403, 404, 409, 422, 503},
    }
    for ruta, codigos in esperados.items():
        assert codigos <= {int(c) for c in rutas[ruta]["post"]["responses"]}, ruta


# --- cancelacion del estudio (CA-13) -------------------------------------------------------------


@pytest.fixture
def cancelada_por_el_estudio(
    cliente: AsyncClient,
    administrador: UsuarioDePrueba,
    reserva_con_pagos: Callable[..., str],
) -> Callable[..., Any]:
    async def crear(usuario: UsuarioDePrueba) -> str:
        id_ = reserva_con_pagos(usuario, 1)
        r = await cliente.post(
            f"{RESERVAS}/{id_}/cancelar",
            json={"por": "estudio", "nota": "Averia en la sala"},
            headers=con(administrador),
        )
        assert r.status_code == 200 and r.json()["eleccion_estudio"] == "pendiente", r.text
        return id_

    return crear


async def test_reprogramar_sin_costo_tras_la_cancelacion_del_estudio(
    cliente: AsyncClient,
    cliente_a: UsuarioDePrueba,
    administrador: UsuarioDePrueba,
    cancelada_por_el_estudio: Callable[..., Any],
    nuevo_dia: str,
    sql: Ejecutar,
) -> None:
    id_ = await cancelada_por_el_estudio(cliente_a)
    r = await simular(cliente, cliente_a, id_)
    assert r.status_code == 200, r.text
    vista = r.json()
    assert (vista["nivel"], vista["penalizacion"], vista["credito"]) == (None, "0.00", "0.00")
    assert (vista["precio"]["total"], vista["saldo"]) == ("200", "100.00")
    assert vista["reprogramaciones_restantes"] == 2  # no cuenta para los limites
    r = await reprogramar(cliente, cliente_a, id_, nivel_esperado=None)
    assert r.status_code == 200, r.text
    reserva = r.json()
    assert (reserva["estado"], reserva["motivo_cancelacion"]) == ("confirmada", None)
    assert reserva["eleccion_estudio"] == "reprogramada" and reserva["inicio"] == NUEVO
    assert "cancelacion" not in reserva and "devolucion" not in reserva
    assert reserva["precio"]["total"] == "200"  # el mismo precio, sin recalcular
    assert reserva["reprogramaciones"][0]["nivel"] is None
    assert {c["hito"]: c["estado"] for c in reserva["cuotas"]} == {
        "al_reservar": "pagada",
        "al_terminar": "pendiente",
    }
    assert sql("select count(*) from public.credito") == [(0,)]
    avisos = sql(
        "select count(*) from public.notificacion where tipo = 'eleccion_estudio_resuelta' "
        "and datos ->> 'opcion' = 'reprogramar' and destinatario = %s",
        administrador.correo,
    )
    assert avisos == [(1,)]


async def test_el_administrador_reprograma_por_el_cliente_tras_el_estudio(
    cliente: AsyncClient,
    cliente_a: UsuarioDePrueba,
    administrador: UsuarioDePrueba,
    cancelada_por_el_estudio: Callable[..., Any],
    nuevo_dia: str,
    sql: Ejecutar,
) -> None:
    id_ = await cancelada_por_el_estudio(cliente_a)
    r = await reprogramar(cliente, administrador, id_, nivel_esperado=None)
    assert r.status_code == 200, r.text
    assert r.json()["eleccion_estudio"] == "reprogramada"
    avisos = sql(
        "select count(*) from public.notificacion where tipo = 'eleccion_estudio_resuelta' "
        "and destinatario = %s",
        administrador.correo,
    )
    assert avisos == [(0,)]


async def test_tras_el_estudio_el_nivel_esperado_es_null_y_el_tramo_se_respeta(
    cliente: AsyncClient,
    cliente_a: UsuarioDePrueba,
    cliente_b: UsuarioDePrueba,
    cancelada_por_el_estudio: Callable[..., Any],
    reservar: Callable[..., str],
    nuevo_dia: str,
) -> None:
    id_ = await cancelada_por_el_estudio(cliente_a)
    r = await reprogramar(cliente, cliente_a, id_, nivel_esperado=1)
    assert (r.status_code, codigo(r)) == (409, "nivel_cambiado")
    reservar(cliente_b.id, "2027-07-05T10:00:00-05:00", "2027-07-05T12:00:00-05:00")
    r = await reprogramar(cliente, cliente_a, id_, nivel_esperado=None)
    assert (r.status_code, codigo(r)) == (409, "tramo_no_disponible")


async def test_elegir_la_devolucion_integra_del_estudio(
    cliente: AsyncClient,
    cliente_a: UsuarioDePrueba,
    cancelada_por_el_estudio: Callable[..., Any],
    sql: Ejecutar,
    administrador: UsuarioDePrueba,
) -> None:
    id_ = await cancelada_por_el_estudio(cliente_a)
    url = f"{RESERVAS}/{id_}/eleccion-estudio"
    r = await cliente.post(url, json={"opcion": "devolucion"}, headers=con(cliente_a))
    assert r.status_code == 200, r.text
    reserva = r.json()
    assert (reserva["estado"], reserva["eleccion_estudio"]) == ("cancelada", "devolucion")
    d = reserva["devolucion"]
    assert (d["tipo"], d["estado"], d["id_credito"], d["id_reserva"]) == (
        "estudio",
        "aprobada",
        None,
        id_,
    )
    assert (d["monto_solicitado"], d["monto_aprobado"]) == ("100.00", "100.00")
    assert d["limite"] is not None
    plazo = sql(
        "select limite = public.sumar_dias_habiles(solicitada_en, 7) from public.devolucion"
    )
    assert plazo == [(True,)]
    avisos = sql(
        "select count(*) from public.notificacion where tipo = 'eleccion_estudio_resuelta' "
        "and datos ->> 'opcion' = 'devolucion' and destinatario = %s",
        administrador.correo,
    )
    assert avisos == [(1,)]
    r = await cliente.post(url, json={"opcion": "devolucion"}, headers=con(cliente_a))
    assert (r.status_code, codigo(r)) == (409, "eleccion_no_disponible")
    # El administrador la marca realizada como cualquier devolucion.
    r = await cliente.post(
        f"/api/v1/devoluciones/{d['id']}/realizada",
        json={"nota": "Yape 123"},
        headers=con(administrador),
    )
    assert r.status_code == 200, r.text
    r = await simular(cliente, cliente_a, id_)
    assert (r.status_code, codigo(r)) == (409, "reprogramacion_no_permitida")


async def test_con_varias_devoluciones_del_estudio_la_reserva_trae_la_mas_reciente(
    cliente: AsyncClient,
    cliente_a: UsuarioDePrueba,
    cancelada_por_el_estudio: Callable[..., Any],
    sql: Ejecutar,
) -> None:
    id_ = await cancelada_por_el_estudio(cliente_a)
    url = f"{RESERVAS}/{id_}/eleccion-estudio"
    await cliente.post(url, json={"opcion": "devolucion"}, headers=con(cliente_a))
    # La mas antigua se inserta despues: manda la fecha de solicitud, no el orden en que se lee.
    sql(
        "insert into public.devolucion (id, id_reserva, id_cliente, tipo, motivo, "
        "monto_solicitado, estado, monto_aprobado, solicitada_en, decidida_en, limite) "
        "values (gen_random_uuid(), %s, %s, 'estudio', 'Pago tardio', 7, 'aprobada', 7, "
        "now() - interval '1 hour', now(), now())",
        UUID(id_),
        cliente_a.id,
    )
    r = await cliente.get(f"{RESERVAS}/{id_}", headers=con(cliente_a))
    assert r.status_code == 200 and r.json()["devolucion"]["monto_aprobado"] == "100.00"


async def test_el_administrador_elige_por_el_cliente(
    cliente: AsyncClient,
    cliente_a: UsuarioDePrueba,
    administrador: UsuarioDePrueba,
    cancelada_por_el_estudio: Callable[..., Any],
) -> None:
    id_ = await cancelada_por_el_estudio(cliente_a)
    r = await cliente.post(
        f"{RESERVAS}/{id_}/eleccion-estudio",
        json={"opcion": "devolucion"},
        headers=con(administrador),
    )
    assert r.status_code == 200 and r.json()["devolucion"]["cliente"]["id"] == str(cliente_a.id)


async def test_la_eleccion_sin_pendiente_o_ya_hecha_es_409_y_nadie_mas_elige(
    cliente: AsyncClient,
    cliente_a: UsuarioDePrueba,
    cliente_b: UsuarioDePrueba,
    personal: UsuarioDePrueba,
    cancelada_por_el_estudio: Callable[..., Any],
    reserva_con_pagos: Callable[..., str],
    nuevo_dia: str,
    sql: Ejecutar,
) -> None:
    normal = reserva_con_pagos(cliente_a, 1)
    cuerpo = {"opcion": "devolucion"}
    r = await cliente.post(
        f"{RESERVAS}/{normal}/eleccion-estudio", json=cuerpo, headers=con(cliente_a)
    )
    assert (r.status_code, codigo(r)) == (409, "eleccion_no_disponible")
    pendiente = await cancelada_por_el_estudio(cliente_a)
    url = f"{RESERVAS}/{pendiente}/eleccion-estudio"
    assert (await cliente.post(url, json=cuerpo)).status_code == 401
    r = await cliente.post(url, json=cuerpo, headers=con(cliente_b))
    assert (r.status_code, codigo(r)) == (404, "no_encontrado")
    r = await cliente.post(url, json=cuerpo, headers=con(personal))
    assert (r.status_code, codigo(r)) == (403, "sin_permiso")
    for malo in ({"opcion": "reprogramar"}, {}, {"opcion": "devolucion", "monto": "1.00"}):
        r = await cliente.post(url, json=malo, headers=con(cliente_a))
        assert (r.status_code, codigo(r)) == (422, "datos_invalidos"), malo
    assert sql("select count(*) from public.devolucion") == [(0,)]
    assert estado_de(sql, pendiente)[3] == "pendiente"
    # Reprogramada ya, no se elige la devolucion.
    r = await reprogramar(cliente, cliente_a, pendiente, nivel_esperado=None)
    assert r.status_code == 200, r.text
    r = await cliente.post(url, json=cuerpo, headers=con(cliente_a))
    assert (r.status_code, codigo(r)) == (409, "eleccion_no_disponible")


async def test_mientras_la_eleccion_esta_pendiente_nada_vence(
    cliente_a: UsuarioDePrueba,
    cancelada_por_el_estudio: Callable[..., Any],
    sql: Ejecutar,
) -> None:
    id_ = await cancelada_por_el_estudio(cliente_a)
    antes = estado_de(sql, id_)
    sql("select public.avanzar_reservas(), public.caducar_reservas(), public.procesar_creditos()")
    assert estado_de(sql, id_) == antes


# --- disponibilidad con `excluir_reserva` ---------------------------------------------------------


async def test_disponibilidad_excluye_la_propia_reserva_solo_para_su_dueno_o_el_administrador(
    cliente: AsyncClient,
    cliente_a: UsuarioDePrueba,
    cliente_b: UsuarioDePrueba,
    administrador: UsuarioDePrueba,
    reserva_con_pagos: Callable[..., str],
    franja: Callable[[str, str], str],
    sala: str,
) -> None:
    franja("2027-06-01 08:00-05", "2027-06-01 20:00-05")
    id_ = reserva_con_pagos(cliente_a, 1)
    base = {
        "sala": sala,
        "desde": "2027-06-01T08:00:00-05:00",
        "hasta": "2027-06-01T20:00:00-05:00",
    }

    async def ocupados(usuario: UsuarioDePrueba | None, **extra: str) -> int:
        r = await cliente.get(
            "/api/v1/disponibilidad",
            params={**base, **extra},
            headers=con(usuario) if usuario else None,
        )
        assert r.status_code == 200, r.text
        return len(r.json()["ocupados"])

    assert await ocupados(cliente_a) == 1
    assert await ocupados(cliente_a, excluir_reserva=id_) == 0  # el dueno la ve libre
    assert await ocupados(administrador, excluir_reserva=id_) == 0
    assert await ocupados(cliente_b, excluir_reserva=id_) == 1  # otro cliente: se ignora
    assert await ocupados(None, excluir_reserva=id_) == 1  # anonimo: se ignora
    assert await ocupados(cliente_a, excluir_reserva=str(UUID(int=5))) == 1  # inexistente


def _captura_en_validacion(
    configuracion: Configuracion, sql: Ejecutar, usuario: UsuarioDePrueba, id_: str
) -> None:
    """El cliente subio la captura del saldo y el estudio aun no la valida."""
    cuota = sql(
        "select id from public.cuota where id_reserva = %s and hito = 'al_terminar'", UUID(id_)
    )[0][0]
    with psycopg.connect(configuracion.url_base_datos_admin) as c:
        c.execute("set local role authenticated")
        claims = json.dumps({"sub": str(usuario.id), "role": "authenticated"})
        c.execute("select set_config('request.jwt.claims', %s, true)", (claims,))
        c.execute(
            "insert into public.comprobante_pago (id_cuota, id_cliente, metodo, monto, "
            "numero_operacion, ruta_captura, tipo_captura) "
            "values (%s, %s, 'yape', 50, %s, %s, 'image/png')",
            (cuota, usuario.id, f"OP-{id_[:8]}", f"{usuario.id}/{id_[:8]}.png"),
        )


@pytest.mark.parametrize("ruta", ["eleccion-estudio", "reprogramar", "reprogramar/simular"])
async def test_con_una_captura_en_validacion_no_se_elige_tras_la_cancelacion_del_estudio(
    cliente: AsyncClient,
    cliente_a: UsuarioDePrueba,
    administrador: UsuarioDePrueba,
    reserva_con_pagos: Callable[..., str],
    configuracion: Configuracion,
    nuevo_dia: str,
    sql: Ejecutar,
    ruta: str,
) -> None:
    id_ = reserva_con_pagos(cliente_a, 1)
    _captura_en_validacion(configuracion, sql, cliente_a, id_)
    r = await cliente.post(
        f"{RESERVAS}/{id_}/cancelar",
        json={"por": "estudio", "nota": "Averia en la sala"},
        headers=con(administrador),
    )
    assert r.json()["eleccion_estudio"] == "pendiente", r.text
    antes = estado_de(sql, id_)
    cuerpo = {**CUERPOS[ruta], **({"total_esperado": None} if ruta == "reprogramar" else {})}
    if ruta == "reprogramar":
        cuerpo["nivel_esperado"] = None
    r = await cliente.post(f"{RESERVAS}/{id_}/{ruta}", json=cuerpo, headers=con(cliente_a))
    try:
        assert (r.status_code, codigo(r)) == (409, "eleccion_no_disponible"), r.text
        assert "validemos tu pago" in r.json()["error"]["mensaje"]
        assert estado_de(sql, id_) == antes
        assert sql("select count(*) from public.devolucion") == [(0,)]
    finally:
        sql("delete from public.comprobante_pago where starts_with(numero_operacion, 'OP-')")
