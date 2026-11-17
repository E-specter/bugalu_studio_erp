"""API de RF-02: catalogo, tarifas, recargos, feriados y simulacion (stack local con RLS real)."""

from collections.abc import Callable
from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal
from typing import Any
from uuid import UUID, uuid4

import pytest
from fastapi import FastAPI
from httpx import AsyncClient

from bugalu.modulos.catalogo.dominio.precio import (
    ConfiguracionImpuestos,
    Especialista,
    Recargos,
    Servicio,
    Unidad,
    calcular_simulacion,
)

pytestmark = pytest.mark.integracion

Cabeceras = dict[str, str]
Sql = Callable[..., list[tuple[Any, ...]]]
LIMA = timezone(timedelta(hours=-5))
D = Decimal

SERVICIO = {
    "id", "nombre", "categoria", "ocupa_sala", "tarifa_hora", "monto_fijo",
    "especialistas_por_defecto", "activo",
}  # fmt: skip
ESPECIALISTA = {"id", "nombre", "monto_fijo", "monto_variable", "unidad", "activo"}


async def _servicios(cliente: AsyncClient) -> dict[str, dict[str, Any]]:
    return {s["nombre"]: s for s in (await cliente.get("/api/v1/servicios")).json()}


async def _especialistas(cliente: AsyncClient) -> dict[str, dict[str, Any]]:
    return {e["nombre"]: e for e in (await cliente.get("/api/v1/especialistas")).json()}


def _sala(sql: Sql) -> str:
    return str(sql("select id from public.sala_tecnica limit 1")[0][0])


def _tramo(dia: int, desde: int, hasta: int, mes: int = 12) -> dict[str, str]:
    return {
        "inicio": datetime(2026, mes, dia, desde, tzinfo=LIMA).isoformat(),
        "fin": datetime(2026, mes, dia, hasta, tzinfo=LIMA).isoformat(),
    }


# --- lectura publica -----------------------------------------------------------------------------


async def test_lectura_publica_de_servicios_especialistas_y_recargos(cliente: AsyncClient) -> None:
    servicios = (await cliente.get("/api/v1/servicios")).json()
    assert len(servicios) == 7 and all(set(s) == SERVICIO for s in servicios)
    voces = next(s for s in servicios if s["nombre"] == "Grabación de voces")
    assert voces["tarifa_hora"] == "80.00" and voces["monto_fijo"] == "0.00"
    assert voces["categoria"] == "grabacion" and voces["ocupa_sala"] is True
    especialistas = (await cliente.get("/api/v1/especialistas")).json()
    assert len(especialistas) == 4 and all(set(e) == ESPECIALISTA for e in especialistas)
    ingeniero = next(e for e in especialistas if e["nombre"] == "Ingeniero de sonido")
    assert voces["especialistas_por_defecto"] == [ingeniero["id"]]
    assert (ingeniero["monto_fijo"], ingeniero["monto_variable"], ingeniero["unidad"]) == (
        "30.00", "25.00", "lapso_30",
    )  # fmt: skip
    assert (await cliente.get("/api/v1/recargos")).json() == {
        "noche": {"porcentaje": "25.00", "desde": "20:00", "hasta": "06:00"},
        "fin_de_semana": {"porcentaje": "20.00"},
        "feriado": {"porcentaje": "30.00"},
    }


async def test_la_lectura_publica_ignora_un_token_invalido(cliente: AsyncClient) -> None:
    r = await cliente.get("/api/v1/servicios", headers={"Authorization": "Bearer basura"})
    assert r.status_code == 200


# --- servicios -----------------------------------------------------------------------------------


async def test_el_administrador_edita_el_servicio_y_reemplaza_sus_especialistas(
    cliente: AsyncClient, administrador: Cabeceras
) -> None:
    servicios, especialistas = await _servicios(cliente), await _especialistas(cliente)
    voces = servicios["Grabación de voces"]
    ejecutante = especialistas["Ejecutante"]["id"]
    r = await cliente.patch(
        f"/api/v1/servicios/{voces['id']}",
        headers=administrador,
        json={
            "tarifa_hora": "99.5",
            "monto_fijo": "12.00",
            "activo": False,
            "especialistas_por_defecto": [ejecutante, ejecutante],
        },
    )
    assert r.status_code == 200
    assert r.json() == {
        **voces,
        "tarifa_hora": "99.50",
        "monto_fijo": "12.00",
        "activo": False,
        "especialistas_por_defecto": [ejecutante],
    }
    assert (await _servicios(cliente))["Grabación de voces"] == r.json()


async def test_un_patch_parcial_no_toca_los_demas_campos(
    cliente: AsyncClient, administrador: Cabeceras
) -> None:
    voces = (await _servicios(cliente))["Grabación de voces"]
    r = await cliente.patch(
        f"/api/v1/servicios/{voces['id']}", headers=administrador, json={"monto_fijo": "5"}
    )
    assert r.json() == {**voces, "monto_fijo": "5.00"}


async def test_lista_vacia_quita_todos_los_especialistas_por_defecto(
    cliente: AsyncClient, administrador: Cabeceras
) -> None:
    voces = (await _servicios(cliente))["Grabación de voces"]
    r = await cliente.patch(
        f"/api/v1/servicios/{voces['id']}",
        headers=administrador,
        json={"especialistas_por_defecto": []},
    )
    assert r.json()["especialistas_por_defecto"] == []


async def test_un_cliente_no_edita_servicios_y_la_fila_queda_intacta(
    cliente: AsyncClient, cliente_sin_rol: Cabeceras, sql: Sql
) -> None:
    voces = (await _servicios(cliente))["Grabación de voces"]
    antes = sql("select * from public.servicio order by id")
    r = await cliente.patch(
        f"/api/v1/servicios/{voces['id']}",
        headers=cliente_sin_rol,
        json={"tarifa_hora": "1", "especialistas_por_defecto": []},
    )
    assert r.status_code == 403 and r.json()["error"]["codigo"] == "sin_permiso"
    assert sql("select * from public.servicio order by id") == antes
    assert (await _servicios(cliente))["Grabación de voces"] == voces


async def test_sin_token_la_escritura_es_401(cliente: AsyncClient) -> None:
    r = await cliente.patch(f"/api/v1/servicios/{uuid4()}", json={"activo": False})
    assert r.status_code == 401 and r.json()["error"]["codigo"] == "no_autenticado"


async def test_servicio_o_especialista_inexistente_es_404(
    cliente: AsyncClient, administrador: Cabeceras
) -> None:
    r = await cliente.patch(f"/api/v1/servicios/{uuid4()}", headers=administrador, json={})
    assert r.status_code == 404 and r.json()["error"]["codigo"] == "no_encontrado"
    r = await cliente.patch(f"/api/v1/especialistas/{uuid4()}", headers=administrador, json={})
    assert r.status_code == 404


@pytest.mark.parametrize(
    "cuerpo",
    [
        {"tarifa_hora": "-1"},
        {"tarifa_hora": "1.234"},
        {"tarifa_hora": "100000000.00"},
        {"tarifa_hora": "abc"},
        {"tarifa_hora": "NaN"},
        {"tarifa_hora": None},
        {"monto_fijo": "-0.01"},
        {"activo": None},
        {"activo": "quizas"},
        {"especialistas_por_defecto": [str(uuid4())]},
        {"especialistas_por_defecto": ["no-es-uuid"]},
        {"especialistas_por_defecto": None},
        {"nombre": "Otro nombre"},
        {"categoria": "ensayo"},
    ],
)
async def test_servicio_con_datos_invalidos_es_422_y_no_cambia_nada(
    cliente: AsyncClient, administrador: Cabeceras, sql: Sql, cuerpo: dict[str, Any]
) -> None:
    voces = (await _servicios(cliente))["Grabación de voces"]
    antes = sql("select * from public.servicio order by id")
    r = await cliente.patch(f"/api/v1/servicios/{voces['id']}", headers=administrador, json=cuerpo)
    assert r.status_code == 422 and r.json()["error"]["codigo"] == "datos_invalidos"
    assert sql("select * from public.servicio order by id") == antes
    assert (await _servicios(cliente))["Grabación de voces"] == voces


# --- especialistas -------------------------------------------------------------------------------


async def test_el_administrador_edita_un_especialista(
    cliente: AsyncClient, administrador: Cabeceras
) -> None:
    ejecutante = (await _especialistas(cliente))["Ejecutante"]
    r = await cliente.patch(
        f"/api/v1/especialistas/{ejecutante['id']}",
        headers=administrador,
        json={"monto_fijo": "0", "monto_variable": "33.3", "unidad": "lapso_30", "activo": False},
    )
    assert r.status_code == 200
    assert r.json() == {
        **ejecutante,
        "monto_fijo": "0.00",
        "monto_variable": "33.30",
        "unidad": "lapso_30",
        "activo": False,
    }


async def test_un_cliente_no_edita_especialistas_y_la_fila_queda_intacta(
    cliente: AsyncClient, cliente_sin_rol: Cabeceras, sql: Sql
) -> None:
    ejecutante = (await _especialistas(cliente))["Ejecutante"]
    antes = sql("select * from public.especialista order by id")
    r = await cliente.patch(
        f"/api/v1/especialistas/{ejecutante['id']}", headers=cliente_sin_rol, json={"activo": False}
    )
    assert r.status_code == 403
    assert sql("select * from public.especialista order by id") == antes


@pytest.mark.parametrize(
    "cuerpo",
    [
        {"unidad": "dia"},
        {"unidad": None},
        {"monto_fijo": "-1"},
        {"monto_variable": "-5.00"},
        {"monto_variable": "1.999"},
        {"activo": "tal vez"},
        {"nombre": "Otro"},
    ],
)
async def test_especialista_con_datos_invalidos_es_422(
    cliente: AsyncClient, administrador: Cabeceras, sql: Sql, cuerpo: dict[str, Any]
) -> None:
    ejecutante = (await _especialistas(cliente))["Ejecutante"]
    antes = sql("select * from public.especialista order by id")
    r = await cliente.patch(
        f"/api/v1/especialistas/{ejecutante['id']}", headers=administrador, json=cuerpo
    )
    assert r.status_code == 422 and r.json()["error"]["codigo"] == "datos_invalidos"
    assert sql("select * from public.especialista order by id") == antes


# --- recargos ------------------------------------------------------------------------------------

RECARGOS = {
    "noche": {"porcentaje": "10", "desde": "22:30", "hasta": "05:00"},
    "fin_de_semana": {"porcentaje": "15.5"},
    "feriado": {"porcentaje": "0"},
}


async def test_el_administrador_reemplaza_los_recargos(
    cliente: AsyncClient, administrador: Cabeceras
) -> None:
    r = await cliente.put("/api/v1/recargos", headers=administrador, json=RECARGOS)
    esperado = {
        "noche": {"porcentaje": "10.00", "desde": "22:30", "hasta": "05:00"},
        "fin_de_semana": {"porcentaje": "15.50"},
        "feriado": {"porcentaje": "0.00"},
    }
    assert r.status_code == 200 and r.json() == esperado
    assert (await cliente.get("/api/v1/recargos")).json() == esperado


async def test_un_cliente_no_cambia_los_recargos(
    cliente: AsyncClient, cliente_sin_rol: Cabeceras, sql: Sql
) -> None:
    antes = sql("select * from public.recargo order by tipo")
    r = await cliente.put("/api/v1/recargos", headers=cliente_sin_rol, json=RECARGOS)
    assert r.status_code == 403 and r.json()["error"]["codigo"] == "sin_permiso"
    assert sql("select * from public.recargo order by tipo") == antes


def _recargos(**cambios: Any) -> dict[str, Any]:
    return {**RECARGOS, **cambios}


@pytest.mark.parametrize(
    "cuerpo",
    [
        _recargos(feriado={"porcentaje": "300.01"}),
        _recargos(feriado={"porcentaje": "-1"}),
        _recargos(fin_de_semana={"porcentaje": "1.234"}),
        _recargos(noche={"porcentaje": "10", "desde": "25:00", "hasta": "05:00"}),
        _recargos(noche={"porcentaje": "10", "desde": "22:00", "hasta": "5am"}),
        _recargos(noche={"porcentaje": "10", "desde": "22:00", "hasta": "22:00"}),
        _recargos(noche={"porcentaje": "10", "desde": "22:00"}),
        _recargos(noche={"porcentaje": "10", "desde": "22:00:00", "hasta": "05:00"}),
        _recargos(feriado={"porcentaje": "10", "desde": "01:00"}),
        {"noche": RECARGOS["noche"], "feriado": RECARGOS["feriado"]},
        {**RECARGOS, "otro": {"porcentaje": "1"}},
    ],
)
async def test_recargos_invalidos_son_422_y_no_cambian_nada(
    cliente: AsyncClient, administrador: Cabeceras, sql: Sql, cuerpo: dict[str, Any]
) -> None:
    antes = sql("select * from public.recargo order by tipo")
    r = await cliente.put("/api/v1/recargos", headers=administrador, json=cuerpo)
    assert r.status_code == 422 and r.json()["error"]["codigo"] == "datos_invalidos"
    assert sql("select * from public.recargo order by tipo") == antes


# --- feriados ------------------------------------------------------------------------------------


async def test_alta_lista_y_baja_de_feriados(
    cliente: AsyncClient, administrador: Cabeceras
) -> None:
    r = await cliente.post(
        "/api/v1/feriados", headers=administrador, json={"fecha": "2026-12-25", "nombre": "Navidad"}
    )
    assert r.status_code == 201 and r.json() == {"fecha": "2026-12-25", "nombre": "Navidad"}
    await cliente.post(
        "/api/v1/feriados",
        headers=administrador,
        json={"fecha": "2027-01-01", "nombre": "Año Nuevo"},
    )
    todos = (await cliente.get("/api/v1/feriados")).json()
    assert [f["fecha"] for f in todos] == ["2026-12-25", "2027-01-01"]
    de_2026 = (await cliente.get("/api/v1/feriados", params={"anio": 2026})).json()
    assert de_2026 == [{"fecha": "2026-12-25", "nombre": "Navidad"}]
    assert (await cliente.get("/api/v1/feriados", params={"anio": 2030})).json() == []
    r = await cliente.delete("/api/v1/feriados/2026-12-25", headers=administrador)
    assert r.status_code == 204 and r.content == b""
    assert len((await cliente.get("/api/v1/feriados")).json()) == 1


async def test_feriado_repetido_es_409_y_borrar_uno_inexistente_es_404(
    cliente: AsyncClient, administrador: Cabeceras
) -> None:
    cuerpo = {"fecha": "2026-12-25", "nombre": "Navidad"}
    await cliente.post("/api/v1/feriados", headers=administrador, json=cuerpo)
    r = await cliente.post(
        "/api/v1/feriados", headers=administrador, json={**cuerpo, "nombre": "x"}
    )
    assert r.status_code == 409 and r.json()["error"]["codigo"] == "feriado_repetido"
    assert (await cliente.get("/api/v1/feriados")).json() == [cuerpo]
    r = await cliente.delete("/api/v1/feriados/2026-12-31", headers=administrador)
    assert r.status_code == 404


async def test_un_cliente_no_altera_feriados(
    cliente: AsyncClient, cliente_sin_rol: Cabeceras, administrador: Cabeceras, sql: Sql
) -> None:
    cuerpo = {"fecha": "2026-12-25", "nombre": "Navidad"}
    r = await cliente.post("/api/v1/feriados", headers=cliente_sin_rol, json=cuerpo)
    assert r.status_code == 403 and sql("select count(*) from public.feriado") == [(0,)]
    await cliente.post("/api/v1/feriados", headers=administrador, json=cuerpo)
    r = await cliente.delete("/api/v1/feriados/2026-12-25", headers=cliente_sin_rol)
    assert r.status_code == 403 and sql("select count(*) from public.feriado") == [(1,)]


@pytest.mark.parametrize("anio", ["abc", "1", "99999", "2026.5"])
async def test_anio_invalido_es_422(cliente: AsyncClient, anio: str) -> None:
    r = await cliente.get("/api/v1/feriados", params={"anio": anio})
    assert r.status_code == 422 and r.json()["error"]["codigo"] == "datos_invalidos"


@pytest.mark.parametrize(
    "cuerpo",
    [
        {"fecha": "2026-13-01", "nombre": "x"},
        {"fecha": "ayer", "nombre": "x"},
        {"fecha": "2026-12-25"},
        {"fecha": "2026-12-25", "nombre": ""},
        {"fecha": "2026-12-25", "nombre": "x" * 201},
        {"fecha": "2026-12-25", "nombre": "x", "otro": 1},
    ],
)
async def test_feriado_invalido_es_422(
    cliente: AsyncClient, administrador: Cabeceras, sql: Sql, cuerpo: dict[str, Any]
) -> None:
    r = await cliente.post("/api/v1/feriados", headers=administrador, json=cuerpo)
    assert r.status_code == 422 and sql("select count(*) from public.feriado") == [(0,)]


@pytest.mark.parametrize("valor", ["a\u0000b", "a\x07b", "a\x1fb", "a\x7fb", "a\x85b", "a b"])
async def test_nombre_de_feriado_con_caracteres_de_control_es_422_nunca_500(
    cliente: AsyncClient, administrador: Cabeceras, sql: Sql, valor: str
) -> None:
    r = await cliente.post(
        "/api/v1/feriados", headers=administrador, json={"fecha": "2026-12-25", "nombre": valor}
    )
    assert r.status_code == 422 and r.json()["error"]["codigo"] == "datos_invalidos"
    assert sql("select count(*) from public.feriado") == [(0,)]


async def test_fecha_invalida_al_borrar_es_422(
    cliente: AsyncClient, administrador: Cabeceras
) -> None:
    r = await cliente.delete("/api/v1/feriados/no-es-fecha", headers=administrador)
    assert r.status_code == 422


# --- simulacion ----------------------------------------------------------------------------------


async def _motor(
    cliente: AsyncClient, servicio: str, elegidos: list[str], inicio: str, fin: str
) -> Any:
    """Calcula lo esperado con el motor del dominio a partir de lo que publica la API."""
    s = (await _servicios(cliente))[servicio]
    esp = {e["id"]: e for e in (await cliente.get("/api/v1/especialistas")).json()}
    r = (await cliente.get("/api/v1/recargos")).json()
    feriados = {
        date.fromisoformat(f["fecha"]) for f in (await cliente.get("/api/v1/feriados")).json()
    }

    def convertir(e: dict[str, Any]) -> Especialista:
        return Especialista(
            UUID(e["id"]), e["nombre"], D(e["monto_fijo"]), D(e["monto_variable"]),
            Unidad(e["unidad"]), e["activo"],
        )  # fmt: skip

    dominio = Servicio(
        UUID(s["id"]), s["nombre"], s["categoria"], s["ocupa_sala"], D(s["tarifa_hora"]),
        D(s["monto_fijo"]), tuple(UUID(i) for i in s["especialistas_por_defecto"]), s["activo"],
    )  # fmt: skip
    recargos = Recargos(
        D(r["noche"]["porcentaje"]), time.fromisoformat(r["noche"]["desde"]),
        time.fromisoformat(r["noche"]["hasta"]), D(r["fin_de_semana"]["porcentaje"]),
        D(r["feriado"]["porcentaje"]),
    )  # fmt: skip
    return calcular_simulacion(
        dominio,
        [convertir(esp[i]) for i in s["especialistas_por_defecto"]],
        [convertir(esp[i]) for i in elegidos],
        datetime.fromisoformat(inicio),
        datetime.fromisoformat(fin),
        recargos,
        feriados,
        ConfiguracionImpuestos(D("18.00"), True),
        50,
    )


def _esperado(sim: Any) -> dict[str, Any]:
    return {
        "lineas": [
            {"concepto": x.concepto, "cantidad": str(x.cantidad), "unidad": x.unidad,
             "monto": str(x.monto)}
            for x in sim.lineas
        ],
        "recargos": [
            {"tipo": x.tipo, "bloques": x.bloques, "monto": str(x.monto)} for x in sim.recargos
        ],
        "total": str(sim.total),
        "anticipo": str(sim.anticipo),
        "porcentaje_adelanto": "50.00",
        "impuesto": {
            "nombre": "IGV", "porcentaje": "18.00", "incluido": True,
            "base": str(sim.impuesto.base), "monto": str(sim.impuesto.monto),
        },
    }  # fmt: skip


async def test_la_simulacion_publica_coincide_con_el_motor(
    cliente: AsyncClient, administrador: Cabeceras, sql: Sql
) -> None:
    await cliente.post(
        "/api/v1/feriados",
        headers=administrador,
        json={"fecha": "2026-12-24", "nombre": "Nochebuena"},
    )
    servicios, especialistas = await _servicios(cliente), await _especialistas(cliente)
    voces, ejecutante = servicios["Grabación de voces"], especialistas["Ejecutante"]
    # miercoles 23 dic de 21:00 a 02:00 del jueves 24 (feriado): noche y feriado
    inicio = datetime(2026, 12, 23, 21, tzinfo=LIMA)
    fin = datetime(2026, 12, 24, 2, tzinfo=LIMA)
    r = await cliente.post(  # sin token: es publica
        "/api/v1/simulaciones",
        json={
            "id_sala": _sala(sql),
            "id_servicio": voces["id"],
            "inicio": inicio.isoformat(),
            "fin": fin.isoformat(),
            "especialistas": [ejecutante["id"], voces["especialistas_por_defecto"][0]],
        },
    )
    assert r.status_code == 200
    esperado = _esperado(
        await _motor(
            cliente, "Grabación de voces", [ejecutante["id"]], inicio.isoformat(), fin.isoformat()
        )
    )
    assert r.json() == esperado
    assert {x["tipo"] for x in r.json()["recargos"]} == {"noche", "feriado"}


async def test_la_simulacion_con_montos_fijados_da_el_total_esperado(
    cliente: AsyncClient, administrador: Cabeceras, sql: Sql
) -> None:
    servicios, especialistas = await _servicios(cliente), await _especialistas(cliente)
    ensayo, ing = servicios["Ensayo"], especialistas["Ingeniero de sonido"]
    await cliente.patch(
        f"/api/v1/servicios/{ensayo['id']}",
        headers=administrador,
        json={"tarifa_hora": "40", "monto_fijo": "10", "especialistas_por_defecto": [ing["id"]]},
    )
    r = await cliente.post(
        "/api/v1/simulaciones",
        json={
            "id_sala": _sala(sql),
            "id_servicio": ensayo["id"],
            **_tramo(16, 10, 12),
            "especialistas": [],
        },
    )  # miercoles 16 dic, de dia: 2 h x 40 + 10 fijo + 4 lapsos x 25 + 30 fijo de ingeniero
    assert r.status_code == 200
    assert r.json()["total"] == "220.00" and r.json()["anticipo"] == "110.00"
    assert r.json()["recargos"] == []


async def test_la_simulacion_no_crea_ni_modifica_nada(cliente: AsyncClient, sql: Sql) -> None:
    tablas = ("servicio", "especialista", "feriado", "recargo", "usuario")
    antes = [sql(f"select count(*) from public.{t}") for t in tablas]
    voces = (await _servicios(cliente))["Grabación de voces"]
    cuerpo = {
        "id_sala": _sala(sql),
        "id_servicio": voces["id"],
        **_tramo(16, 10, 11),
        "especialistas": [],
    }
    for _ in range(2):
        assert (await cliente.post("/api/v1/simulaciones", json=cuerpo)).status_code == 200
    assert [sql(f"select count(*) from public.{t}") for t in tablas] == antes


async def test_simulacion_de_posproduccion_es_422_servicio_no_reservable(
    cliente: AsyncClient, sql: Sql
) -> None:
    mezcla = (await _servicios(cliente))["Mezcla"]
    r = await cliente.post(
        "/api/v1/simulaciones",
        json={
            "id_sala": _sala(sql),
            "id_servicio": mezcla["id"],
            **_tramo(16, 10, 11),
            "especialistas": [],
        },
    )
    assert r.status_code == 422 and r.json()["error"]["codigo"] == "servicio_no_reservable"


async def test_simulacion_de_servicio_inactivo_es_422_servicio_no_reservable(
    cliente: AsyncClient, administrador: Cabeceras, sql: Sql
) -> None:
    voces = (await _servicios(cliente))["Grabación de voces"]
    await cliente.patch(
        f"/api/v1/servicios/{voces['id']}", headers=administrador, json={"activo": False}
    )
    r = await cliente.post(
        "/api/v1/simulaciones",
        json={
            "id_sala": _sala(sql),
            "id_servicio": voces["id"],
            **_tramo(16, 10, 11),
            "especialistas": [],
        },
    )
    assert r.status_code == 422 and r.json()["error"]["codigo"] == "servicio_no_reservable"


@pytest.mark.parametrize(
    ("inicio", "fin"),
    [
        ("2026-12-16T10:15:00-05:00", "2026-12-16T11:15:00-05:00"),
        ("2026-12-16T10:00:00-05:00", "2026-12-16T10:45:00-05:00"),
        ("2026-12-16T11:00:00-05:00", "2026-12-16T10:00:00-05:00"),
        ("2026-12-16T10:00:00-05:00", "2026-12-16T10:00:00-05:00"),
        ("2026-12-16T10:00:00-05:00", "2026-12-16T18:30:00-05:00"),
    ],
)
async def test_tramo_invalido_es_422(cliente: AsyncClient, sql: Sql, inicio: str, fin: str) -> None:
    voces = (await _servicios(cliente))["Grabación de voces"]
    r = await cliente.post(
        "/api/v1/simulaciones",
        json={
            "id_sala": _sala(sql),
            "id_servicio": voces["id"],
            "inicio": inicio,
            "fin": fin,
            "especialistas": [],
        },
    )
    assert r.status_code == 422 and r.json()["error"]["codigo"] == "tramo_invalido"


async def test_simulacion_con_referencias_inexistentes_es_422(
    cliente: AsyncClient, administrador: Cabeceras, sql: Sql
) -> None:
    servicios, especialistas = await _servicios(cliente), await _especialistas(cliente)
    voces, ejecutante = servicios["Grabación de voces"], especialistas["Ejecutante"]
    base = {
        "id_sala": _sala(sql),
        "id_servicio": voces["id"],
        **_tramo(16, 10, 11),
        "especialistas": [],
    }
    await cliente.patch(
        f"/api/v1/especialistas/{ejecutante['id']}", headers=administrador, json={"activo": False}
    )
    for cambios in (
        {"id_sala": str(uuid4())},
        {"id_servicio": str(uuid4())},
        {"especialistas": [str(uuid4())]},
        {"especialistas": [ejecutante["id"]]},  # inactivo
    ):
        r = await cliente.post("/api/v1/simulaciones", json={**base, **cambios})
        assert r.status_code == 422 and r.json()["error"]["codigo"] == "datos_invalidos", cambios


async def test_simulacion_con_cuerpo_invalido_es_422_datos_invalidos(
    cliente: AsyncClient, sql: Sql
) -> None:
    voces = (await _servicios(cliente))["Grabación de voces"]
    base = {
        "id_sala": _sala(sql),
        "id_servicio": voces["id"],
        **_tramo(16, 10, 11),
        "especialistas": [],
    }
    for cambios in (
        {"id_sala": "no-uuid"},
        {"inicio": "2026-12-16T10:00:00"},  # sin zona horaria
        {"fin": "manana"},
        {"especialistas": "todos"},
        {"especialistas": ["no-uuid"]},
        {"precio": "1.00"},
        {"especialistas": [str(uuid4())] * 21},
    ):
        r = await cliente.post("/api/v1/simulaciones", json={**base, **cambios})
        assert r.status_code == 422 and r.json()["error"]["codigo"] == "datos_invalidos", cambios
    faltante = {k: v for k, v in base.items() if k != "inicio"}
    assert (await cliente.post("/api/v1/simulaciones", json=faltante)).status_code == 422


# --- OpenAPI -------------------------------------------------------------------------------------

CONTRATO = {
    ("get", "/api/v1/servicios"): {503},
    ("patch", "/api/v1/servicios/{id_servicio}"): {401, 403, 404, 422, 503},
    ("get", "/api/v1/especialistas"): {503},
    ("patch", "/api/v1/especialistas/{id_especialista}"): {401, 403, 404, 422, 503},
    ("get", "/api/v1/recargos"): {503},
    ("put", "/api/v1/recargos"): {401, 403, 422, 503},
    ("get", "/api/v1/feriados"): {422, 503},
    ("post", "/api/v1/feriados"): {401, 403, 409, 422, 503},
    ("delete", "/api/v1/feriados/{fecha}"): {401, 403, 404, 422, 503},
    ("post", "/api/v1/simulaciones"): {422, 503},
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
    assert rutas["/api/v1/feriados/{fecha}"]["delete"]["responses"]["204"]
    assert rutas["/api/v1/feriados"]["post"]["responses"]["201"]


async def test_dos_patch_concurrentes_de_especialistas_dan_200_y_una_lista_entera(
    cliente: AsyncClient, administrador: Cabeceras, sql: Sql
) -> None:
    import asyncio

    voces = (await _servicios(cliente))["Grabación de voces"]
    e = [x["id"] for x in (await _especialistas(cliente)).values()]
    listas = ([e[0], e[1]], [e[1], e[2]])
    url = f"/api/v1/servicios/{voces['id']}"
    for _ in range(15):
        rs = await asyncio.gather(
            *(
                cliente.patch(url, headers=administrador, json={"especialistas_por_defecto": ids})
                for ids in listas
            )
        )
        assert [r.status_code for r in rs] == [200, 200]
        final = sorted(
            str(f[0])
            for f in sql(
                "select id_especialista from public.servicio_especialista where id_servicio = %s",
                voces["id"],
            )
        )
        assert final in (sorted(listas[0]), sorted(listas[1]))
