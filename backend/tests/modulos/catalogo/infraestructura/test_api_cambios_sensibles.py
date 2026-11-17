"""RF-20 (2/2): barreras, vista previa, confirmacion y registro de cambios (stack local, RLS)."""

import asyncio
from collections.abc import Callable, Iterator
from typing import Any

import pytest
from httpx import AsyncClient, Response

from tests.conftest import UsuarioDePrueba

pytestmark = pytest.mark.integracion

Sql = Callable[..., list[tuple[Any, ...]]]
Cabeceras = dict[str, str]
PREV, CONF, REGISTRO = (
    "/api/v1/cambios-sensibles/previsualizar",
    "/api/v1/cambios-sensibles/confirmar",
    "/api/v1/registro-cambios",
)
CUENTA_TARIFA = (
    "select count(*) from public.registro_cambio where id_recurso = %s and campo = 'tarifa_hora'"
)
PARAMETROS_INICIALES = {
    "porcentaje_adelanto": 50, "horas_nivel_1": 48, "horas_nivel_2": 24,
    "porcentaje_penalizacion_nivel_2": 25, "minutos_tolerancia_inasistencia": 15,
    "dias_vigencia_credito": 30, "reprogramaciones_nivel_1": 2, "reprogramaciones_nivel_2": 1,
    "horas_limite_pago": 1, "anticipacion_minima_horas": 24,
}  # fmt: skip


@pytest.fixture(autouse=True)
def configuracion_intacta(sql: Sql) -> Iterator[None]:
    anteriores = sql("select clave, valor from public.parametro")
    yield
    sql(
        "update public.configuracion_impuestos set porcentaje_igv = 18.00, "
        "precios_incluyen_igv = true"
    )
    for clave, valor in anteriores:
        sql("update public.parametro set valor = %s where clave = %s", valor, clave)


@pytest.fixture
def otro_administrador(
    crear_usuario: Callable[[], UsuarioDePrueba],
    poner_rol: Callable[[UsuarioDePrueba, str, str | None], None],
) -> Cabeceras:
    u = crear_usuario()
    poner_rol(u, "administrador", None)
    return {"Authorization": f"Bearer {u.token}"}


async def _id(cliente: AsyncClient, ruta: str, nombre: str) -> str:
    return str(next(x["id"] for x in (await cliente.get(ruta)).json() if x["nombre"] == nombre))


async def _previsualizar(
    cliente: AsyncClient,
    cab: Cabeceras,
    recurso: str,
    cambios: dict[str, Any],
    id_recurso: str | None = None,
) -> Response:
    cuerpo: dict[str, Any] = {"recurso": recurso, "cambios": cambios}
    if id_recurso:
        cuerpo["id_recurso"] = id_recurso
    return await cliente.post(PREV, headers=cab, json=cuerpo)


async def _confirmar(
    cliente: AsyncClient, cab: Cabeceras, token: str, palabra: str = "CONFIRMAR"
) -> Response:
    return await cliente.post(CONF, headers=cab, json={"token": token, "palabra": palabra})


async def _cambiar(
    cliente: AsyncClient,
    cab: Cabeceras,
    recurso: str,
    cambios: dict[str, Any],
    id_recurso: str | None = None,
) -> Response:
    p = await _previsualizar(cliente, cab, recurso, cambios, id_recurso)
    assert p.status_code == 200, p.text
    return await _confirmar(cliente, cab, p.json()["token"])


def _codigo(r: Response) -> tuple[int, str]:
    return r.status_code, r.json()["error"]["codigo"]


# --- 428 en los endpoints de siempre ---------------------------------------------------------


async def test_cambiar_una_tarifa_exige_confirmacion_y_no_aplica_nada(
    cliente: AsyncClient, administrador: Cabeceras, sql: Sql
) -> None:
    voces = await _id(cliente, "/api/v1/servicios", "Grabación de voces")
    r = await cliente.patch(
        f"/api/v1/servicios/{voces}",
        headers=administrador,
        json={"tarifa_hora": "99", "activo": False},
    )
    assert _codigo(r) == (428, "confirmacion_requerida")
    assert r.json()["error"]["detalles"] == {"campos": ["tarifa_hora"]}
    assert sql("select tarifa_hora, activo from public.servicio where id = %s", voces) == [
        (80, True)
    ]


async def test_mismo_valor_o_campo_no_sensible_sigue_en_un_paso(
    cliente: AsyncClient, administrador: Cabeceras
) -> None:
    voces = await _id(cliente, "/api/v1/servicios", "Grabación de voces")
    r = await cliente.patch(
        f"/api/v1/servicios/{voces}",
        headers=administrador,
        json={"tarifa_hora": "80.00", "activo": False},
    )
    assert r.status_code == 200 and r.json()["activo"] is False
    r = await cliente.patch(
        "/api/v1/parametros", headers=administrador, json={"anticipacion_minima_horas": 3}
    )
    assert r.status_code == 200
    r = await cliente.patch(
        "/api/v1/parametros", headers=administrador, json={"porcentaje_adelanto": 50}
    )
    assert r.status_code == 200


async def test_especialista_recargos_y_parametros_exigen_confirmacion(
    cliente: AsyncClient, administrador: Cabeceras
) -> None:
    ing = await _id(cliente, "/api/v1/especialistas", "Ingeniero de sonido")
    r = await cliente.patch(
        f"/api/v1/especialistas/{ing}", headers=administrador, json={"unidad": "hora"}
    )
    assert r.status_code == 428 and r.json()["error"]["detalles"] == {"campos": ["unidad"]}
    recargos = (await cliente.get("/api/v1/recargos")).json()
    recargos["feriado"]["porcentaje"] = "99.00"
    r = await cliente.put("/api/v1/recargos", headers=administrador, json=recargos)
    assert r.status_code == 428
    assert r.json()["error"]["detalles"] == {"campos": ["feriado.porcentaje"]}
    r = await cliente.patch(
        "/api/v1/parametros", headers=administrador, json={"porcentaje_adelanto": 40}
    )
    assert r.status_code == 428
    assert r.json()["error"]["detalles"] == {"campos": ["porcentaje_adelanto"]}
    r = await cliente.get("/api/v1/parametros", headers=administrador)
    assert r.json()["porcentaje_adelanto"] == 50 and r.json()["horas_nivel_1"] == 48
    assert len(r.json()) == 12


async def test_parametros_incoherentes_son_422_tambien_en_el_endpoint_de_siempre(
    cliente: AsyncClient, administrador: Cabeceras
) -> None:
    r = await cliente.patch("/api/v1/parametros", headers=administrador, json={"horas_nivel_2": 60})
    assert _codigo(r) == (422, "plazos_incoherentes")


# --- vista previa -----------------------------------------------------------------------------


async def test_previsualizar_un_servicio_devuelve_antes_despues_impacto_y_token(
    cliente: AsyncClient, administrador: Cabeceras, sql: Sql
) -> None:
    voces = await _id(cliente, "/api/v1/servicios", "Grabación de voces")
    r = await _previsualizar(cliente, administrador, "servicio", {"tarifa_hora": "100"}, voces)
    assert r.status_code == 200, r.text
    p = r.json()
    assert p["palabra"] == "CONFIRMAR" and len(p["token"]) >= 32 and p["expira_en"]
    assert (p["recurso"], p["id_recurso"]) == ("servicio", voces)
    assert p["nombre_recurso"] == "Grabación de voces"
    assert p["cambios"] == [{"campo": "tarifa_hora", "anterior": "80.00", "nuevo": "100.00"}]
    ejemplo = p["impacto"]["ejemplos"][0]
    assert ejemplo["tipo"] == "importe" and ejemplo["antes"] != ejemplo["despues"]
    assert p["impacto"]["operaciones_vigentes"] >= 0
    # No cambia nada y el token no se guarda en claro.
    assert sql("select tarifa_hora from public.servicio where id = %s", voces) == [(80,)]
    guardado = sql(
        "select count(*) from public.confirmacion_cambio where hash_token = %s", p["token"]
    )
    assert guardado == [(0,)]


@pytest.mark.parametrize(
    ("recurso", "cambios", "con_id", "estado", "codigo"),
    [
        ("servicio", {"tarifa_hora": "80"}, True, 422, "sin_cambios"),
        ("servicio", {"activo": False}, True, 422, "datos_invalidos"),
        ("servicio", {"tarifa_hora": "-1"}, True, 422, "datos_invalidos"),
        ("servicio", {"tarifa_hora": "90"}, False, 422, "datos_invalidos"),
        ("impuestos", {"porcentaje_igv": "100"}, False, 422, "datos_invalidos"),
        ("impuestos", {}, False, 422, "sin_cambios"),
        ("parametros", {"horas_nivel_1": 24}, False, 422, "plazos_incoherentes"),
        ("parametros", {"anticipacion_minima_horas": 3}, False, 422, "datos_invalidos"),
        ("parametros", {"porcentaje_adelanto": 101}, False, 422, "datos_invalidos"),
        ("inventado", {"a": 1}, False, 422, "datos_invalidos"),
    ],
)
async def test_previsualizar_rechaza_lo_invalido(
    cliente: AsyncClient, administrador: Cabeceras,
    recurso: str, cambios: dict[str, Any], con_id: bool, estado: int, codigo: str,
) -> None:  # fmt: skip
    id_recurso = await _id(cliente, "/api/v1/servicios", "Grabación de voces") if con_id else None
    r = await _previsualizar(cliente, administrador, recurso, cambios, id_recurso)
    assert _codigo(r) == (estado, codigo)


async def test_previsualizar_servicio_inexistente_es_404(
    cliente: AsyncClient, administrador: Cabeceras
) -> None:
    r = await _previsualizar(
        cliente,
        administrador,
        "servicio",
        {"tarifa_hora": "9"},
        "00000000-0000-0000-0000-000000000001",
    )
    assert r.status_code == 404


async def test_previsualizar_cada_recurso_trae_ejemplos(
    cliente: AsyncClient, administrador: Cabeceras
) -> None:
    ing = await _id(cliente, "/api/v1/especialistas", "Ingeniero de sonido")
    recargos = (await cliente.get("/api/v1/recargos")).json()
    recargos["noche"]["porcentaje"] = "50"
    recargos["noche"]["desde"] = "21:00"
    casos: list[tuple[str, dict[str, Any], str | None]] = [
        ("especialista", {"monto_variable": "60"}, ing),
        ("recargos", recargos, None),
        ("impuestos", {"porcentaje_igv": "10", "precios_incluyen_igv": False}, None),
        (
            "parametros",
            {"horas_limite_pago": 3, "porcentaje_adelanto": 40, "horas_nivel_2": 12},
            None,
        ),
        ("parametros", {"minutos_tolerancia_inasistencia": 20}, None),
    ]
    for recurso, cambios, id_recurso in casos:
        r = await _previsualizar(cliente, administrador, recurso, cambios, id_recurso)
        assert r.status_code == 200, (recurso, r.text)
        p = r.json()
        assert p["impacto"]["ejemplos"], recurso
        assert {e["tipo"] for e in p["impacto"]["ejemplos"]} <= {"importe", "fecha_hora", "texto"}
        if recurso == "recargos":
            assert [c["campo"] for c in p["cambios"]] == ["noche.porcentaje", "noche.desde"]


async def test_previsualizar_cuenta_las_operaciones_vigentes(
    cliente: AsyncClient, administrador: Cabeceras, sql: Sql
) -> None:
    p = (await _previsualizar(cliente, administrador, "impuestos", {"porcentaje_igv": "10"})).json()
    esperadas = sql(
        "select count(*) from public.reserva "
        "where estado in ('pre_reservada', 'confirmada') and inicio > now()"
    )[0][0]
    assert p["impacto"]["operaciones_vigentes"] == esperadas


# --- confirmacion -----------------------------------------------------------------------------


async def test_confirmar_aplica_el_cambio_y_registra_cada_campo(
    cliente: AsyncClient, administrador: Cabeceras, sql: Sql
) -> None:
    voces = await _id(cliente, "/api/v1/servicios", "Grabación de voces")
    r = await _cambiar(
        cliente, administrador, "servicio", {"tarifa_hora": "100", "monto_fijo": "5"}, voces
    )
    assert r.status_code == 200, r.text
    cuerpo = r.json()
    assert (cuerpo["recurso"], cuerpo["id_recurso"]) == ("servicio", voces)
    assert cuerpo["valor"]["tarifa_hora"] == "100.00" and cuerpo["valor"]["monto_fijo"] == "5.00"
    registrados = {c["campo"]: (c["anterior"], c["nuevo"]) for c in cuerpo["cambios"]}
    assert registrados == {"tarifa_hora": ("80.00", "100.00"), "monto_fijo": ("0.00", "5.00")}
    assert cuerpo["cambios"][0]["autor"]["id"]
    assert cuerpo["cambios"][0]["nombre_recurso"] == "Grabación de voces"
    assert sql("select tarifa_hora, monto_fijo from public.servicio where id = %s", voces) == [
        (100, 5)
    ]


async def test_confirmar_impuestos_recargos_especialista_y_parametros(
    cliente: AsyncClient, administrador: Cabeceras
) -> None:
    r = await _cambiar(
        cliente,
        administrador,
        "impuestos",
        {"porcentaje_igv": "10.5", "precios_incluyen_igv": False},
    )
    assert r.status_code == 200
    assert r.json()["valor"] == {"porcentaje_igv": "10.50", "precios_incluyen_igv": False}
    assert (await cliente.get("/api/v1/impuestos")).json()["porcentaje_igv"] == "10.50"

    recargos = (await cliente.get("/api/v1/recargos")).json()
    recargos["noche"] = {"porcentaje": "40", "desde": "21:30", "hasta": "05:00"}
    r = await _cambiar(cliente, administrador, "recargos", recargos)
    assert r.status_code == 200
    assert r.json()["valor"]["noche"] == {"porcentaje": "40.00", "desde": "21:30", "hasta": "05:00"}

    ing = await _id(cliente, "/api/v1/especialistas", "Ingeniero de sonido")
    r = await _cambiar(
        cliente, administrador, "especialista", {"unidad": "hora", "monto_variable": "70"}, ing
    )
    assert r.status_code == 200 and r.json()["valor"]["unidad"] == "hora"

    r = await _cambiar(
        cliente, administrador, "parametros", {"porcentaje_adelanto": 30, "horas_nivel_1": 72}
    )
    assert r.status_code == 200, r.text
    assert r.json()["valor"]["porcentaje_adelanto"] == 30
    assert (await cliente.get("/api/v1/parametros", headers=administrador)).json()[
        "horas_nivel_1"
    ] == 72


async def test_palabra_incorrecta_es_422_y_el_token_sigue_vigente(
    cliente: AsyncClient, administrador: Cabeceras, sql: Sql
) -> None:
    p = (await _previsualizar(cliente, administrador, "impuestos", {"porcentaje_igv": "9"})).json()
    malas = ("confirmar", "CONFIRMA", "", "CONFIRMAR\x00", "\x07CONFIRMAR", "CONFIRMAR‮", "x" * 5000)
    for palabra in malas:
        r = await _confirmar(cliente, administrador, p["token"], palabra)
        assert _codigo(r) == (422, "palabra_incorrecta"), palabra
    assert sql("select porcentaje_igv from public.configuracion_impuestos") == [(18,)]
    r = await _confirmar(cliente, administrador, p["token"], "  CONFIRMAR  ")
    assert r.status_code == 200, r.text


async def test_un_token_se_usa_una_vez(cliente: AsyncClient, administrador: Cabeceras) -> None:
    p = (await _previsualizar(cliente, administrador, "impuestos", {"porcentaje_igv": "9"})).json()
    assert (await _confirmar(cliente, administrador, p["token"])).status_code == 200
    r = await _confirmar(cliente, administrador, p["token"])
    assert _codigo(r) == (409, "confirmacion_no_valida")


async def test_token_vencido_o_inexistente_es_409(
    cliente: AsyncClient, administrador: Cabeceras, sql: Sql
) -> None:
    p = (await _previsualizar(cliente, administrador, "impuestos", {"porcentaje_igv": "9"})).json()
    sql(
        "update public.confirmacion_cambio set creada_en = now() - interval '20 minutes', "
        "expira_en = now() - interval '10 minutes' where usada_en is null and expira_en > now()"
    )
    for token in (p["token"], "no-existe", "\x00"):
        r = await _confirmar(cliente, administrador, token)
        assert _codigo(r) == (409, "confirmacion_no_valida"), token
    assert sql("select porcentaje_igv from public.configuracion_impuestos") == [(18,)]


async def test_token_de_otro_administrador_es_403(
    cliente: AsyncClient, administrador: Cabeceras, otro_administrador: Cabeceras, sql: Sql
) -> None:
    p = (await _previsualizar(cliente, administrador, "impuestos", {"porcentaje_igv": "9"})).json()
    r = await _confirmar(cliente, otro_administrador, p["token"])
    assert r.status_code == 403
    assert sql("select porcentaje_igv from public.configuracion_impuestos") == [(18,)]
    assert (await _confirmar(cliente, administrador, p["token"])).status_code == 200


async def test_si_otro_cambio_gano_es_cambio_desactualizado(
    cliente: AsyncClient, administrador: Cabeceras, otro_administrador: Cabeceras, sql: Sql
) -> None:
    a = (await _previsualizar(cliente, administrador, "impuestos", {"porcentaje_igv": "9"})).json()
    b = (
        await _previsualizar(cliente, otro_administrador, "impuestos", {"porcentaje_igv": "7"})
    ).json()
    assert (await _confirmar(cliente, administrador, a["token"])).status_code == 200
    r = await _confirmar(cliente, otro_administrador, b["token"])
    assert _codigo(r) == (409, "cambio_desactualizado")
    assert sql("select porcentaje_igv from public.configuracion_impuestos") == [(9,)]


async def test_dos_confirmaciones_a_la_vez_una_gana_y_la_otra_es_desactualizada(
    cliente: AsyncClient, administrador: Cabeceras, otro_administrador: Cabeceras, sql: Sql
) -> None:
    voces = await _id(cliente, "/api/v1/servicios", "Grabación de voces")
    a = (
        await _previsualizar(cliente, administrador, "servicio", {"tarifa_hora": "91"}, voces)
    ).json()
    b = (
        await _previsualizar(cliente, otro_administrador, "servicio", {"tarifa_hora": "92"}, voces)
    ).json()
    antes = sql(
        CUENTA_TARIFA,
        voces,
    )[0][0]
    ra, rb = await asyncio.gather(
        _confirmar(cliente, administrador, a["token"]),
        _confirmar(cliente, otro_administrador, b["token"]),
    )
    assert sorted([ra.status_code, rb.status_code]) == [200, 409]
    perdedora = ra if ra.status_code == 409 else rb
    assert perdedora.json()["error"]["codigo"] == "cambio_desactualizado"
    ganadora = "91.00" if ra.status_code == 200 else "92.00"
    assert sql("select tarifa_hora::text from public.servicio where id = %s", voces) == [
        (ganadora,)
    ]
    assert (
        sql(CUENTA_TARIFA, voces)[0][0] - antes == 1
    )  # el registro no se borra: se cuenta lo nuevo


async def test_cliente_o_personal_no_previsualizan_ni_confirman_y_la_fila_queda_intacta(
    cliente: AsyncClient, administrador: Cabeceras, cliente_sin_rol: Cabeceras,
    crear_usuario: Callable[[], UsuarioDePrueba],
    poner_rol: Callable[[UsuarioDePrueba, str, str | None], None], sql: Sql,
) -> None:  # fmt: skip
    personal = crear_usuario()
    poner_rol(personal, "personal", "ingenieria")
    cab_personal = {"Authorization": f"Bearer {personal.token}"}
    p = (await _previsualizar(cliente, administrador, "impuestos", {"porcentaje_igv": "9"})).json()
    for cab in (cliente_sin_rol, cab_personal):
        r = await _previsualizar(cliente, cab, "impuestos", {"porcentaje_igv": "9"})
        assert r.status_code == 403
        assert (await _confirmar(cliente, cab, p["token"])).status_code == 403
        assert (await cliente.get(REGISTRO, headers=cab)).status_code == 403
    sin_sesion = (
        (PREV, {"recurso": "impuestos", "cambios": {}}),
        (CONF, {"token": "x", "palabra": "x"}),
    )
    for ruta, cuerpo in sin_sesion:
        assert (await cliente.post(ruta, json=cuerpo)).status_code == 401
    assert (await cliente.get(REGISTRO)).status_code == 401
    assert sql("select porcentaje_igv from public.configuracion_impuestos") == [(18,)]


async def test_el_cambio_no_altera_las_reservas_existentes(
    cliente: AsyncClient,
    administrador: Cabeceras,
    sql: Sql,
    crear_usuario: Callable[[], UsuarioDePrueba],
) -> None:
    dueno = crear_usuario()
    sala = sql("select id from public.sala_tecnica limit 1")[0][0]
    reserva = sql(
        "insert into public.reserva (id_cliente, id_sala, id_servicio, inicio, fin, total, precio) "
        "select %s, %s, se.id, date_trunc('day', now()) + interval '30 days 10 hours', "
        "date_trunc('day', now()) + interval '30 days 12 hours', 150, "
        "'{\"total\": \"150.00\"}'::jsonb from public.servicio se where se.nombre = 'Ensayo' "
        "returning id",
        dueno.id,
        sala,
    )[0][0]
    consulta = (
        "select total, precio, parametros_aplicados, vence_pago from public.reserva where id = %s"
    )
    antes = sql(consulta, reserva)
    for recurso, cambios in (
        ("impuestos", {"porcentaje_igv": "5", "precios_incluyen_igv": False}),
        ("parametros", {"porcentaje_adelanto": 20, "horas_limite_pago": 9}),
    ):
        assert (await _cambiar(cliente, administrador, recurso, cambios)).status_code == 200
    assert sql(consulta, reserva) == antes
    assert antes[0][2]["porcentaje_igv"] == "18.00" and antes[0][2]["porcentaje_adelanto"] == 50
    sql("delete from public.reserva where id = %s", reserva)


# --- registro de cambios ----------------------------------------------------------------------


async def test_registro_orden_descendente_filtros_y_rango(
    cliente: AsyncClient, administrador: Cabeceras
) -> None:
    for porcentaje in ("9", "8"):
        r = await _cambiar(cliente, administrador, "impuestos", {"porcentaje_igv": porcentaje})
        assert r.status_code == 200
    r = await cliente.get(REGISTRO, headers=administrador)
    assert r.status_code == 200
    filas = r.json()
    fechas = [f["cambiado_en"] for f in filas]
    assert filas and fechas == sorted(fechas, reverse=True)
    assert set(filas[0]) == {
        "id", "cambiado_en", "autor", "recurso", "id_recurso", "nombre_recurso",
        "campo", "anterior", "nuevo",
    }  # fmt: skip
    assert (filas[0]["recurso"], filas[0]["anterior"], filas[0]["nuevo"]) == (
        "impuestos", "9.00", "8.00",
    )  # fmt: skip
    solo = (
        await cliente.get(REGISTRO, headers=administrador, params={"recurso": "servicio"})
    ).json()
    assert all(f["recurso"] == "servicio" for f in solo)
    invertido = {"desde": "2026-12-10", "hasta": "2026-12-09"}
    r = await cliente.get(REGISTRO, headers=administrador, params=invertido)
    assert _codigo(r) == (422, "rango_invalido")
    largo = {"desde": "2025-01-01", "hasta": "2026-12-09"}
    r = await cliente.get(REGISTRO, headers=administrador, params=largo)
    assert _codigo(r) == (422, "rango_invalido")
    r = await cliente.get(REGISTRO, headers=administrador, params={"recurso": "x"})
    assert _codigo(r) == (422, "datos_invalidos")
    lejos = {"desde": "2020-01-01", "hasta": "2020-01-31"}
    r = await cliente.get(REGISTRO, headers=administrador, params=lejos)
    assert r.status_code == 200 and r.json() == []


async def test_el_registro_no_se_puede_alterar_por_la_api(
    cliente: AsyncClient, administrador: Cabeceras
) -> None:
    for metodo in ("put", "patch", "delete"):
        r = await getattr(cliente, metodo)(REGISTRO, headers=administrador)
        assert r.status_code == 405


def test_openapi_declara_los_errores_nuevos(app: Any) -> None:
    esquema = app.openapi()
    for ruta, metodo, codigos in (
        ("/api/v1/cambios-sensibles/previsualizar", "post", {"401", "403", "404", "422", "503"}),
        ("/api/v1/cambios-sensibles/confirmar", "post", {"401", "403", "409", "422", "503"}),
        ("/api/v1/registro-cambios", "get", {"401", "403", "422", "503"}),
        ("/api/v1/servicios/{id_servicio}", "patch", {"428"}),
        ("/api/v1/especialistas/{id_especialista}", "patch", {"428"}),
        ("/api/v1/recargos", "put", {"428"}),
        ("/api/v1/parametros", "patch", {"428"}),
    ):
        respuestas = esquema["paths"][ruta][metodo]["responses"]
        assert codigos <= set(respuestas), (ruta, set(respuestas))
        for c in codigos:
            assert "RespuestaError" in str(respuestas[c]), (ruta, c)
