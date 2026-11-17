"""RF-17 etapa A: textos legales versionados y aceptaciones (stack local, RLS real)."""

import asyncio
import base64
import json
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import uuid4

import psycopg
import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from bugalu.compartido.configuracion import Configuracion, obtener_configuracion
from bugalu.main import crear_app
from tests.conftest import UsuarioDePrueba

pytestmark = [pytest.mark.integracion, pytest.mark.usefixtures("textos_aislados")]

Cabeceras = dict[str, str]
Sql = Callable[..., list[tuple[Any, ...]]]
Crear = Callable[[], UsuarioDePrueba]
BASE = "/api/v1/textos-legales"
AVISOS = "select count(*) from public.notificacion where tipo = 'texto_legal_nuevo'"


def _con(usuario: UsuarioDePrueba) -> Cabeceras:
    return {"Authorization": f"Bearer {usuario.token}"}


@pytest.fixture
def sql(configuracion: Configuracion) -> Sql:
    def consultar(consulta: str, *parametros: Any) -> list[tuple[Any, ...]]:
        with psycopg.connect(configuracion.url_base_datos_admin) as c:
            cursor = c.execute(consulta, parametros)
            return cursor.fetchall() if cursor.description else []

    return consultar


@pytest.fixture
def administrador(
    crear_usuario: Crear, poner_rol: Callable[[UsuarioDePrueba, str, str | None], None]
) -> Cabeceras:
    u = crear_usuario()
    poner_rol(u, "administrador", None)
    return _con(u)


def _fecha(dias: int) -> str:
    return (datetime.now(UTC) + timedelta(days=dias, minutes=1)).isoformat()


async def _publicar(cliente: AsyncClient, cabeceras: Cabeceras, **cambios: Any) -> Any:
    cuerpo = {
        "tipo": "terminos_uso",
        "version": "1.0.0",
        "tipo_cambio": "mayor",
        "contenido": "# Términos\n\nTexto **completo**.",
        "resumenes": {"registro": "Resumen del registro"},
        **cambios,
    }
    return await cliente.post(BASE, headers=cabeceras, json=cuerpo)


def _filas(sql: Sql) -> list[tuple[Any, ...]]:
    return sql("select tipo, version, contenido from public.texto_legal order by 1, 2")


# --- publicar -------------------------------------------------------------------------------------


async def test_el_administrador_publica_la_primera_version_vigente_ya(
    cliente: AsyncClient, administrador: Cabeceras, sql: Sql
) -> None:
    r = await _publicar(cliente, administrador)
    assert r.status_code == 201, r.text
    cuerpo = r.json()
    assert cuerpo["tipo"] == "terminos_uso"
    assert cuerpo["version"] == "1.0.0"
    assert cuerpo["programada"] is False
    assert cuerpo["resumenes"] == {"registro": "Resumen del registro"}
    assert "<strong>completo</strong>" in cuerpo["contenido_html"]
    assert cuerpo["contenido"].startswith("# Términos")
    assert datetime.fromisoformat(cuerpo["publicado_en"]).tzinfo is not None
    assert [f[:2] for f in _filas(sql)] == [("terminos_uso", "1.0.0")]
    assert sql(AVISOS) == [(0,)]


async def test_una_mayor_se_programa_y_avisa_a_cada_cliente(
    cliente: AsyncClient, administrador: Cabeceras, crear_usuario: Crear, sql: Sql
) -> None:
    c = crear_usuario()
    await _publicar(cliente, administrador)
    r = await _publicar(
        cliente,
        administrador,
        version="2.0.0",
        vigente_desde=_fecha(16),
        resumen_cambios="Nuevos plazos",
    )
    assert r.status_code == 201, r.text
    assert r.json()["programada"] is True
    avisos = sql(
        "select destinatario, datos from public.notificacion where tipo = 'texto_legal_nuevo'"
    )
    clientes = sql(
        "select a.email from public.usuario u join auth.users a on a.id = u.id "
        "where u.rol = 'cliente'"
    )
    assert sorted(a[0] for a in avisos) == sorted(x[0] for x in clientes)
    assert c.correo in {a[0] for a in avisos}
    assert avisos[0][1]["version"] == "2.0.0" and avisos[0][1]["resumen_cambios"] == "Nuevos plazos"


async def test_una_menor_avisa_y_un_parche_rige_ya_sin_aviso(
    cliente: AsyncClient, administrador: Cabeceras, sql: Sql
) -> None:
    await _publicar(cliente, administrador)
    menor = await _publicar(
        cliente, administrador, version="1.1.0", tipo_cambio="menor", vigente_desde=_fecha(16)
    )
    assert menor.status_code == 201
    assert sql(AVISOS)[0][0] > 0
    await cliente.delete(f"{BASE}/terminos_uso/versiones/1.1.0", headers=administrador)
    assert sql(AVISOS) == [(0,)]
    parche = await _publicar(cliente, administrador, version="1.0.1", tipo_cambio="parche")
    assert parche.status_code == 201
    assert parche.json()["programada"] is False
    assert sql(AVISOS) == [(0,)]


@pytest.mark.parametrize(
    ("cambios", "codigo"),
    [
        ({"version": "1.0.0"}, "version_invalida"),
        ({"version": "0.9.0"}, "version_invalida"),
        ({"version": "1.1.0", "tipo_cambio": "mayor"}, "version_invalida"),
        ({"version": "2.0.0", "vigente_desde": None}, "aviso_insuficiente"),
        ({"version": "2.0.0", "vigente_desde": "en 14 dias"}, "aviso_insuficiente"),
    ],
)
async def test_422_de_publicacion_y_la_base_queda_intacta(
    cliente: AsyncClient,
    administrador: Cabeceras,
    sql: Sql,
    cambios: dict[str, Any],
    codigo: str,
) -> None:
    await _publicar(cliente, administrador)
    antes = _filas(sql)
    if cambios.get("vigente_desde") == "en 14 dias":
        cambios = {**cambios, "vigente_desde": _fecha(14)}
    r = await _publicar(cliente, administrador, **cambios)
    assert (r.status_code, r.json()["error"]["codigo"]) == (422, codigo)
    assert _filas(sql) == antes


@pytest.mark.parametrize("version", ["1.0.3000000000", "3000000000.0.0", "1.0.1000000000"])
async def test_una_parte_de_la_version_con_mas_de_nueve_cifras_es_422_y_no_rompe_las_lecturas(
    cliente: AsyncClient, administrador: Cabeceras, sql: Sql, version: str
) -> None:
    r = await _publicar(cliente, administrador, version=version, tipo_cambio="parche")
    assert (r.status_code, r.json()["error"]["codigo"]) == (422, "version_invalida")
    assert _filas(sql) == []
    assert (await cliente.get(BASE)).status_code == 200


@pytest.mark.parametrize(
    "cambios",
    [
        {"tipo": "autorizacion_menor"},
        {"tipo": "otro"},
        {"tipo_cambio": "enorme"},
        {"contenido": ""},
        {"contenido": "hola\x00mundo"},
        {"resumenes": {"inventado": "x"}},
        {"vigente_desde": "2027-01-01T00:00:00"},  # sin zona
        {"version": "1" * 50},
    ],
)
async def test_422_datos_invalidos_nunca_500(
    cliente: AsyncClient, administrador: Cabeceras, sql: Sql, cambios: dict[str, Any]
) -> None:
    r = await _publicar(cliente, administrador, **cambios)
    assert r.status_code == 422, r.text
    assert r.json()["error"]["codigo"] in ("datos_invalidos", "version_invalida")
    assert _filas(sql) == []


async def test_409_si_ya_hay_una_programada(
    cliente: AsyncClient, administrador: Cabeceras, sql: Sql
) -> None:
    await _publicar(cliente, administrador)
    await _publicar(cliente, administrador, version="2.0.0", vigente_desde=_fecha(16))
    r = await _publicar(
        cliente, administrador, version="2.1.0", tipo_cambio="menor", vigente_desde=_fecha(16)
    )
    assert (r.status_code, r.json()["error"]["codigo"]) == (409, "version_programada")
    assert len(_filas(sql)) == 2


async def test_publicar_exige_sesion_y_rol_administrador(
    cliente: AsyncClient, crear_usuario: Crear, sql: Sql
) -> None:
    sin = await _publicar(cliente, {})
    assert (sin.status_code, sin.json()["error"]["codigo"]) == (401, "no_autenticado")
    r = await _publicar(cliente, _con(crear_usuario()))
    assert (r.status_code, r.json()["error"]["codigo"]) == (403, "sin_permiso")
    assert _filas(sql) == []


async def test_dos_publicaciones_simultaneas_dejan_una_sola_programada(
    cliente: AsyncClient, administrador: Cabeceras, sql: Sql
) -> None:
    await _publicar(cliente, administrador)
    rs = await asyncio.gather(
        _publicar(cliente, administrador, version="2.0.0", vigente_desde=_fecha(16)),
        _publicar(
            cliente, administrador, version="2.1.0", tipo_cambio="menor", vigente_desde=_fecha(16)
        ),
    )
    # el orden de llegada decide: 2.1.0 tras 2.0.0 choca con la programada (409); al reves es 422
    assert sorted(r.status_code for r in rs) in ([201, 409], [201, 422])
    assert len(_filas(sql)) == 2


# --- retirar --------------------------------------------------------------------------------------


async def test_retirar_una_programada_borra_la_fila_y_su_aviso(
    cliente: AsyncClient, administrador: Cabeceras, sql: Sql
) -> None:
    await _publicar(cliente, administrador)
    await _publicar(cliente, administrador, version="2.0.0", vigente_desde=_fecha(16))
    r = await cliente.delete(f"{BASE}/terminos_uso/versiones/2.0.0", headers=administrador)
    assert r.status_code == 204 and r.content == b""
    assert [f[:2] for f in _filas(sql)] == [("terminos_uso", "1.0.0")]
    assert sql(AVISOS) == [(0,)]


async def test_retirar_la_vigente_da_409_y_la_fila_queda(
    cliente: AsyncClient, administrador: Cabeceras, sql: Sql
) -> None:
    await _publicar(cliente, administrador)
    r = await cliente.delete(f"{BASE}/terminos_uso/versiones/1.0.0", headers=administrador)
    assert (r.status_code, r.json()["error"]["codigo"]) == (409, "version_vigente")
    assert len(_filas(sql)) == 1


async def test_retirar_inexistente_da_404_y_sin_rol_403_con_la_fila_intacta(
    cliente: AsyncClient, administrador: Cabeceras, crear_usuario: Crear, sql: Sql
) -> None:
    await _publicar(cliente, administrador)
    await _publicar(cliente, administrador, version="2.0.0", vigente_desde=_fecha(16))
    ruta = f"{BASE}/terminos_uso/versiones"
    assert (await cliente.delete(f"{ruta}/9.9.9", headers=administrador)).status_code == 404
    assert (await cliente.delete(f"{ruta}/otro", headers=administrador)).status_code == 404
    assert (await cliente.delete(f"{ruta}/2.0.0", headers=_con(crear_usuario()))).status_code == 403
    assert (await cliente.delete(f"{ruta}/2.0.0")).status_code == 401
    assert len(_filas(sql)) == 2


# --- lectura publica ------------------------------------------------------------------------------


async def test_get_textos_es_publico_y_lista_vigentes_y_programados(
    cliente: AsyncClient, administrador: Cabeceras
) -> None:
    await _publicar(cliente, administrador)
    await _publicar(cliente, administrador, version="2.0.0", vigente_desde=_fecha(16))
    await _publicar(cliente, administrador, tipo="politica_privacidad")
    await _publicar(
        cliente, administrador, tipo="politica_privacidad", version="1.0.1", tipo_cambio="parche"
    )
    r = await cliente.get(BASE, headers={"Authorization": "Bearer basura"})
    assert r.status_code == 200
    filas = [(t["tipo"], t["version"], t["programada"]) for t in r.json()]
    assert filas == [
        ("politica_privacidad", "1.0.1", False),  # la 1.0.0 quedo superada: no se lista
        ("terminos_uso", "1.0.0", False),
        ("terminos_uso", "2.0.0", True),
    ]
    assert "contenido" not in r.json()[0]
    assert set(r.json()[0]) >= {
        "tipo",
        "version",
        "tipo_cambio",
        "vigente_desde",
        "resumenes",
        "resumen_cambios",
        "programada",
    }


async def test_get_version_sirve_siempre_el_texto_exacto_de_cada_version(
    cliente: AsyncClient, administrador: Cabeceras
) -> None:
    await _publicar(cliente, administrador, contenido="Texto uno")
    await _publicar(
        cliente, administrador, version="1.0.1", tipo_cambio="parche", contenido="Texto dos"
    )
    uno = (await cliente.get(f"{BASE}/terminos_uso/versiones/1.0.0")).json()
    dos = (await cliente.get(f"{BASE}/terminos_uso/versiones/1.0.1")).json()
    assert (uno["contenido"], dos["contenido"]) == ("Texto uno", "Texto dos")
    assert uno["contenido_html"] == "<p>Texto uno</p>\n"


async def test_el_html_servido_sale_saneado(cliente: AsyncClient, administrador: Cabeceras) -> None:
    malo = (
        "# T\n\n<script>alert(1)</script>\n\n[x](javascript:alert(1)) "
        "[y](https://bugalu.pe) <img src=x onerror=alert(1)>"
    )
    await _publicar(cliente, administrador, contenido=malo)
    r = await cliente.get(f"{BASE}/terminos_uso/versiones/1.0.0")
    html = r.json()["contenido_html"]
    assert "<script" not in html and "<img" not in html and 'href="javascript' not in html
    assert 'href="https://bugalu.pe"' in html
    assert r.json()["contenido"] == malo  # el Markdown se guarda tal cual


@pytest.mark.parametrize(
    "ruta",
    ["terminos_uso/versiones/1.0.0", "otro/versiones/1.0.0", "terminos_uso/versiones/x"],
)
async def test_get_version_inexistente_da_404(cliente: AsyncClient, ruta: str) -> None:
    r = await cliente.get(f"{BASE}/{ruta}")
    assert (r.status_code, r.json()["error"]["codigo"]) == (404, "no_encontrado")


# --- aceptaciones ---------------------------------------------------------------------------------


async def _con_textos(cliente: AsyncClient, administrador: Cabeceras) -> None:
    await _publicar(cliente, administrador)
    await _publicar(cliente, administrador, tipo="politica_privacidad")


def _aceptar(cabeceras: Cabeceras, *textos: tuple[str, str]) -> dict[str, Any]:
    return {
        "headers": cabeceras,
        "json": {
            "contexto": "registro",
            "textos": [{"tipo": t, "version": v} for t, v in textos],
        },
    }


async def test_el_cliente_acepta_la_vigente_y_queda_registrada(
    cliente: AsyncClient, administrador: Cabeceras, crear_usuario: Crear, sql: Sql
) -> None:
    await _con_textos(cliente, administrador)
    u = crear_usuario()
    r = await cliente.post(
        "/api/v1/aceptaciones",
        **_aceptar(_con(u), ("terminos_uso", "1.0.0"), ("politica_privacidad", "1.0.0")),
    )
    assert r.status_code == 201, r.text
    cuerpo = r.json()
    assert [(a["tipo"], a["version"], a["contexto"]) for a in cuerpo] == [
        ("politica_privacidad", "1.0.0", "registro"),
        ("terminos_uso", "1.0.0", "registro"),
    ]
    assert cuerpo[0]["id_operacion"] is None and cuerpo[0]["retirada_en"] is None
    assert cuerpo[0]["aceptante"] is None
    assert datetime.fromisoformat(cuerpo[0]["aceptada_en"]).tzinfo is not None
    assert sql("select count(*) from public.aceptacion where id_usuario = %s", u.id) == [(2,)]
    # repetir no duplica
    r2 = await cliente.post("/api/v1/aceptaciones", **_aceptar(_con(u), ("terminos_uso", "1.0.0")))
    assert r2.status_code == 201
    assert [a["id"] for a in r2.json()] == [a["id"] for a in cuerpo if a["tipo"] == "terminos_uso"]
    assert sql("select count(*) from public.aceptacion where id_usuario = %s", u.id) == [(2,)]


async def test_409_texto_desactualizado_trae_la_vigente_y_no_guarda_nada(
    cliente: AsyncClient, administrador: Cabeceras, crear_usuario: Crear, sql: Sql
) -> None:
    await _con_textos(cliente, administrador)
    await _publicar(cliente, administrador, version="2.0.0", vigente_desde=_fecha(16))
    u = crear_usuario()
    for version in ("2.0.0", "0.5.0"):  # programada y desconocida: solo la vigente se acepta
        r = await cliente.post(
            "/api/v1/aceptaciones",
            **_aceptar(_con(u), ("politica_privacidad", "1.0.0"), ("terminos_uso", version)),
        )
        assert (r.status_code, r.json()["error"]["codigo"]) == (409, "texto_desactualizado")
        vigente = r.json()["error"]["detalles"]["vigente"]
        assert (vigente["tipo"], vigente["version"]) == ("terminos_uso", "1.0.0")
    assert sql("select count(*) from public.aceptacion where id_usuario = %s", u.id) == [(0,)]


async def test_409_si_el_texto_no_esta_publicado(
    cliente: AsyncClient, crear_usuario: Crear
) -> None:
    r = await cliente.post(
        "/api/v1/aceptaciones", **_aceptar(_con(crear_usuario()), ("terminos_uso", "1.0.0"))
    )
    assert (r.status_code, r.json()["error"]["codigo"]) == (409, "texto_desactualizado")


@pytest.mark.parametrize(
    "cuerpo",
    [
        {"contexto": "reserva", "textos": [{"tipo": "terminos_uso", "version": "1.0.0"}]},
        {"contexto": "registro", "textos": []},
        {
            "contexto": "registro",
            "textos": [{"tipo": "condiciones_contratacion", "version": "1.0.0"}],
        },
        {"contexto": "registro", "textos": [{"tipo": "terminos_uso", "version": "1.0.0"}] * 2},
        {"contexto": "registro", "textos": [{"tipo": "terminos_uso"}]},
        {"contexto": "registro"},
    ],
)
async def test_422_de_aceptaciones(
    cliente: AsyncClient,
    administrador: Cabeceras,
    crear_usuario: Crear,
    cuerpo: dict[str, Any],
) -> None:
    await _con_textos(cliente, administrador)
    r = await cliente.post("/api/v1/aceptaciones", headers=_con(crear_usuario()), json=cuerpo)
    assert (r.status_code, r.json()["error"]["codigo"]) == (422, "datos_invalidos")


async def test_aceptar_exige_sesion_y_rechaza_un_token_manipulado(
    cliente: AsyncClient, crear_usuario: Crear
) -> None:
    cuerpo = {"contexto": "registro", "textos": [{"tipo": "terminos_uso", "version": "1.0.0"}]}
    assert (await cliente.post("/api/v1/aceptaciones", json=cuerpo)).status_code == 401
    cabecera, carga, firma = crear_usuario().token.split(".")
    datos = json.loads(base64.urlsafe_b64decode(carga + "=="))
    datos["sub"] = str(uuid4())
    falsa = base64.urlsafe_b64encode(json.dumps(datos).encode()).rstrip(b"=").decode()
    r = await cliente.post(
        "/api/v1/aceptaciones",
        headers={"Authorization": f"Bearer {cabecera}.{falsa}.{firma}"},
        json=cuerpo,
    )
    assert r.status_code == 401


async def test_mis_aceptaciones_solo_trae_las_propias_mas_recientes_primero(
    cliente: AsyncClient, administrador: Cabeceras, crear_usuario: Crear
) -> None:
    await _con_textos(cliente, administrador)
    a, b = crear_usuario(), crear_usuario()
    await cliente.post("/api/v1/aceptaciones", **_aceptar(_con(a), ("terminos_uso", "1.0.0")))
    await cliente.post(
        "/api/v1/aceptaciones", **_aceptar(_con(a), ("politica_privacidad", "1.0.0"))
    )
    await cliente.post("/api/v1/aceptaciones", **_aceptar(_con(b), ("terminos_uso", "1.0.0")))
    r = await cliente.get("/api/v1/aceptaciones/mias", headers=_con(a))
    assert r.status_code == 200
    assert [x["tipo"] for x in r.json()] == ["politica_privacidad", "terminos_uso"]
    vacias = await cliente.get("/api/v1/aceptaciones/mias", headers=_con(crear_usuario()))
    assert vacias.json() == []
    assert (await cliente.get("/api/v1/aceptaciones/mias")).status_code == 401


async def test_el_administrador_ve_las_aceptaciones_de_un_usuario(
    cliente: AsyncClient, administrador: Cabeceras, crear_usuario: Crear
) -> None:
    await _con_textos(cliente, administrador)
    u, otro = crear_usuario(), crear_usuario()
    await cliente.post("/api/v1/aceptaciones", **_aceptar(_con(u), ("terminos_uso", "1.0.0")))
    r = await cliente.get(f"/api/v1/usuarios/{u.id}/aceptaciones", headers=administrador)
    assert r.status_code == 200 and [x["tipo"] for x in r.json()] == ["terminos_uso"]
    # un cliente no ve las de nadie, ni siquiera las suyas por esta ruta
    for objetivo in (u, otro):
        r403 = await cliente.get(f"/api/v1/usuarios/{objetivo.id}/aceptaciones", headers=_con(u))
        assert (r403.status_code, r403.json()["error"]["codigo"]) == (403, "sin_permiso")
    assert (await cliente.get(f"/api/v1/usuarios/{u.id}/aceptaciones")).status_code == 401
    r404 = await cliente.get(f"/api/v1/usuarios/{uuid4()}/aceptaciones", headers=administrador)
    assert (r404.status_code, r404.json()["error"]["codigo"]) == (404, "no_encontrado")
    malo = await cliente.get("/api/v1/usuarios/no-es-uuid/aceptaciones", headers=administrador)
    assert malo.status_code == 422


# --- fallos de infraestructura y contrato ---------------------------------------------------------


async def test_503_con_la_base_caida_nunca_500(
    monkeypatch: pytest.MonkeyPatch, crear_usuario: Crear
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
        for ruta, cabeceras in (
            (BASE, {}),
            (f"{BASE}/terminos_uso/versiones/1.0.0", {}),
            ("/api/v1/aceptaciones/mias", _con(usuario)),
        ):
            r = await c.get(ruta, headers=cabeceras)
            assert r.status_code == 503, (ruta, r.status_code)
            assert r.json()["error"]["codigo"] == "base_de_datos_no_disponible"


CONTRATO = {
    ("get", "/api/v1/textos-legales"): {503},
    ("post", "/api/v1/textos-legales"): {401, 403, 409, 422, 503},
    ("get", "/api/v1/textos-legales/{tipo}/versiones/{version}"): {404, 503},
    ("delete", "/api/v1/textos-legales/{tipo}/versiones/{version}"): {401, 403, 404, 409, 503},
    ("post", "/api/v1/aceptaciones"): {401, 409, 422, 503},
    ("get", "/api/v1/aceptaciones/mias"): {401, 503},
    ("get", "/api/v1/usuarios/{id_usuario}/aceptaciones"): {401, 403, 404, 422, 503},
}


def test_openapi_declara_los_codigos_del_contrato(app: FastAPI) -> None:
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
    assert rutas["/api/v1/textos-legales"]["post"]["responses"]["201"]
    assert rutas["/api/v1/textos-legales/{tipo}/versiones/{version}"]["delete"]["responses"]["204"]
