# ruff: noqa: E501, F811 - SQL literal y fixtures compartidas
"""Consulta, bandeja, respuesta unica, transcripcion, adjuntos firmados y CSV (Administrador y dueno)."""

import csv
import io
from datetime import UTC, datetime, timedelta
from typing import Any

import httpx
import pytest
from httpx import AsyncClient

from tests.conftest import UsuarioDePrueba
from tests.modulos.reclamaciones.infraestructura.conftest import (
    HOJAS,
    PNG,
    datos,
    enviar,
)
from tests.modulos.reservas.infraestructura.conftest import Ejecutar, con

pytestmark = pytest.mark.integracion


def codigo(r: Any) -> str:
    return str(r.json()["error"]["codigo"])


async def registrar(
    cliente: AsyncClient, usuario: UsuarioDePrueba | None = None, **cambios: Any
) -> dict[str, Any]:
    r = await enviar(cliente, datos(**cambios), usuario=usuario)
    assert r.status_code == 201, r.text
    hoja: dict[str, Any] = r.json()
    return hoja


# --- bandeja ---------------------------------------------------------------------------------


async def test_la_bandeja_es_del_administrador_con_dias_y_marca_de_spam(
    anonimo: AsyncClient, administrador: UsuarioDePrueba, cliente_a: UsuarioDePrueba
) -> None:
    hoja = await registrar(anonimo, sitio_web="x")
    r = await anonimo.get(HOJAS, headers=con(administrador))
    assert r.status_code == 200
    fila = next(h for h in r.json() if h["id"] == hoja["id"])
    assert fila["estado"] == "pendiente"
    assert fila["consumidor"] == {"nombre": "Ana Prueba"}
    assert fila["revisar_spam"] is True
    assert fila["origen"] == "web"
    assert fila["dias_habiles_restantes"] in (14, 15)
    prohibida = await anonimo.get(HOJAS, headers=con(cliente_a))
    assert (prohibida.status_code, codigo(prohibida)) == (403, "sin_permiso")


async def test_la_bandeja_pone_las_pendientes_primero_por_plazo_y_filtra(
    anonimo: AsyncClient, administrador: UsuarioDePrueba, sql: Ejecutar
) -> None:
    a, b, c = [await registrar(anonimo) for _ in range(3)]
    sql("alter table public.hoja_reclamacion disable trigger user")
    try:
        sql(
            "update public.hoja_reclamacion set vence_respuesta = vence_respuesta + interval '10 days' where id = %s",
            a["id"],
        )
        sql(
            "update public.hoja_reclamacion set vence_respuesta = vence_respuesta + interval '5 days' where id = %s",
            b["id"],
        )
    finally:
        sql("alter table public.hoja_reclamacion enable trigger user")
    # c (la mas proxima), b, a; luego la respondida
    resp = await anonimo.post(
        f"{HOJAS}/{a['id']}/respuesta",
        json={"texto": "Respuesta de prueba"},
        headers=con(administrador),
    )
    assert resp.status_code == 200, resp.text
    ids = {a["id"], b["id"], c["id"]}
    lista = [
        h["id"]
        for h in (await anonimo.get(HOJAS, headers=con(administrador))).json()
        if h["id"] in ids
    ]
    assert lista == [c["id"], b["id"], a["id"]]
    pendientes = (await anonimo.get(f"{HOJAS}?estado=pendiente", headers=con(administrador))).json()
    assert {h["id"] for h in pendientes} >= {b["id"], c["id"]} and a["id"] not in {
        h["id"] for h in pendientes
    }
    respondidas = (
        await anonimo.get(f"{HOJAS}?estado=respondida", headers=con(administrador))
    ).json()
    assert a["id"] in {h["id"] for h in respondidas}
    hoy = sql("select (now() at time zone 'America/Lima')::date::text")[0][0]
    rango = await anonimo.get(f"{HOJAS}?desde={hoy}&hasta={hoy}", headers=con(administrador))
    assert ids <= {h["id"] for h in rango.json()}
    vacio = await anonimo.get(
        f"{HOJAS}?desde=2001-01-01&hasta=2001-01-02", headers=con(administrador)
    )
    assert vacio.json() == []


@pytest.mark.parametrize(
    "consulta",
    ["?estado=otro", "?desde=ayer", "?desde=2026-02-01&hasta=2026-01-01"],
)
async def test_la_bandeja_valida_sus_filtros(
    anonimo: AsyncClient, administrador: UsuarioDePrueba, consulta: str
) -> None:
    r = await anonimo.get(f"{HOJAS}{consulta}", headers=con(administrador))
    assert r.status_code == 422, r.text


async def test_una_hoja_ajena_o_inexistente_es_404_y_el_administrador_ve_todo(
    anonimo: AsyncClient, administrador: UsuarioDePrueba
) -> None:
    hoja = await registrar(anonimo)
    ver = await anonimo.get(f"{HOJAS}/{hoja['id']}", headers=con(administrador))
    assert ver.status_code == 200
    assert ver.json()["consumidor"]["documento"] == "12345678"
    nada = await anonimo.get(
        f"{HOJAS}/00000000-0000-0000-0000-000000000001", headers=con(administrador)
    )
    assert (nada.status_code, codigo(nada)) == (404, "no_encontrado")
    assert (await anonimo.get(f"{HOJAS}/no-es-uuid", headers=con(administrador))).status_code == 422


# --- respuesta unica ---------------------------------------------------------------------------


async def test_el_administrador_responde_una_vez_y_el_cliente_ve_la_respuesta_sin_el_autor(
    anonimo: AsyncClient,
    administrador: UsuarioDePrueba,
    cliente_a: UsuarioDePrueba,
    sql: Ejecutar,
) -> None:
    hoja = await registrar(anonimo, cliente_a)
    r = await anonimo.post(
        f"{HOJAS}/{hoja['id']}/respuesta",
        json={"texto": "Revisamos tu caso y lo resolvimos."},
        headers=con(administrador),
    )
    assert r.status_code == 200, r.text
    resp = r.json()
    assert resp["estado"] == "respondida"
    assert resp["dias_habiles_restantes"] is None
    assert resp["respuesta"]["texto"] == "Revisamos tu caso y lo resolvimos."
    assert resp["respuesta"]["medio"] == "correo"
    assert resp["respuesta"]["enviada_en"]
    assert resp["respuesta"]["respondida_por"]["id"] == str(administrador.id)
    # medio correo: aviso al consumidor con la respuesta
    avisos = sql(
        "select tipo from public.notificacion where datos ->> 'id' = %s and tipo = 'reclamacion_respondida'",
        hoja["id"],
    )
    assert avisos == [("reclamacion_respondida",)]
    # el dueno la ve, sin saber quien respondio; el administrador si
    propia = (await anonimo.get(f"{HOJAS}/{hoja['id']}", headers=con(cliente_a))).json()
    assert propia["respuesta"]["texto"] == "Revisamos tu caso y lo resolvimos."
    assert propia["respuesta"].get("respondida_por") is None
    assert propia["revisar_spam"] is None
    # una sola vez
    otra = await anonimo.post(
        f"{HOJAS}/{hoja['id']}/respuesta",
        json={"texto": "Otra respuesta distinta"},
        headers=con(administrador),
    )
    assert (otra.status_code, codigo(otra)) == (409, "ya_respondida")
    assert sql("select respuesta_texto from public.hoja_reclamacion where id = %s", hoja["id"]) == [
        ("Revisamos tu caso y lo resolvimos.",)
    ]


async def test_dos_respuestas_simultaneas_solo_dejan_una(
    anonimo: AsyncClient, administrador: UsuarioDePrueba
) -> None:
    import asyncio

    hoja = await registrar(anonimo)
    rs = await asyncio.gather(
        *(
            anonimo.post(
                f"{HOJAS}/{hoja['id']}/respuesta",
                json={"texto": f"Respuesta numero {i} larga"},
                headers=con(administrador),
            )
            for i in range(2)
        )
    )
    assert sorted(r.status_code for r in rs) == [200, 409]


async def test_con_medio_carta_exige_referencia_y_fecha_y_no_envia_correo(
    anonimo: AsyncClient, administrador: UsuarioDePrueba, sql: Ejecutar
) -> None:
    hoja = await registrar(anonimo, medio_respuesta="carta")
    url = f"{HOJAS}/{hoja['id']}/respuesta"
    for cuerpo in (
        {"texto": "Respuesta por carta"},
        {"texto": "Respuesta por carta", "referencia_carta": "CARTA-1"},
        {"texto": "Respuesta por carta", "enviada_en": "2026-11-18T10:00:00-05:00"},
    ):
        r = await anonimo.post(url, json=cuerpo, headers=con(administrador))
        assert (r.status_code, codigo(r)) == (422, "datos_invalidos"), cuerpo
    ok = await anonimo.post(
        url,
        json={
            "texto": "Respuesta por carta",
            "referencia_carta": "CARTA-1",
            "enviada_en": "2026-11-18T10:00:00-05:00",
        },
        headers=con(administrador),
    )
    assert ok.status_code == 200, ok.text
    assert ok.json()["respuesta"]["referencia_carta"] == "CARTA-1"
    assert datetime.fromisoformat(ok.json()["respuesta"]["enviada_en"]) == datetime.fromisoformat(
        "2026-11-18T10:00:00-05:00"
    )
    assert sql(
        "select count(*) from public.notificacion where tipo = 'reclamacion_respondida' and datos ->> 'id' = %s",
        hoja["id"],
    ) == [(0,)]


@pytest.mark.parametrize("texto", ["corto", "x" * 5001, "con\x00nulo larga"])
async def test_el_texto_de_la_respuesta_tiene_de_10_a_5000(
    anonimo: AsyncClient, administrador: UsuarioDePrueba, texto: str
) -> None:
    hoja = await registrar(anonimo)
    r = await anonimo.post(
        f"{HOJAS}/{hoja['id']}/respuesta", json={"texto": texto}, headers=con(administrador)
    )
    assert (r.status_code, codigo(r)) == (422, "datos_invalidos")


async def test_solo_el_administrador_responde_y_la_hoja_debe_existir(
    anonimo: AsyncClient, administrador: UsuarioDePrueba, cliente_a: UsuarioDePrueba, sql: Ejecutar
) -> None:
    hoja = await registrar(anonimo, cliente_a)
    r = await anonimo.post(
        f"{HOJAS}/{hoja['id']}/respuesta",
        json={"texto": "Me respondo a mi mismo"},
        headers=con(cliente_a),
    )
    assert (r.status_code, codigo(r)) == (403, "sin_permiso")
    assert sql("select respuesta_texto from public.hoja_reclamacion where id = %s", hoja["id"]) == [
        (None,)
    ]
    nada = await anonimo.post(
        f"{HOJAS}/00000000-0000-0000-0000-000000000001/respuesta",
        json={"texto": "Respuesta larga"},
        headers=con(administrador),
    )
    assert (nada.status_code, codigo(nada)) == (404, "no_encontrado")


# --- transcripcion -----------------------------------------------------------------------------


async def test_el_administrador_transcribe_una_hoja_del_libro_fisico(
    anonimo: AsyncClient, administrador: UsuarioDePrueba, sql: Ejecutar
) -> None:
    original = (datetime.now(UTC) - timedelta(days=30)).replace(microsecond=0)
    cuerpo = datos(tipo=None, fecha_original=original.isoformat(), numero_hoja_fisica="FIS-0042")
    r = await enviar(
        anonimo,
        cuerpo,
        [("foto-hoja.png", PNG, "image/png")],
        administrador,
        f"{HOJAS}/transcripcion",
    )
    assert r.status_code == 201, r.text
    hoja = r.json()
    assert (hoja["origen"], hoja["numero_hoja_fisica"], hoja["tipo"]) == (
        "libro_fisico",
        "FIS-0042",
        None,
    )
    assert datetime.fromisoformat(hoja["fecha_original"]) == original
    assert hoja["revisar_spam"] is False
    assert len(hoja["adjuntos"]) == 1
    # el plazo cuenta desde la fecha original (15 dias habiles)
    esperado = sql(
        "select to_char(public.sumar_dias_habiles(%s::timestamptz, 15) at time zone 'America/Lima', 'YYYY-MM-DD')",
        original.isoformat(),
    )[0][0]
    assert sql(
        "select to_char(vence_respuesta at time zone 'America/Lima', 'YYYY-MM-DD') from public.hoja_reclamacion where id = %s",
        hoja["id"],
    ) == [(esperado,)]
    assert hoja["dias_habiles_restantes"] < 0
    # copia al consumidor (tiene correo) y ningun aviso al administrador
    tipos = {
        f[0]
        for f in sql("select tipo from public.notificacion where datos ->> 'id' = %s", hoja["id"])
    }
    assert tipos == {"reclamacion_registrada"}


async def test_solo_el_administrador_transcribe_y_la_fecha_no_es_futura(
    anonimo: AsyncClient, administrador: UsuarioDePrueba, cliente_a: UsuarioDePrueba, sql: Ejecutar
) -> None:
    reciente = (datetime.now(UTC) - timedelta(days=10)).isoformat()
    base = {"fecha_original": reciente, "numero_hoja_fisica": "FIS-1"}
    r = await enviar(anonimo, datos(**base), None, cliente_a, f"{HOJAS}/transcripcion")
    assert (r.status_code, codigo(r)) == (403, "sin_permiso")
    futura = datos(fecha_original="2999-01-01T10:00:00-05:00", numero_hoja_fisica="FIS-2")
    r = await enviar(anonimo, futura, None, administrador, f"{HOJAS}/transcripcion")
    assert (r.status_code, codigo(r)) == (422, "fecha_original_invalida")
    assert r.json()["error"]["detalles"]["campo"] == "fecha_original"
    sin_fecha = datos(numero_hoja_fisica="FIS-3")
    r = await enviar(anonimo, sin_fecha, None, administrador, f"{HOJAS}/transcripcion")
    assert (r.status_code, r.json()["error"]["detalles"]["campo"]) == (422, "fecha_original")
    no_confirmada = datos(confirmado=False, **base)
    r = await enviar(anonimo, no_confirmada, None, administrador, f"{HOJAS}/transcripcion")
    assert (r.status_code, codigo(r)) == (409, "confirmacion_requerida")
    assert sql(
        "select count(*) from public.hoja_reclamacion where numero_hoja_fisica like 'FIS-%%' and correo like '%%@prueba.bugalu.pe'"
    ) == [(0,)]


@pytest.mark.parametrize(
    "antigua",
    [(datetime.now(UTC) - timedelta(days=91)).isoformat(), "0026-03-01T10:00:00-05:00"],
    ids=["hace_91_dias", "del_anio_26"],
)
async def test_la_fecha_original_no_puede_ser_de_hace_mas_de_90_dias(
    anonimo: AsyncClient, administrador: UsuarioDePrueba, sql: Ejecutar, antigua: str
) -> None:
    cuerpo = datos(tipo=None, fecha_original=antigua, numero_hoja_fisica="FIS-OLD")
    r = await enviar(anonimo, cuerpo, None, administrador, f"{HOJAS}/transcripcion")
    assert (r.status_code, codigo(r)) == (422, "fecha_original_invalida")
    assert r.json()["error"]["detalles"] == {"campo": "fecha_original"}
    assert sql(
        "select count(*) from public.hoja_reclamacion where correo = %s",
        cuerpo["consumidor"]["correo"],
    ) == [(0,)]


# --- adjuntos por URL firmada ---------------------------------------------------------------------


async def test_el_administrador_obtiene_una_url_firmada_y_baja_el_archivo(
    anonimo: AsyncClient, administrador: UsuarioDePrueba, cliente_a: UsuarioDePrueba
) -> None:
    r = await enviar(anonimo, datos(), [("a.png", PNG, "image/png")], cliente_a)
    hoja = r.json()
    url = f"{HOJAS}/{hoja['id']}/adjuntos/1"
    firmada = await anonimo.get(url, headers=con(administrador))
    assert firmada.status_code == 200, firmada.text
    assert set(firmada.json()) == {"url", "expira_en"}
    archivo = httpx.get(firmada.json()["url"], timeout=10)
    assert (archivo.status_code, archivo.content) == (200, PNG)
    # ni el dueno ni otro cliente: solo el Administrador baja adjuntos
    ajeno = await anonimo.get(url, headers=con(cliente_a))
    assert (ajeno.status_code, codigo(ajeno)) == (403, "sin_permiso")
    inexistente = await anonimo.get(f"{HOJAS}/{hoja['id']}/adjuntos/2", headers=con(administrador))
    assert (inexistente.status_code, codigo(inexistente)) == (404, "no_encontrado")
    assert (
        await anonimo.get(f"{HOJAS}/{hoja['id']}/adjuntos/0", headers=con(administrador))
    ).status_code == 422


async def test_el_bucket_no_se_lee_sin_firma(
    configuracion: Any, anonimo: AsyncClient, administrador: UsuarioDePrueba, sql: Ejecutar
) -> None:
    hoja = (await enviar(anonimo, datos(), [("a.png", PNG, "image/png")])).json()
    ruta = sql("select ruta from public.adjunto_reclamacion where id_hoja = %s", hoja["id"])[0][0]
    abierta = httpx.get(
        f"{configuracion.url_supabase}/storage/v1/object/public/reclamaciones/{ruta}",
        headers={"apikey": configuracion.clave_publicable_supabase},
    )
    assert abierta.status_code in (400, 404)
    anon = httpx.get(
        f"{configuracion.url_supabase}/storage/v1/object/reclamaciones/{ruta}",
        headers={"apikey": configuracion.clave_publicable_supabase},
    )
    assert anon.status_code in (400, 401, 403, 404)


# --- exportacion CSV -----------------------------------------------------------------------------


async def test_el_csv_trae_todas_las_columnas_la_respuesta_y_neutraliza_formulas(
    anonimo: AsyncClient, administrador: UsuarioDePrueba, sql: Ejecutar
) -> None:
    cuerpo = datos()
    cuerpo["consumidor"]["nombre"] = '=HYPERLINK("http://malo.example","clic")'
    hoja = (await enviar(anonimo, cuerpo, [("a.png", PNG, "image/png")])).json()
    await anonimo.post(
        f"{HOJAS}/{hoja['id']}/respuesta",
        json={"texto": "Respuesta para Indecopi"},
        headers=con(administrador),
    )
    hoy = sql("select (now() at time zone 'America/Lima')::date::text")[0][0]
    r = await anonimo.get(f"{HOJAS}/exportar?desde={hoy}&hasta={hoy}", headers=con(administrador))
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("text/csv")
    assert "attachment" in r.headers["content-disposition"]
    filas = list(csv.DictReader(io.StringIO(r.content.decode("utf-8-sig"))))
    fila = next(f for f in filas if f["numero"] == hoja["numero"])
    assert fila["nombre"] == "'" + cuerpo["consumidor"]["nombre"]
    assert fila["respuesta_texto"] == "Respuesta para Indecopi"
    assert (fila["estado"], fila["adjuntos"], fila["origen"], fila["medio_respuesta"]) == (
        "respondida",
        "1",
        "web",
        "correo",
    )
    assert fila["detalle"] == cuerpo["detalle"]
    assert fila["respondida_por"]


async def test_el_csv_valida_el_rango_y_es_solo_del_administrador(
    anonimo: AsyncClient, administrador: UsuarioDePrueba, cliente_a: UsuarioDePrueba
) -> None:
    mal = await anonimo.get(
        f"{HOJAS}/exportar?desde=2026-02-01&hasta=2026-01-01", headers=con(administrador)
    )
    assert (mal.status_code, codigo(mal)) == (422, "rango_invalido")
    falta = await anonimo.get(f"{HOJAS}/exportar?desde=2026-02-01", headers=con(administrador))
    assert falta.status_code == 422
    cliente = await anonimo.get(
        f"{HOJAS}/exportar?desde=2026-01-01&hasta=2026-02-01", headers=con(cliente_a)
    )
    assert (cliente.status_code, codigo(cliente)) == (403, "sin_permiso")
