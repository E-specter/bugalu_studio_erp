"""RF-17 etapa A: perfil reforzado, pendientes y consentimientos (stack local, RLS real)."""

import threading
import time
from collections.abc import Callable
from typing import Any

import psycopg
import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from bugalu.compartido.configuracion import Configuracion, obtener_configuracion
from bugalu.main import crear_app
from tests.conftest import UsuarioDePrueba

pytestmark = [pytest.mark.integracion, pytest.mark.usefixtures("textos_de_prueba")]

Crear = Callable[[], UsuarioDePrueba]
Sql = Callable[..., list[tuple[Any, ...]]]
PERFIL = "/api/v1/perfil"
DNI = {"tipo": "dni", "numero": "12345678"}


def _con(usuario: UsuarioDePrueba) -> dict[str, str]:
    return {"Authorization": f"Bearer {usuario.token}"}


def _codigo(r: Any) -> str:
    return str(r.json()["error"]["codigo"])


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
) -> UsuarioDePrueba:
    u = crear_usuario()
    poner_rol(u, "administrador", None)
    return u


def _aceptar(*tipos: str) -> dict[str, Any]:
    return {"contexto": "registro", "textos": [{"tipo": t, "version": "1.0.0"} for t in tipos]}


# --- GET /perfil ---------------------------------------------------------------------------------


async def test_get_perfil_trae_modalidad_pendientes_y_consentimientos(
    cliente: AsyncClient, crear_usuario: Crear
) -> None:
    u = crear_usuario()
    j = (await cliente.get(PERFIL, headers=_con(u))).json()
    assert (j["modalidad"], j["documento"], j["domicilio"], j["redes"], j["integrantes"]) == (
        "individual",
        None,
        None,
        [],
        [],
    )
    assert j["es_menor"] is False
    assert j["consentimientos"] == {
        "promociones_correo": False,
        "promociones_whatsapp": False,
        "fotos_videos": False,
        "excluir_material": False,
    }
    assert j["datos_para_reservar"] is False
    assert [(p["tipo"], p["version"], p["contexto"], p["motivo"]) for p in j["pendientes"]] == [
        ("politica_privacidad", "1.0.0", "registro", "registro_pendiente"),
        ("terminos_uso", "1.0.0", "registro", "registro_pendiente"),
    ]
    assert "documento_repetido" not in j  # solo lo ve el Administrador


async def test_pendientes_vacios_y_datos_para_reservar_con_el_perfil_completo(
    cliente: AsyncClient, crear_usuario: Crear, completar_perfil: Callable[..., UsuarioDePrueba]
) -> None:
    u = completar_perfil(crear_usuario())
    j = (await cliente.get(PERFIL, headers=_con(u))).json()
    assert (j["pendientes"], j["datos_para_reservar"]) == ([], True)
    assert j["documento"]["tipo"] == "dni"


async def test_una_version_mayor_de_terminos_queda_pendiente_y_la_menor_no(
    cliente: AsyncClient,
    crear_usuario: Crear,
    completar_perfil: Callable[..., UsuarioDePrueba],
    sql: Sql,
) -> None:
    u = completar_perfil(crear_usuario())
    sql(
        "insert into public.texto_legal (tipo, version, tipo_cambio, contenido, vigente_desde) "
        "values ('terminos_uso', '1.1.0', 'menor', 'x', now())"
    )
    assert (await cliente.get(PERFIL, headers=_con(u))).json()["pendientes"] == []
    sql(
        "insert into public.texto_legal (tipo, version, tipo_cambio, contenido, vigente_desde) "
        "values ('terminos_uso', '2.0.0', 'mayor', 'x', now())"
    )
    pendientes = (await cliente.get(PERFIL, headers=_con(u))).json()["pendientes"]
    assert pendientes == [
        {
            "tipo": "terminos_uso",
            "version": "2.0.0",
            "contexto": "registro",
            "motivo": "version_mayor",
        }
    ]


async def test_el_registro_acepta_terminos_politica_y_declaracion_juntos(
    cliente: AsyncClient, crear_usuario: Crear
) -> None:
    u = crear_usuario()
    r = await cliente.post(
        "/api/v1/aceptaciones",
        headers=_con(u),
        json=_aceptar("terminos_uso", "politica_privacidad", "declaracion_agrupacion"),
    )
    assert r.status_code == 201
    assert {(a["tipo"], a["contexto"]) for a in r.json()} == {
        ("terminos_uso", "registro"),
        ("politica_privacidad", "registro"),
        ("declaracion_agrupacion", "registro"),
    }


# --- PATCH /perfil -------------------------------------------------------------------------------


async def test_patch_guarda_documento_domicilio_y_redes_y_el_get_los_devuelve(
    cliente: AsyncClient, crear_usuario: Crear
) -> None:
    u = crear_usuario()
    cuerpo = {
        "documento": DNI,
        "domicilio": "Av. Lima 123, Lima",
        "redes": [{"red": "instagram", "valor": "@banda"}, {"red": "otra", "valor": "banda.pe"}],
        "es_menor": False,
    }
    r = await cliente.patch(PERFIL, headers=_con(u), json=cuerpo)
    assert r.status_code == 200
    for clave, valor in cuerpo.items():
        assert r.json()[clave] == valor
    assert (await cliente.get(PERFIL, headers=_con(u))).json()["documento"] == DNI


@pytest.mark.parametrize("tipo", ["ce", "pasaporte"])
async def test_el_documento_de_extranjeria_pierde_los_espacios_internos(
    cliente: AsyncClient, crear_usuario: Crear, tipo: str
) -> None:
    u = crear_usuario()
    r = await cliente.patch(
        PERFIL, headers=_con(u), json={"documento": {"tipo": tipo, "numero": "ab 123456"}}
    )
    assert r.status_code == 200
    assert r.json()["documento"] == {"tipo": tipo, "numero": "AB123456"}


async def test_el_documento_de_extranjeria_se_normaliza_a_mayusculas(
    cliente: AsyncClient, crear_usuario: Crear
) -> None:
    u = crear_usuario()
    r = await cliente.patch(
        PERFIL, headers=_con(u), json={"documento": {"tipo": "ce", "numero": " ab123456 "}}
    )
    assert r.status_code == 200
    assert r.json()["documento"] == {"tipo": "ce", "numero": "AB123456"}


@pytest.mark.parametrize(
    "cuerpo",
    [
        {"documento": {"tipo": "dni", "numero": "1234567"}},
        {"documento": {"tipo": "dni", "numero": "1234567A"}},
        {"documento": {"tipo": "ce", "numero": "AB123"}},
        {"documento": {"tipo": "pasaporte", "numero": "AB-123456"}},
        {"documento": {"tipo": "ce", "numero": "A" * 13}},
        {"documento": {"tipo": "cedula", "numero": "12345678"}},
        {"documento": None},
        {"domicilio": "x" * 201},
        {"redes": [{"red": "instagram", "valor": "@x"}] * 6},
        {"redes": [{"red": "myspace", "valor": "@x"}]},
        {"redes": [{"red": "tiktok", "valor": ""}]},
        {"redes": None},
        {"integrantes": [{"nombre": "A", "rol": "voz"}] * 21},
        {"integrantes": [{"nombre": "A"}]},
        {"integrantes": None},
        {"modalidad": "banda"},
        {"modalidad": None},
        {"es_menor": None},
        {"documento_repetido": True},
        {"rol": "administrador"},
    ],
)
async def test_patch_invalido_es_422_y_no_cambia_nada(
    cliente: AsyncClient, crear_usuario: Crear, sql: Sql, cuerpo: dict[str, Any]
) -> None:
    u = crear_usuario()
    r = await cliente.patch(PERFIL, headers=_con(u), json=cuerpo)
    assert (r.status_code, _codigo(r)) == (422, "datos_invalidos")
    fila = sql(
        "select documento_numero, domicilio, redes::text, integrantes::text, modalidad, rol "
        "from public.usuario where id = %s",
        u.id,
    )[0]
    assert fila == (None, None, "[]", "[]", "individual", "cliente")


async def test_agrupacion_sin_la_declaracion_aceptada_es_409_y_no_cambia_la_cuenta(
    cliente: AsyncClient, crear_usuario: Crear, sql: Sql
) -> None:
    u = crear_usuario()
    cuerpo = {
        "modalidad": "agrupacion",
        "nombre_artistico": "Los Tigres",
        "integrantes": [{"nombre": "Ana", "rol": "voz"}],
    }
    r = await cliente.patch(PERFIL, headers=_con(u), json=cuerpo)
    assert (r.status_code, _codigo(r)) == (409, "declaracion_requerida")
    assert sql("select modalidad, nombre_artistico from public.usuario where id = %s", u.id) == [
        ("individual", None)
    ]
    await cliente.post(
        "/api/v1/aceptaciones", headers=_con(u), json=_aceptar("declaracion_agrupacion")
    )
    ok = await cliente.patch(PERFIL, headers=_con(u), json=cuerpo)
    assert ok.status_code == 200
    assert (ok.json()["modalidad"], ok.json()["nombre_artistico"]) == ("agrupacion", "Los Tigres")
    assert ok.json()["integrantes"] == [{"nombre": "Ana", "rol": "voz"}]


async def test_agrupacion_exige_integrantes_y_el_individual_no_los_lleva(
    cliente: AsyncClient, crear_usuario: Crear
) -> None:
    u = crear_usuario()
    await cliente.post(
        "/api/v1/aceptaciones", headers=_con(u), json=_aceptar("declaracion_agrupacion")
    )
    sin = await cliente.patch(PERFIL, headers=_con(u), json={"modalidad": "agrupacion"})
    assert (sin.status_code, _codigo(sin), sin.json()["error"]["detalles"]) == (
        422,
        "datos_invalidos",
        {"campo": "integrantes"},
    )
    con = await cliente.patch(
        PERFIL,
        headers=_con(u),
        json={"modalidad": "individual", "integrantes": [{"nombre": "A", "rol": "voz"}]},
    )
    assert (con.status_code, _codigo(con)) == (422, "datos_invalidos")


async def test_volver_a_individual_borra_los_integrantes(
    cliente: AsyncClient, crear_usuario: Crear
) -> None:
    u = crear_usuario()
    await cliente.post(
        "/api/v1/aceptaciones", headers=_con(u), json=_aceptar("declaracion_agrupacion")
    )
    await cliente.patch(
        PERFIL,
        headers=_con(u),
        json={"modalidad": "agrupacion", "integrantes": [{"nombre": "A", "rol": "voz"}]},
    )
    r = await cliente.patch(PERFIL, headers=_con(u), json={"modalidad": "individual"})
    assert (r.status_code, r.json()["integrantes"]) == (200, [])


# --- documento repetido --------------------------------------------------------------------------


async def test_un_documento_repetido_no_bloquea_y_marca_ambas_cuentas(
    cliente: AsyncClient, crear_usuario: Crear, administrador: UsuarioDePrueba
) -> None:
    a, b = crear_usuario(), crear_usuario()
    numero = DNI["numero"][:-1] + "7"  # distinto del de otras pruebas
    doc = {"documento": {"tipo": "dni", "numero": numero}}
    assert (await cliente.patch(PERFIL, headers=_con(a), json=doc)).status_code == 200
    assert (await cliente.patch(PERFIL, headers=_con(b), json=doc)).status_code == 200  # no bloquea

    async def marcados() -> set[str]:
        r = await cliente.get(
            "/api/v1/usuarios?documento_repetido=true", headers=_con(administrador)
        )
        assert r.status_code == 200
        assert all(u["documento_repetido"] for u in r.json())
        return {u["id"] for u in r.json()}

    assert {str(a.id), str(b.id)} <= await marcados()
    cambio = {"documento": {"tipo": "dni", "numero": "76543210"}}
    await cliente.patch(PERFIL, headers=_con(b), json=cambio)
    assert not ({str(a.id), str(b.id)} & await marcados())


def test_dos_cuentas_que_guardan_el_mismo_documento_a_la_vez_quedan_marcadas(
    configuracion: Configuracion, crear_usuario: Crear
) -> None:
    a, b = crear_usuario(), crear_usuario()
    cambio = (
        "update public.usuario set documento_tipo = 'dni', documento_numero = '55443322' "
        "where id = %s"
    )
    url = configuracion.url_base_datos_admin
    with psycopg.connect(url) as ca, psycopg.connect(url) as cb:
        ca.execute(cambio, (a.id,))  # A abre su transaccion sin confirmar

        def guardar_b() -> None:
            cb.execute(cambio, (b.id,))
            cb.commit()

        hilo = threading.Thread(target=guardar_b)
        hilo.start()
        time.sleep(1)  # B corre en paralelo; con el bloqueo espera a A, sin el confirma ya
        ca.commit()
        hilo.join(10)
    with psycopg.connect(url) as c:
        filas = c.execute(
            "select count(*) > 1 from public.usuario where documento_numero = '55443322'"
        ).fetchall()
    assert filas == [(True,)]  # ambas guardaron el documento sin esperar ni perder la escritura


async def test_dos_cuentas_que_intercambian_documentos_a_la_vez_no_se_interbloquean(
    cliente: AsyncClient,
    configuracion: Configuracion,
    crear_usuario: Crear,
    administrador: UsuarioDePrueba,
) -> None:
    a, b = crear_usuario(), crear_usuario()
    x, y, p, q = "11110001", "11110002", "11110003", "11110004"
    cambio = "update public.usuario set documento_tipo = 'dni', documento_numero = %s where id = %s"
    url = configuracion.url_base_datos_admin
    errores: list[Exception] = []
    with psycopg.connect(url) as ca, psycopg.connect(url) as cb:
        ca.execute(cambio, (x, a.id))
        cb.execute(cambio, (y, b.id))
        ca.commit()
        cb.commit()
        ca.execute(cambio, (p, a.id))  # cada transaccion toca dos documentos, en orden cruzado
        cb.execute(cambio, (q, b.id))

        def segundo(con: psycopg.Connection[Any], numero: str, id_: Any) -> None:
            try:
                con.execute(cambio, (numero, id_))
                con.commit()
            except psycopg.errors.DeadlockDetected as error:
                errores.append(error)

        hilo = threading.Thread(target=segundo, args=(ca, y, a.id))
        hilo.start()
        time.sleep(0.5)  # A ya espera a B si el cambio de documento toma bloqueos por documento
        segundo(cb, x, b.id)
        hilo.join(15)
    assert errores == []
    r = await cliente.get("/api/v1/usuarios?documento_repetido=true", headers=_con(administrador))
    assert not ({str(a.id), str(b.id)} & {u["id"] for u in r.json()})  # ahora x e y no se repiten


async def test_la_marca_de_documento_repetido_se_calcula_al_leer(
    cliente: AsyncClient, crear_usuario: Crear, administrador: UsuarioDePrueba, sql: Sql
) -> None:
    a, b = crear_usuario(), crear_usuario()
    cambio = "update public.usuario set documento_tipo = 'dni', documento_numero = '11110009'"
    sql(cambio + " where id = any(%s)", [a.id, b.id])
    r = await cliente.get("/api/v1/usuarios?documento_repetido=true", headers=_con(administrador))
    assert {str(a.id), str(b.id)} <= {u["id"] for u in r.json()}
    assert not sql(
        "select 1 from pg_attribute where attrelid = 'public.usuario'::regclass "
        "and attname = 'documento_repetido' and not attisdropped"
    )  # ya no hay columna guardada ni trigger que toque filas ajenas


async def test_el_filtro_de_documento_repetido_es_del_administrador(
    cliente: AsyncClient, crear_usuario: Crear
) -> None:
    u = crear_usuario()
    r = await cliente.get("/api/v1/usuarios?documento_repetido=true", headers=_con(u))
    assert (r.status_code, _codigo(r)) == (403, "sin_permiso")
    assert (await cliente.get("/api/v1/usuarios?documento_repetido=true")).status_code == 401
    malo = await cliente.get("/api/v1/usuarios?documento_repetido=quiza", headers=_con(u))
    assert malo.status_code == 422


async def test_nadie_edita_el_perfil_ajeno_por_la_api(
    cliente: AsyncClient, crear_usuario: Crear, sql: Sql
) -> None:
    a, b = crear_usuario(), crear_usuario()
    await cliente.patch(PERFIL, headers=_con(a), json={"domicilio": "Mi casa"})
    assert sql("select domicilio from public.usuario where id = %s", b.id) == [(None,)]
    assert sql("select domicilio from public.usuario where id = %s", a.id) == [("Mi casa",)]


# --- PUT /perfil/consentimientos -----------------------------------------------------------------

CONSENTIMIENTOS = "/api/v1/perfil/consentimientos"


def _activas(sql: Sql, u: UsuarioDePrueba) -> list[tuple[Any, ...]]:
    return sql(
        "select consentimiento, tipo, version, retirada_en is not null from public.aceptacion "
        "where id_usuario = %s and consentimiento is not null order by consentimiento, aceptada_en",
        u.id,
    )


async def test_dar_y_retirar_consentimientos_solo_registra_lo_que_cambia(
    cliente: AsyncClient, crear_usuario: Crear, sql: Sql
) -> None:
    u = crear_usuario()
    sql("update public.usuario set telefono = '987654321' where id = %s", u.id)
    r = await cliente.put(
        CONSENTIMIENTOS,
        headers=_con(u),
        json={"promociones_correo": True, "fotos_videos": True},
    )
    assert r.status_code == 200
    assert r.json() == {
        "promociones_correo": True,
        "promociones_whatsapp": False,
        "fotos_videos": True,
        "excluir_material": False,
    }
    assert _activas(sql, u) == [
        ("fotos_videos", "condiciones_contratacion", "1.0.0", False),
        ("promociones_correo", "politica_privacidad", "1.0.0", False),
    ]
    # Repetir lo mismo no crea otra fila.
    await cliente.put(CONSENTIMIENTOS, headers=_con(u), json={"promociones_correo": True})
    assert len(_activas(sql, u)) == 2
    # Retirar marca la fecha; volver a darlo crea otra aceptacion.
    r = await cliente.put(CONSENTIMIENTOS, headers=_con(u), json={"promociones_correo": False})
    assert r.json()["promociones_correo"] is False
    await cliente.put(CONSENTIMIENTOS, headers=_con(u), json={"promociones_correo": True})
    filas = [f for f in _activas(sql, u) if f[0] == "promociones_correo"]
    assert [f[3] for f in filas] == [True, False]
    perfil = (await cliente.get(PERFIL, headers=_con(u))).json()
    assert perfil["consentimientos"]["promociones_correo"] is True


async def test_whatsapp_exige_telefono(
    cliente: AsyncClient, crear_usuario: Crear, sql: Sql
) -> None:
    u = crear_usuario()
    r = await cliente.put(CONSENTIMIENTOS, headers=_con(u), json={"promociones_whatsapp": True})
    assert (r.status_code, _codigo(r)) == (422, "telefono_requerido")
    assert _activas(sql, u) == []
    sql("update public.usuario set telefono = '987654321' where id = %s", u.id)
    ok = await cliente.put(CONSENTIMIENTOS, headers=_con(u), json={"promociones_whatsapp": True})
    assert (ok.status_code, ok.json()["promociones_whatsapp"]) == (200, True)


@pytest.mark.parametrize(
    "cuerpo", [{"promociones_correo": "si"}, {"promociones_correo": None}, {"otro": True}]
)
async def test_consentimientos_invalidos_son_422(
    cliente: AsyncClient, crear_usuario: Crear, cuerpo: dict[str, Any]
) -> None:
    r = await cliente.put(CONSENTIMIENTOS, headers=_con(crear_usuario()), json=cuerpo)
    assert (r.status_code, _codigo(r)) == (422, "datos_invalidos")


async def test_consentimientos_exigen_sesion(cliente: AsyncClient) -> None:
    assert (await cliente.put(CONSENTIMIENTOS, json={})).status_code == 401


# --- infraestructura y contrato ------------------------------------------------------------------


async def test_503_con_la_base_caida_nunca_500(
    monkeypatch: pytest.MonkeyPatch, crear_usuario: Crear
) -> None:
    u = crear_usuario()
    monkeypatch.setenv("URL_BASE_DATOS", "postgresql://u:p@127.0.0.1:1/db")
    monkeypatch.setenv("TIMEOUT_POOL_SEGUNDOS", "0.5")
    obtener_configuracion.cache_clear()
    app = crear_app()
    async with (
        app.router.lifespan_context(app),
        AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c,
    ):
        for metodo, ruta, cuerpo in (
            ("GET", PERFIL, None),
            ("PATCH", PERFIL, {"domicilio": "x"}),
            ("PUT", CONSENTIMIENTOS, {"fotos_videos": True}),
        ):
            r = await c.request(metodo, ruta, headers=_con(u), json=cuerpo)
            assert r.status_code == 503, (ruta, r.status_code)
            assert _codigo(r) == "base_de_datos_no_disponible"


def test_openapi_declara_los_codigos_del_perfil(app: FastAPI) -> None:
    rutas = app.openapi()["paths"]
    esperados = {
        ("patch", "/api/v1/perfil"): {401, 409, 422, 503},
        ("put", "/api/v1/perfil/consentimientos"): {401, 409, 422, 503},
        ("get", "/api/v1/usuarios"): {401, 403, 422, 503},
    }
    for (metodo, ruta), codigos in esperados.items():
        for codigo in codigos:
            esquema = rutas[ruta][metodo]["responses"][str(codigo)]["content"]["application/json"]
            assert esquema["schema"] == {"$ref": "#/components/schemas/RespuestaError"}
