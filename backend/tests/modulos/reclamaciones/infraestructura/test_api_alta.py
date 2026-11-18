# ruff: noqa: E501, F811 - SQL literal y fixtures compartidas
"""POST /reclamaciones: alta publica con o sin sesion, adjuntos, limite por IP y errores."""

import asyncio
import base64
import hashlib
import json
import re
import uuid
from typing import Any

import pytest
from httpx import AsyncClient

from bugalu.compartido.configuracion import Configuracion
from bugalu.compartido.errores import AlmacenamientoNoDisponible
from bugalu.modulos.reclamaciones.infraestructura.entrada.http import router as modulo_router
from tests.conftest import UsuarioDePrueba
from tests.modulos.reclamaciones.infraestructura.conftest import (
    HOJAS,
    JPG,
    PDF,
    PNG,
    datos,
    enviar,
)
from tests.modulos.reservas.infraestructura.conftest import Ejecutar, con

pytestmark = pytest.mark.integracion


def codigo(r: Any) -> str:
    return str(r.json()["error"]["codigo"])


def hojas_de(sql: Ejecutar, correo: str) -> int:
    return int(sql("select count(*) from public.hoja_reclamacion where correo = %s", correo)[0][0])


# --- exito -----------------------------------------------------------------------------------


async def test_un_visitante_registra_una_hoja_sin_cuenta(
    anonimo: AsyncClient, sql: Ejecutar
) -> None:
    cuerpo = datos()
    r = await enviar(anonimo, cuerpo, [("foto.png", PNG, "image/png")])
    assert r.status_code == 201, r.text
    hoja = r.json()
    assert re.fullmatch(r"[0-9]{9}-[0-9]{4}", hoja["numero"])
    assert hoja["estado"] == "pendiente"
    assert hoja["origen"] == "web"
    assert hoja["proveedor"] == {
        "razon_social": "Aural Perú E.I.R.L.",
        "ruc": "20615656128",
        "domicilio": "Av. Javier Prado Este 5920, La Molina, Lima",
    }
    assert hoja["consumidor"]["correo"] == cuerpo["consumidor"]["correo"]
    assert hoja["bien"] == {
        "tipo": "servicio",
        "monto": "50.00",
        "descripcion": "Ensayo del 10 de marzo",
    }
    assert hoja["tipo"] == "reclamo"
    assert hoja["dias_habiles_restantes"] in (14, 15)  # 15 dias habiles, salvo feriados
    assert hoja["revisar_spam"] is None  # la marca es del Administrador
    assert hoja["respuesta"] is None
    assert [(a["n"], a["nombre"], a["tipo"], a["tamano"]) for a in hoja["adjuntos"]] == [
        (1, "foto.png", "image/png", len(PNG))
    ]
    fila = sql(
        "select id_cuenta, origen, vence_respuesta > now() + interval '14 days' "
        "from public.hoja_reclamacion where id = %s",
        hoja["id"],
    )
    assert fila == [(None, "web", True)]
    (ruta,) = sql("select ruta from public.adjunto_reclamacion where id_hoja = %s", hoja["id"])[0]
    assert re.fullmatch(rf"{hoja['id']}/[0-9a-f-]{{36}}\.png", ruta)  # nombre aleatorio de la base
    assert sql(
        "select name from storage.objects where bucket_id = 'reclamaciones' "
        "and (storage.foldername(name))[1] = %s",
        hoja["id"],
    ) == [(ruta,)]
    assert hoja["adjuntos_no_guardados"] == []


async def test_el_tipo_de_los_adjuntos_sale_del_contenido_no_del_nombre(
    anonimo: AsyncClient, sql: Ejecutar
) -> None:
    r = await enviar(
        anonimo,
        datos(),
        [
            ("a.pdf", PNG, "application/pdf"),
            ("b.png", JPG, "image/png"),
            ("c.jpg", PDF, "image/jpeg"),
        ],
    )
    assert r.status_code == 201, r.text
    assert [a["tipo"] for a in r.json()["adjuntos"]] == [
        "image/png",
        "image/jpeg",
        "application/pdf",
    ]
    rutas = sql(
        "select ruta from public.adjunto_reclamacion where id_hoja = %s order by n", r.json()["id"]
    )
    assert [x[0].rsplit(".", 1)[1] for x in rutas] == ["png", "jpg", "pdf"]


async def test_con_sesion_la_hoja_queda_vinculada_y_el_dueno_la_ve_en_mis_reclamos(
    anonimo: AsyncClient, cliente_a: UsuarioDePrueba, cliente_b: UsuarioDePrueba, sql: Ejecutar
) -> None:
    r = await enviar(anonimo, datos(), usuario=cliente_a)
    assert r.status_code == 201, r.text
    id_ = r.json()["id"]
    assert sql("select id_cuenta from public.hoja_reclamacion where id = %s", id_) == [
        (cliente_a.id,)
    ]
    mias = await anonimo.get(f"{HOJAS}/mias", headers=con(cliente_a))
    assert [h["id"] for h in mias.json()] == [id_]
    assert set(mias.json()[0]) >= {
        "id",
        "numero",
        "creada_en",
        "tipo",
        "estado",
        "vence_respuesta",
        "consumidor",
    }
    assert "revisar_spam" not in mias.json()[0] or mias.json()[0]["revisar_spam"] is None
    assert (await anonimo.get(f"{HOJAS}/{id_}", headers=con(cliente_a))).status_code == 200
    # otro cliente, y quien no tiene sesion: no se revela
    ajeno = await anonimo.get(f"{HOJAS}/{id_}", headers=con(cliente_b))
    assert (ajeno.status_code, codigo(ajeno)) == (404, "no_encontrado")
    assert (await anonimo.get(f"{HOJAS}/mias", headers=con(cliente_b))).json() == []
    assert (await anonimo.get(f"{HOJAS}/{id_}")).status_code == 401


async def test_el_campo_trampa_registra_igual_y_marca_la_hoja_para_el_administrador(
    anonimo: AsyncClient, administrador: UsuarioDePrueba, sql: Ejecutar
) -> None:
    r = await enviar(anonimo, datos(sitio_web="http://spam.example"))
    assert r.status_code == 201, r.text
    assert r.json()["revisar_spam"] is None
    assert sql(
        "select revisar_spam from public.hoja_reclamacion where id = %s", r.json()["id"]
    ) == [(True,)]
    vista = await anonimo.get(f"{HOJAS}/{r.json()['id']}", headers=con(administrador))
    assert vista.json()["revisar_spam"] is True
    limpia = await enviar(anonimo, datos(sitio_web=""))
    assert sql(
        "select revisar_spam from public.hoja_reclamacion where id = %s", limpia.json()["id"]
    ) == [(False,)]


async def test_un_menor_con_representante_se_registra(anonimo: AsyncClient) -> None:
    rep = {"nombre": "Rosa Prueba", "domicilio": "Calle 1", "correo": "rosa@prueba.bugalu.pe"}
    r = await enviar(anonimo, datos(es_menor=True, representante=rep))
    assert r.status_code == 201, r.text
    assert r.json()["representante"]["nombre"] == "Rosa Prueba"
    assert r.json()["es_menor"] is True


async def test_el_documento_se_normaliza_y_el_texto_vacio_es_nulo(
    anonimo: AsyncClient, sql: Ejecutar
) -> None:
    cuerpo = datos()
    cuerpo["consumidor"] |= {"tipo_documento": "ce", "documento": " ab 123456 ", "telefono": ""}
    r = await enviar(anonimo, cuerpo)
    assert r.status_code == 201, r.text
    assert sql(
        "select documento, telefono from public.hoja_reclamacion where id = %s", r.json()["id"]
    ) == [("AB123456", None)]


# --- avisos por correo -------------------------------------------------------------------------


async def test_registrar_deja_la_copia_para_el_consumidor_y_el_aviso_para_el_administrador(
    anonimo: AsyncClient, administrador: UsuarioDePrueba, sql: Ejecutar
) -> None:
    cuerpo = datos()
    r = await enviar(anonimo, cuerpo)
    id_ = r.json()["id"]
    filas = sql(
        "select tipo, destinatario from public.notificacion where datos ->> 'id' = %s order by tipo",
        id_,
    )
    correo_admin = sql("select email from auth.users where id = %s", administrador.id)[0][0]
    assert (("reclamacion_recibida", correo_admin) in filas) and (
        ("reclamacion_registrada", cuerpo["consumidor"]["correo"]) in filas
    )


# --- validacion ------------------------------------------------------------------------------


def _con(cambio: dict[str, Any]) -> dict[str, Any]:
    base = datos()
    for clave, valor in cambio.items():
        destino = base
        *ruta, ultima = clave.split(".")
        for paso in ruta:
            destino = destino[paso]
        if valor is None:
            destino.pop(ultima, None)
        else:
            destino[ultima] = valor
    return base


@pytest.mark.parametrize(
    ("cambio", "campo"),
    [
        ({"consumidor.documento": "123"}, "consumidor.documento"),
        ({"consumidor.tipo_documento": "ruc"}, "consumidor.tipo_documento"),
        ({"consumidor.nombre": "x" * 201}, "consumidor.nombre"),
        ({"consumidor.domicilio": None}, "consumidor.domicilio"),
        ({"consumidor.correo": "no-es-un-correo"}, "consumidor.correo"),
        ({"consumidor.telefono": "9" * 21}, "consumidor.telefono"),
        ({"detalle": "corto"}, "detalle"),
        ({"detalle": "x" * 3001}, "detalle"),
        ({"pedido": None}, "pedido"),
        ({"tipo": None}, "tipo"),
        ({"tipo": "sugerencia"}, "tipo"),
        ({"medio_respuesta": "paloma"}, "medio_respuesta"),
        ({"bien.monto": "0"}, "bien.monto"),
        ({"bien.monto": "1000000"}, "bien.monto"),
        ({"bien.monto": "12.345"}, "bien.monto"),
        ({"bien.descripcion": "x" * 1001}, "bien.descripcion"),
        ({"bien.tipo": "otro"}, "bien.tipo"),
        ({"es_menor": True}, "representante"),
        ({"consumidor.nombre": "Ana\x00Prueba"}, "consumidor.nombre"),
        ({"campo_inventado": 1}, "campo_inventado"),
    ],
)
async def test_datos_invalidos_son_422_con_el_campo_y_no_registran_nada(
    anonimo: AsyncClient, sql: Ejecutar, cambio: dict[str, Any], campo: str
) -> None:
    cuerpo = _con(cambio)
    r = await enviar(anonimo, cuerpo)
    assert r.status_code == 422, r.text
    assert codigo(r) == "datos_invalidos"
    assert r.json()["error"]["detalles"]["campo"] == campo
    assert hojas_de(sql, cuerpo["consumidor"]["correo"]) == 0


@pytest.mark.parametrize("datos_rotos", ["no es json", "[1, 2]", "", "null"])
async def test_el_campo_datos_debe_ser_un_objeto_json(
    anonimo: AsyncClient, datos_rotos: str
) -> None:
    r = await anonimo.post(HOJAS, data={"datos": datos_rotos})
    assert (r.status_code, codigo(r)) == (422, "datos_invalidos")


async def test_sin_el_campo_datos_es_422(anonimo: AsyncClient) -> None:
    r = await anonimo.post(HOJAS, data={"otro": "x"})
    assert (r.status_code, codigo(r)) == (422, "datos_invalidos")


@pytest.mark.parametrize("confirmado", [False, None])
async def test_sin_confirmar_es_409_y_no_registra_nada(
    anonimo: AsyncClient, sql: Ejecutar, confirmado: bool | None
) -> None:
    cuerpo = datos(confirmado=confirmado)
    if confirmado is None:
        del cuerpo["confirmado"]
    r = await enviar(anonimo, cuerpo)
    assert (r.status_code, codigo(r)) == (409, "confirmacion_requerida")
    assert hojas_de(sql, cuerpo["consumidor"]["correo"]) == 0


# --- adjuntos ----------------------------------------------------------------------------------


async def test_mas_de_tres_adjuntos_es_422(anonimo: AsyncClient, sql: Ejecutar) -> None:
    cuerpo = datos()
    r = await enviar(anonimo, cuerpo, [("a.png", PNG, "image/png")] * 4)
    assert (r.status_code, codigo(r)) == (422, "demasiados_adjuntos")
    assert hojas_de(sql, cuerpo["consumidor"]["correo"]) == 0


async def test_un_ejecutable_con_nombre_de_imagen_se_rechaza_con_su_posicion(
    anonimo: AsyncClient, sql: Ejecutar
) -> None:
    cuerpo = datos()
    r = await enviar(
        anonimo,
        cuerpo,
        [("a.png", PNG, "image/png"), ("virus.png", b"MZ\x90\x00" * 9, "image/png")],
    )
    assert (r.status_code, codigo(r)) == (422, "adjunto_no_permitido")
    assert r.json()["error"]["detalles"] == {"adjunto": 2}
    assert hojas_de(sql, cuerpo["consumidor"]["correo"]) == 0  # nada a medias


async def test_un_adjunto_de_mas_de_5_mb_es_413_con_su_posicion(
    anonimo: AsyncClient, sql: Ejecutar
) -> None:
    cuerpo = datos()
    grande = PDF + b"0" * (5 * 1024 * 1024)
    r = await enviar(
        anonimo, cuerpo, [("a.pdf", PDF, "application/pdf"), ("b.pdf", grande, "application/pdf")]
    )
    assert (r.status_code, codigo(r)) == (413, "adjunto_muy_grande")
    assert r.json()["error"]["detalles"] == {"adjunto": 2}
    assert hojas_de(sql, cuerpo["consumidor"]["correo"]) == 0


async def test_el_tope_temprano_rechaza_por_content_length_sin_leer_el_cuerpo(
    anonimo: AsyncClient,
) -> None:
    r = await anonimo.post(HOJAS, content=b"x", headers={"Content-Length": str(20 * 1024 * 1024)})
    assert (r.status_code, codigo(r)) == (413, "adjunto_muy_grande")


async def test_si_falla_un_adjunto_la_hoja_se_conserva_se_registra_en_el_log_y_se_indica(
    anonimo: AsyncClient,
    sql: Ejecutar,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    intentos: list[str] = []
    original = modulo_router.AlmacenStorage.subir

    async def falla_en_la_segunda(self: Any, ruta: str, contenido: bytes, mime: str) -> None:
        intentos.append(ruta)
        if len(intentos) == 2:
            raise AlmacenamientoNoDisponible("storage caido")
        await original(self, ruta, contenido, mime)

    monkeypatch.setattr(modulo_router.AlmacenStorage, "subir", falla_en_la_segunda)
    cuerpo = datos()
    with caplog.at_level("ERROR"):
        r = await enviar(
            anonimo, cuerpo, [("a.png", PNG, "image/png"), ("b.png", PNG, "image/png")]
        )
    assert r.status_code == 201, r.text
    hoja = r.json()
    assert hoja["adjuntos_no_guardados"] == [2]
    assert [a["n"] for a in hoja["adjuntos"]] == [1]
    assert hojas_de(sql, cuerpo["consumidor"]["correo"]) == 1
    assert sql(
        "select n from public.adjunto_reclamacion where id_hoja = %s order by n", hoja["id"]
    ) == [(1,)]
    assert sql("select n from public.subida_reclamacion where id_hoja = %s", hoja["id"]) == [(2,)]
    assert f"El adjunto 2 de la hoja {hoja['id']} no se guardo" in caplog.text


async def test_storage_no_admite_subidas_libres_ni_repetidas_con_la_clave_publicable(
    configuracion: Configuracion,
    anonimo: AsyncClient,
    sql: Ejecutar,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    almacen = modulo_router.AlmacenStorage(
        configuracion.url_supabase, configuracion.clave_publicable_supabase
    )
    subir = modulo_router.AlmacenStorage.subir  # la real, antes de apagarla para el backend
    libre = f"{uuid.uuid4()}/{uuid.uuid4()}.png"
    with pytest.raises(AlmacenamientoNoDisponible):
        await subir(almacen, libre, PNG, "image/png")
    assert sql("select count(*) from storage.objects where name = %s", libre) == [(0,)]

    async def no_sube(self: Any, ruta: str, contenido: bytes, mime: str) -> None:
        raise AlmacenamientoNoDisponible("el backend no sube")

    monkeypatch.setattr(modulo_router.AlmacenStorage, "subir", no_sube)
    r = await enviar(anonimo, datos(), [("a.png", PNG, "image/png")])  # deja una subida pendiente
    assert r.json()["adjuntos_no_guardados"] == [1]
    (ruta,) = sql("select ruta from public.subida_reclamacion where id_hoja = %s", r.json()["id"])[
        0
    ]
    await subir(almacen, ruta, PNG, "image/png")  # la ruta pendiente si admite un objeto
    with pytest.raises(AlmacenamientoNoDisponible):
        await subir(almacen, ruta, PNG, "image/png")  # pero solo uno
    sql("update public.subida_reclamacion set caduca_en = now() - interval '1 minute'")
    otra = (await enviar(anonimo, datos(), [("b.png", PNG, "image/png")])).json()
    (caducada,) = sql("select ruta from public.subida_reclamacion where id_hoja = %s", otra["id"])[
        0
    ]
    sql(
        "update public.subida_reclamacion set caduca_en = now() - interval '1 minute' where ruta = %s",
        caducada,
    )
    with pytest.raises(AlmacenamientoNoDisponible):
        await subir(almacen, caducada, PNG, "image/png")  # ni tras caducar


# --- limite por IP y concurrencia -------------------------------------------------------------


async def test_la_sexta_hoja_de_la_misma_ip_en_una_hora_es_429(
    anonimo: AsyncClient, sql: Ejecutar
) -> None:
    for _ in range(5):
        assert (await enviar(anonimo, datos())).status_code == 201
    cuerpo = datos()
    r = await enviar(anonimo, cuerpo)
    assert (r.status_code, codigo(r)) == (429, "demasiadas_solicitudes")
    assert hojas_de(sql, cuerpo["consumidor"]["correo"]) == 0


async def test_otra_ip_no_se_ve_afectada(
    app: Any, anonimo: AsyncClient, ips_usadas: list[str]
) -> None:
    from httpx import ASGITransport

    for _ in range(5):
        await enviar(anonimo, datos())
    ips_usadas.append("172.31.9.9")
    async with AsyncClient(
        transport=ASGITransport(app=app, client=("172.31.9.9", 1)), base_url="http://t"
    ) as otro:
        assert (await enviar(otro, datos())).status_code == 201


async def test_dos_altas_simultaneas_no_repiten_numero(app: Any, ips_usadas: list[str]) -> None:
    from httpx import ASGITransport

    async def alta(i: int) -> Any:
        ip = f"172.30.1.{i}"
        ips_usadas.append(ip)
        async with AsyncClient(
            transport=ASGITransport(app=app, client=(ip, 1)), base_url="http://t"
        ) as c:
            return await enviar(c, datos())

    respuestas = await asyncio.gather(*(alta(i) for i in range(1, 9)))
    assert all(r.status_code == 201 for r in respuestas), [r.text for r in respuestas]
    numeros = [r.json()["numero"] for r in respuestas]
    assert len(set(numeros)) == 8


# --- sesion invalida y errores ---------------------------------------------------------------


def _alg_cambiado(usuario: UsuarioDePrueba) -> str:
    cabecera, carga, firma = usuario.token.split(".")
    h = json.loads(base64.urlsafe_b64decode(cabecera + "=="))
    h["alg"] = "HS256"
    falsa = base64.urlsafe_b64encode(json.dumps(h).encode()).rstrip(b"=").decode()
    return f"{falsa}.{carga}.{firma}"


@pytest.mark.parametrize("token", ["basura", "a.b.c"])
async def test_un_token_invalido_en_el_alta_se_trata_como_sin_sesion(
    anonimo: AsyncClient, sql: Ejecutar, token: str
) -> None:
    r = await enviar(anonimo, datos(), cabeceras={"Authorization": f"Bearer {token}"})
    assert r.status_code == 201, r.text
    assert sql("select id_cuenta from public.hoja_reclamacion where id = %s", r.json()["id"]) == [
        (None,)
    ]


async def test_un_token_con_alg_cambiado_en_el_alta_es_sin_sesion(
    anonimo: AsyncClient, cliente_a: UsuarioDePrueba, sql: Ejecutar
) -> None:
    r = await enviar(
        anonimo, datos(), cabeceras={"Authorization": f"Bearer {_alg_cambiado(cliente_a)}"}
    )
    assert r.status_code == 201, r.text
    assert sql("select id_cuenta from public.hoja_reclamacion where id = %s", r.json()["id"]) == [
        (None,)
    ]


@pytest.mark.parametrize(
    ("metodo", "ruta"),
    [
        ("GET", f"{HOJAS}/mias"),
        ("GET", f"{HOJAS}"),
        ("GET", f"{HOJAS}/00000000-0000-0000-0000-000000000001"),
        ("POST", f"{HOJAS}/00000000-0000-0000-0000-000000000001/respuesta"),
        ("POST", f"{HOJAS}/transcripcion"),
        ("GET", f"{HOJAS}/00000000-0000-0000-0000-000000000001/adjuntos/1"),
        ("GET", f"{HOJAS}/exportar?desde=2026-01-01&hasta=2026-12-31"),
    ],
)
async def test_las_rutas_autenticadas_dan_401_sin_token_o_con_alg_cambiado(
    anonimo: AsyncClient, cliente_a: UsuarioDePrueba, metodo: str, ruta: str
) -> None:
    for cabeceras in (None, {"Authorization": f"Bearer {_alg_cambiado(cliente_a)}"}):
        r = await anonimo.request(metodo, ruta, headers=cabeceras)
        assert (r.status_code, codigo(r)) == (401, "no_autenticado"), (metodo, ruta, cabeceras)


async def test_base_caida_en_el_alta_es_503(monkeypatch: pytest.MonkeyPatch) -> None:
    from httpx import ASGITransport

    from bugalu.compartido.configuracion import obtener_configuracion
    from bugalu.main import crear_app

    monkeypatch.setenv("URL_BASE_DATOS", "postgresql://u:p@127.0.0.1:1/db")
    monkeypatch.setenv("TIMEOUT_POOL_SEGUNDOS", "0.5")
    obtener_configuracion.cache_clear()
    app = crear_app()
    async with app.router.lifespan_context(app):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
            r = await enviar(c, datos())
    assert (r.status_code, codigo(r)) == (503, "base_de_datos_no_disponible")


# --- clave de envio (precision 11) ---------------------------------------------------------------


async def test_un_reintento_con_la_misma_clave_devuelve_200_con_la_misma_hoja(
    anonimo: AsyncClient, administrador: UsuarioDePrueba, sql: Ejecutar
) -> None:
    clave = str(uuid.uuid4())
    cuerpo = datos(clave_envio=clave)
    adjuntos = [("a.png", PNG, "image/png")]
    primera = await enviar(anonimo, cuerpo, adjuntos)
    assert primera.status_code == 201, primera.text
    segunda = await enviar(anonimo, cuerpo, adjuntos)
    assert segunda.status_code == 200, segunda.text
    assert segunda.json() == primera.json() | {"revisar_spam": None} | {
        k: segunda.json()[k] for k in ("dias_habiles_restantes",)
    }
    assert hojas_de(sql, cuerpo["consumidor"]["correo"]) == 1
    assert segunda.json()["adjuntos_no_guardados"] == []
    avisos = dict(
        sql(
            "select tipo, count(*) from public.notificacion where datos ->> 'id' = %s group by 1",
            primera.json()["id"],
        )
    )
    administradores = sql("select count(*) from public.usuario where rol = 'administrador'")[0][0]
    assert avisos == {"reclamacion_registrada": 1, "reclamacion_recibida": administradores}
    assert sql(
        "select count(*) from storage.objects where bucket_id = 'reclamaciones' "
        "and (storage.foldername(name))[1] = %s",
        primera.json()["id"],
    ) == [(1,)]


async def test_sin_clave_o_con_otra_clave_son_hojas_distintas(
    anonimo: AsyncClient, sql: Ejecutar
) -> None:
    cuerpo = datos()
    assert (await enviar(anonimo, cuerpo)).status_code == 201
    assert (await enviar(anonimo, cuerpo)).status_code == 201
    assert (await enviar(anonimo, datos(clave_envio=str(uuid.uuid4())))).status_code == 201
    assert hojas_de(sql, cuerpo["consumidor"]["correo"]) == 2


async def test_dos_altas_simultaneas_con_la_misma_clave_dejan_una_hoja(
    app: Any, ips_usadas: list[str], sql: Ejecutar
) -> None:
    from httpx import ASGITransport

    cuerpo = datos(clave_envio=str(uuid.uuid4()))

    async def alta(i: int) -> Any:
        ip = f"172.29.1.{i}"
        ips_usadas.append(ip)
        transporte = ASGITransport(app=app, client=(ip, 1))
        async with AsyncClient(transport=transporte, base_url="http://t") as c:
            return await enviar(c, cuerpo)

    rs = await asyncio.gather(alta(1), alta(2))
    assert sorted(r.status_code for r in rs) == [200, 201], [r.text for r in rs]
    assert rs[0].json()["id"] == rs[1].json()["id"]
    assert hojas_de(sql, cuerpo["consumidor"]["correo"]) == 1


async def test_una_clave_que_no_es_uuid_es_422(anonimo: AsyncClient) -> None:
    r = await enviar(anonimo, datos(clave_envio="123"))
    assert (r.status_code, r.json()["error"]["detalles"]["campo"]) == (422, "clave_envio")


# --- en_tu_cuenta (precision 12) --------------------------------------------------------------------


async def test_en_tu_cuenta_depende_del_token_de_cada_peticion(
    anonimo: AsyncClient,
    administrador: UsuarioDePrueba,
    cliente_a: UsuarioDePrueba,
    cliente_b: UsuarioDePrueba,
    sql: Ejecutar,
) -> None:
    sin_token = await enviar(anonimo, datos())
    assert sin_token.json()["en_tu_cuenta"] is False
    propia = await enviar(anonimo, datos(), usuario=cliente_a)
    assert propia.json()["en_tu_cuenta"] is True
    id_ = propia.json()["id"]
    visto = {
        u.id: (await anonimo.get(f"{HOJAS}/{id_}", headers=con(u))).json()
        for u in (cliente_a, administrador)
    }
    assert visto[cliente_a.id]["en_tu_cuenta"] is True
    assert visto[administrador.id]["en_tu_cuenta"] is False  # la ve, pero no es suya


async def test_el_reenvio_con_la_misma_clave_no_vincula_la_hoja_a_posteriori(
    anonimo: AsyncClient, cliente_a: UsuarioDePrueba, cliente_b: UsuarioDePrueba, sql: Ejecutar
) -> None:
    cuerpo = datos(clave_envio=str(uuid.uuid4()))
    creada = await enviar(anonimo, cuerpo)  # sin token
    assert (creada.status_code, creada.json()["en_tu_cuenta"]) == (201, False)
    reenvio = await enviar(anonimo, cuerpo, usuario=cliente_a)  # ahora con token
    assert (reenvio.status_code, reenvio.json()["en_tu_cuenta"]) == (200, False)
    assert sql(
        "select id_cuenta from public.hoja_reclamacion where id = %s", creada.json()["id"]
    ) == [(None,)]
    propia = datos(clave_envio=str(uuid.uuid4()))
    assert (await enviar(anonimo, propia, usuario=cliente_a)).json()["en_tu_cuenta"] is True
    mismo = await enviar(anonimo, propia, usuario=cliente_a)
    ajeno = await enviar(anonimo, propia, usuario=cliente_b)
    sin = await enviar(anonimo, propia)
    assert [r.json()["en_tu_cuenta"] for r in (mismo, ajeno, sin)] == [True, False, False]


# --- la clave de envio solo reintenta con los mismos datos (auditoria A) ----------------------------------


def _otro(cuerpo: dict[str, Any], campo: str) -> dict[str, Any]:
    """Una copia con un solo campo distinto."""
    nuevo = json.loads(json.dumps(cuerpo))
    if campo == "documento":
        nuevo["consumidor"]["documento"] = "87654321"
    elif campo == "correo":
        nuevo["consumidor"]["correo"] = f"{uuid.uuid4().hex}@prueba.bugalu.pe"
    else:
        nuevo[campo] = "Otro texto distinto del primero."
    return nuevo


@pytest.mark.parametrize("campo", ["documento", "correo", "detalle", "pedido"])
async def test_la_misma_clave_con_otros_datos_registra_una_hoja_nueva_sin_datos_ajenos(
    anonimo: AsyncClient, sql: Ejecutar, campo: str
) -> None:
    clave = str(uuid.uuid4())
    primera_peticion = datos(clave_envio=clave)
    primera = await enviar(anonimo, primera_peticion)
    assert primera.status_code == 201, primera.text
    peticion = _otro(primera_peticion, campo)
    r = await enviar(anonimo, peticion)
    assert r.status_code == 201, r.text
    assert r.json()["id"] != primera.json()["id"]
    assert r.json()["consumidor"]["documento"] == peticion["consumidor"]["documento"]
    assert r.json()["consumidor"]["correo"] == peticion["consumidor"]["correo"]
    assert (r.json()["detalle"], r.json()["pedido"]) == (peticion["detalle"], peticion["pedido"])
    assert sql("select count(*) from public.hoja_reclamacion where id = %s", r.json()["id"]) == [
        (1,)
    ]


async def test_el_reintento_devuelve_el_estado_y_la_respuesta_reales_de_la_hoja(
    anonimo: AsyncClient, administrador: UsuarioDePrueba
) -> None:
    cuerpo = datos(clave_envio=str(uuid.uuid4()))
    creada = await enviar(anonimo, cuerpo)
    assert (creada.status_code, creada.json()["estado"]) == (201, "pendiente")
    resp = await anonimo.post(
        f"{HOJAS}/{creada.json()['id']}/respuesta",
        json={"texto": "Respuesta del estudio."},
        headers=con(administrador),
    )
    assert resp.status_code == 200, resp.text
    reintento = await enviar(anonimo, cuerpo)
    assert reintento.status_code == 200, reintento.text
    hoja = reintento.json()
    assert (hoja["estado"], hoja["dias_habiles_restantes"]) == ("respondida", None)
    assert hoja["respuesta"]["texto"] == "Respuesta del estudio."
    assert hoja["respuesta"]["respondida_por"] is None  # el autor es del Administrador
    assert hoja["respuesta"]["medio"] == "correo"


# --- la IP del limite viene del proxy de confianza y de nadie mas (auditoria A) -----------------------------


async def _ip_vista_por_uvicorn(
    app: Any, confiables: str, ips_usadas: list[str], sql: Ejecutar
) -> str | None:
    """Un uvicorn real en 127.0.0.1 con `--forwarded-allow-ips`, y una alta que dice venir de 198.51.100.7."""
    import uvicorn

    servidor = uvicorn.Server(
        uvicorn.Config(
            app,
            host="127.0.0.1",
            port=0,
            forwarded_allow_ips=confiables,
            lifespan="off",
            log_level="error",
        )
    )
    tarea = asyncio.create_task(servidor.serve())
    while not servidor.started:
        await asyncio.sleep(0.02)
    puerto = servidor.servers[0].sockets[0].getsockname()[1]
    reenviada = "198.51.100.7"
    ips_usadas += [reenviada, "127.0.0.1"]
    try:
        async with AsyncClient(base_url=f"http://127.0.0.1:{puerto}") as c:
            r = await enviar(c, datos(), cabeceras={"X-Forwarded-For": reenviada})
        assert r.status_code == 201, r.text
    finally:
        servidor.should_exit = True
        await tarea
    hashes = {
        f[0]
        for f in sql(
            "select ip_hash from public.intento_reclamacion where ip_hash = any(%s)",
            [hashlib.sha256(i.encode()).hexdigest() for i in (reenviada, "127.0.0.1")],
        )
    }
    return next(
        (i for i in (reenviada, "127.0.0.1") if hashlib.sha256(i.encode()).hexdigest() in hashes),
        None,
    )


async def test_el_limite_usa_la_ip_reenviada_solo_si_el_proxy_es_de_confianza(
    app: Any, ips_usadas: list[str], sql: Ejecutar
) -> None:
    assert await _ip_vista_por_uvicorn(app, "127.0.0.1", ips_usadas, sql) == "198.51.100.7"
    sql(
        "delete from public.intento_reclamacion where ip_hash = any(%s)",
        [hashlib.sha256(i.encode()).hexdigest() for i in ("198.51.100.7", "127.0.0.1")],
    )
    # quien no es el proxy de confianza no puede elegir su IP con una cabecera
    assert await _ip_vista_por_uvicorn(app, "10.9.9.9", ips_usadas, sql) == "127.0.0.1"
