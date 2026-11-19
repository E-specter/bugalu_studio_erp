"""RF-20 CA-11 a CA-13: parametros de danos (tarifa de gestion y tope de horas), sensibles."""

import base64
import json
import time
from collections.abc import Callable, Iterator
from typing import Any
from uuid import uuid4

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import ec
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient, Response

from bugalu.compartido.autenticacion import obtener_resolutor_clave
from bugalu.compartido.configuracion import Configuracion, obtener_configuracion
from bugalu.main import crear_app
from tests.conftest import UsuarioDePrueba

pytestmark = pytest.mark.integracion

Sql = Callable[..., list[tuple[Any, ...]]]
Cabeceras = dict[str, str]
DANOS, PARAMETROS = "/api/v1/parametros/danos", "/api/v1/parametros"
PREV, CONF, REGISTRO = (
    "/api/v1/cambios-sensibles/previsualizar",
    "/api/v1/cambios-sensibles/confirmar",
    "/api/v1/registro-cambios",
)
LEER = "select tarifa_hora_gestion::text from public.configuracion_danos"
CONFIRMACIONES = "select count(*) from public.confirmacion_cambio"
REGISTROS = "select count(*) from public.registro_cambio where recurso = 'parametros'"
TOPE = "select valor from public.parametro where clave = 'tope_horas_sesiones_perdidas'"


@pytest.fixture(autouse=True)
def danos_iniciales(sql: Sql) -> Iterator[None]:
    """Parte de la tarifa sin fijar y del tope 8; al final deja lo que habia."""
    tarifa, tope = sql(LEER)[0][0], sql(TOPE)[0][0]
    adelanto = sql("select valor from public.parametro where clave = 'porcentaje_adelanto'")[0][0]
    sql("update public.configuracion_danos set tarifa_hora_gestion = 0")
    sql("update public.parametro set valor = 8 where clave = 'tope_horas_sesiones_perdidas'")
    yield
    sql("update public.configuracion_danos set tarifa_hora_gestion = %s", tarifa)
    sql("update public.parametro set valor = %s where clave = 'tope_horas_sesiones_perdidas'", tope)
    sql("update public.parametro set valor = %s where clave = 'porcentaje_adelanto'", adelanto)


def _codigo(r: Response) -> tuple[int, str]:
    return r.status_code, r.json()["error"]["codigo"]


async def _cambiar(cliente: AsyncClient, cab: Cabeceras, cambios: dict[str, Any]) -> Response:
    p = await cliente.post(PREV, headers=cab, json={"recurso": "parametros", "cambios": cambios})
    assert p.status_code == 200, p.text
    return await cliente.post(
        CONF, headers=cab, json={"token": p.json()["token"], "palabra": "CONFIRMAR"}
    )


# --- lectura -------------------------------------------------------------------------------------


async def test_los_parametros_de_danos_son_publicos_con_la_tarifa_como_texto(
    cliente: AsyncClient, cliente_sin_rol: Cabeceras
) -> None:
    esperado = {"tarifa_hora_gestion": "0.00", "tope_horas_sesiones_perdidas": 8}
    assert (await cliente.get(DANOS)).json() == esperado  # visitante sin sesion
    r = await cliente.get(DANOS, headers=cliente_sin_rol)
    assert r.status_code == 200 and r.json() == esperado


async def test_el_administrador_ve_ambos_en_los_parametros(
    cliente: AsyncClient, administrador: Cabeceras
) -> None:
    r = await cliente.get(PARAMETROS, headers=administrador)
    assert r.json()["tarifa_hora_gestion"] == "0.00"
    assert r.json()["tope_horas_sesiones_perdidas"] == 8


# --- barrera: 428 sin aplicar nada ---------------------------------------------------------------


@pytest.mark.parametrize(
    ("cambio", "campo"),
    [
        ({"tarifa_hora_gestion": "25.50"}, "tarifa_hora_gestion"),
        ({"tarifa_hora_gestion": 25}, "tarifa_hora_gestion"),
        ({"tope_horas_sesiones_perdidas": 9}, "tope_horas_sesiones_perdidas"),
    ],
)
async def test_cambiar_un_parametro_de_danos_pide_confirmacion_y_no_aplica_nada(
    cliente: AsyncClient, administrador: Cabeceras, sql: Sql, cambio: dict[str, Any], campo: str
) -> None:
    minima = sql("select valor from public.parametro where clave = 'anticipacion_minima_horas'")
    r = await cliente.patch(
        PARAMETROS, headers=administrador, json={**cambio, "anticipacion_minima_horas": 77}
    )
    assert _codigo(r) == (428, "confirmacion_requerida")
    assert r.json()["error"]["detalles"] == {"campos": [campo]}
    assert sql(LEER) == [("0.00",)] and sql(TOPE) == [(8,)]
    assert (
        sql("select valor from public.parametro where clave = 'anticipacion_minima_horas'")
        == minima
    )


async def test_el_mismo_valor_sigue_en_un_paso_y_no_deja_registro(
    cliente: AsyncClient, administrador: Cabeceras, sql: Sql
) -> None:
    registros = sql(REGISTROS)
    r = await cliente.patch(
        PARAMETROS,
        headers=administrador,
        json={"tarifa_hora_gestion": "0.0", "tope_horas_sesiones_perdidas": 8},
    )
    assert r.status_code == 200, r.text
    assert (r.json()["tarifa_hora_gestion"], r.json()["tope_horas_sesiones_perdidas"]) == (
        "0.00",
        8,
    )
    assert sql(REGISTROS) == registros  # sin cambio de valor no hay registro


# --- 422 con su campo ----------------------------------------------------------------------------

INVALIDOS = [
    {"tarifa_hora_gestion": "10000"},
    {"tarifa_hora_gestion": "-0.01"},
    {"tarifa_hora_gestion": "1.234"},
    {"tarifa_hora_gestion": "abc"},
    {"tarifa_hora_gestion": "NaN"},
    {"tarifa_hora_gestion": True},
    {"tarifa_hora_gestion": [1]},
    {"tarifa_hora_gestion": None},
    {"tope_horas_sesiones_perdidas": 0},
    {"tope_horas_sesiones_perdidas": 201},
    {"tope_horas_sesiones_perdidas": "8"},
    {"tope_horas_sesiones_perdidas": 8.5},
    {"tope_horas_sesiones_perdidas": True},
    {"tope_horas_sesiones_perdidas": None},
]


@pytest.mark.parametrize("cuerpo", INVALIDOS)
async def test_valores_invalidos_de_danos_son_422_con_su_campo_en_patch_y_vista_previa(
    cliente: AsyncClient, administrador: Cabeceras, sql: Sql, cuerpo: dict[str, Any]
) -> None:
    campo = next(iter(cuerpo))
    r = await cliente.patch(PARAMETROS, headers=administrador, json=cuerpo)
    assert _codigo(r) == (422, "datos_invalidos")
    assert r.json()["error"]["detalles"]["campo"] == campo
    r = await cliente.post(
        PREV, headers=administrador, json={"recurso": "parametros", "cambios": cuerpo}
    )
    assert _codigo(r) == (422, "datos_invalidos")
    assert r.json()["error"]["detalles"]["campo"] == campo
    assert sql(LEER) == [("0.00",)] and sql(TOPE) == [(8,)]


# --- 401 y 403 -----------------------------------------------------------------------------------

ESCRITURAS = [
    ("patch", PARAMETROS, {"tarifa_hora_gestion": "25.00"}),
    ("post", PREV, {"recurso": "parametros", "cambios": {"tope_horas_sesiones_perdidas": 9}}),
]


async def _enviar(
    cliente: AsyncClient, metodo: str, ruta: str, token: str | None, cuerpo: Any
) -> Response:
    cabeceras = {"Authorization": f"Bearer {token}"} if token else {}
    return await cliente.request(metodo, ruta, headers=cabeceras, json=cuerpo)


@pytest.mark.parametrize(("metodo", "ruta", "cuerpo"), ESCRITURAS)
async def test_401_sin_token_con_alg_cambiado_o_caducado(
    app: FastAPI,
    cliente: AsyncClient,
    configuracion: Configuracion,
    crear_usuario: Callable[[], UsuarioDePrueba],
    sql: Sql,
    metodo: str,
    ruta: str,
    cuerpo: Any,
) -> None:
    assert (await _enviar(cliente, metodo, ruta, None, cuerpo)).status_code == 401
    cabecera, carga, firma = crear_usuario().token.split(".")
    datos = json.loads(base64.urlsafe_b64decode(cabecera + "=="))
    datos["alg"] = "HS256"
    falsa = base64.urlsafe_b64encode(json.dumps(datos).encode()).rstrip(b"=").decode()
    assert (
        await _enviar(cliente, metodo, ruta, f"{falsa}.{carga}.{firma}", cuerpo)
    ).status_code == 401
    clave = ec.generate_private_key(ec.SECP256R1())
    app.dependency_overrides[obtener_resolutor_clave] = lambda: lambda _t: clave.public_key()
    caducado = jwt.encode(
        {
            "sub": str(uuid4()),
            "aud": "authenticated",
            "iss": configuracion.emisor_jwt,
            "exp": time.time() - 60,
        },
        clave,
        algorithm="ES256",
    )
    assert (await _enviar(cliente, metodo, ruta, caducado, cuerpo)).status_code == 401
    assert sql(LEER) == [("0.00",)] and sql(TOPE) == [(8,)]


@pytest.mark.parametrize(("metodo", "ruta", "cuerpo"), ESCRITURAS)
async def test_403_un_cliente_no_cambia_ni_previsualiza_y_la_fila_queda_intacta(
    cliente: AsyncClient,
    crear_usuario: Callable[[], UsuarioDePrueba],
    sql: Sql,
    metodo: str,
    ruta: str,
    cuerpo: Any,
) -> None:
    confirmaciones = sql(CONFIRMACIONES)
    r = await _enviar(cliente, metodo, ruta, crear_usuario().token, cuerpo)
    assert _codigo(r) == (403, "sin_permiso")
    assert sql(LEER) == [("0.00",)] and sql(TOPE) == [(8,)]
    assert sql(CONFIRMACIONES) == confirmaciones  # ni una vista previa guardada


# --- vista previa, confirmacion y registro -------------------------------------------------------


async def test_vista_previa_y_confirmacion_aplican_y_dejan_registro(
    cliente: AsyncClient, administrador: Cabeceras, sql: Sql
) -> None:
    p = await cliente.post(
        PREV,
        headers=administrador,
        json={
            "recurso": "parametros",
            "cambios": {"tarifa_hora_gestion": "25.5", "tope_horas_sesiones_perdidas": 12},
        },
    )
    assert p.status_code == 200, p.text
    previa = p.json()
    assert previa["cambios"] == [
        {"campo": "tarifa_hora_gestion", "anterior": "0.00", "nuevo": "25.50"},
        {"campo": "tope_horas_sesiones_perdidas", "anterior": "8", "nuevo": "12"},
    ]
    ejemplos = {e["concepto"]: e for e in previa["impacto"]["ejemplos"]}
    assert ejemplos["Tarifa por hora de gestión"]["tipo"] == "importe"
    assert previa["impacto"]["operaciones_vigentes"] == 0  # no se guardan en las reservas
    assert sql(LEER) == [("0.00",)]  # la vista previa no cambia nada

    mala = await cliente.post(
        CONF, headers=administrador, json={"token": previa["token"], "palabra": "confirmar"}
    )
    assert _codigo(mala) == (422, "palabra_incorrecta")
    r = await cliente.post(
        CONF, headers=administrador, json={"token": previa["token"], "palabra": " CONFIRMAR "}
    )
    assert r.status_code == 200, r.text
    assert r.json()["valor"]["tarifa_hora_gestion"] == "25.50"
    assert r.json()["valor"]["tope_horas_sesiones_perdidas"] == 12
    assert [(c["campo"], c["anterior"], c["nuevo"]) for c in r.json()["cambios"]] == [
        ("tarifa_hora_gestion", "0.00", "25.50"),
        ("tope_horas_sesiones_perdidas", "8", "12"),
    ]
    assert (await cliente.get(DANOS)).json() == {
        "tarifa_hora_gestion": "25.50",
        "tope_horas_sesiones_perdidas": 12,
    }
    assert sql(LEER) == [("25.50",)] and sql(TOPE) == [(12,)]
    reusado = await cliente.post(
        CONF, headers=administrador, json={"token": previa["token"], "palabra": "CONFIRMAR"}
    )
    assert _codigo(reusado) == (409, "confirmacion_no_valida")
    registro = await cliente.get(REGISTRO, headers=administrador, params={"recurso": "parametros"})
    campos = [(c["campo"], c["anterior"], c["nuevo"]) for c in registro.json()[:2]]
    assert sorted(campos) == [
        ("tarifa_hora_gestion", "0.00", "25.50"),
        ("tope_horas_sesiones_perdidas", "8", "12"),
    ]


async def test_confirmar_con_el_valor_anterior_cambiado_es_409_y_no_aplica(
    cliente: AsyncClient, administrador: Cabeceras, sql: Sql
) -> None:
    p = await cliente.post(
        PREV,
        headers=administrador,
        json={"recurso": "parametros", "cambios": {"tarifa_hora_gestion": "30"}},
    )
    sql("update public.configuracion_danos set tarifa_hora_gestion = 11")
    r = await cliente.post(
        CONF, headers=administrador, json={"token": p.json()["token"], "palabra": "CONFIRMAR"}
    )
    assert _codigo(r) == (409, "cambio_desactualizado")
    assert sql(LEER) == [("11.00",)]


async def test_sin_cambios_en_danos_es_422_sin_cambios(
    cliente: AsyncClient, administrador: Cabeceras
) -> None:
    r = await cliente.post(
        PREV,
        headers=administrador,
        json={"recurso": "parametros", "cambios": {"tarifa_hora_gestion": "0"}},
    )
    assert _codigo(r) == (422, "sin_cambios")


async def test_la_tarifa_cambia_en_un_cambio_mixto_con_otro_parametro(
    cliente: AsyncClient, administrador: Cabeceras
) -> None:
    r = await _cambiar(
        cliente, administrador, {"tarifa_hora_gestion": "9999.99", "porcentaje_adelanto": 40}
    )
    assert r.status_code == 200, r.text
    assert r.json()["valor"]["tarifa_hora_gestion"] == "9999.99"
    assert r.json()["valor"]["porcentaje_adelanto"] == 40


# --- 503 y contrato ------------------------------------------------------------------------------


async def test_503_con_la_base_caida_nunca_500(
    monkeypatch: pytest.MonkeyPatch, crear_usuario: Callable[[], UsuarioDePrueba]
) -> None:
    usuario = crear_usuario()
    monkeypatch.setenv("URL_BASE_DATOS", "postgresql://u:p@127.0.0.1:1/db")
    monkeypatch.setenv("TIMEOUT_POOL_SEGUNDOS", "0.5")
    obtener_configuracion.cache_clear()
    app = crear_app()
    async with (
        app.router.lifespan_context(app),
        AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c,
    ):
        r = await c.get(DANOS)
        assert _codigo(r) == (503, "base_de_datos_no_disponible")
        r = await c.patch(
            PARAMETROS,
            headers={"Authorization": f"Bearer {usuario.token}"},
            json={"tarifa_hora_gestion": "25.00"},
        )
        assert _codigo(r) == (503, "base_de_datos_no_disponible")
    obtener_configuracion.cache_clear()


def test_openapi_declara_el_endpoint_publico_de_danos(app: FastAPI) -> None:
    respuestas = app.openapi()["paths"][DANOS]["get"]["responses"]
    assert {"200", "503"} <= set(respuestas)
    assert "RespuestaError" in str(respuestas["503"])
