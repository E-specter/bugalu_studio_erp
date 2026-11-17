"""API de RF-05 (registrar pago con captura y verla): stack local con RLS y Storage reales."""

import asyncio
from collections.abc import Callable
from typing import Any

import httpx
import pytest
from fastapi import FastAPI
from httpx import AsyncClient

from bugalu.compartido.configuracion import Configuracion
from bugalu.modulos.pagos.dominio.captura import LIMITE_BYTES
from bugalu.modulos.pagos.infraestructura.entrada.http import router as modulo_router
from bugalu.modulos.pagos.infraestructura.salida.almacen_storage import AlmacenStorage
from tests.conftest import UsuarioDePrueba
from tests.modulos.pagos.infraestructura.conftest import PDF, PNG, operacion
from tests.modulos.reservas.infraestructura.conftest import Ejecutar, con

pytestmark = pytest.mark.integracion

PAGOS = "/api/v1/pagos"
Cuota = Callable[..., str]


async def pagar(
    cliente: AsyncClient,
    usuario: UsuarioDePrueba | None,
    cuota: str,
    captura: bytes = PNG,
    nombre: str = "captura.png",
    tipo: str = "image/png",
    **campos: str,
) -> Any:
    datos = {
        "id_cuota": cuota,
        "metodo": "yape",
        "monto": "25.00",
        "numero_operacion": operacion(),
        **campos,
    }
    return await cliente.post(
        PAGOS,
        data=datos,
        files={"captura": (nombre, captura, tipo)},
        headers=con(usuario) if usuario else None,
    )


def codigo(r: Any) -> str:
    return str(r.json()["error"]["codigo"])


def objetos(sql: Ejecutar, usuario: UsuarioDePrueba) -> list[str]:
    filas = sql(
        "select name from storage.objects where bucket_id = 'comprobantes' "
        "and (storage.foldername(name))[1] = %s",
        str(usuario.id),
    )
    return [f[0] for f in filas]


def pagos_de(sql: Ejecutar, usuario: UsuarioDePrueba) -> int:
    return int(
        sql("select count(*) from public.comprobante_pago where id_cliente = %s", usuario.id)[0][0]
    )


# --- registrar: exito ----------------------------------------------------------------------------


async def test_registra_un_png_y_el_objeto_queda_en_storage(
    cliente: AsyncClient, cliente_a: UsuarioDePrueba, cuota_de: Cuota, sql: Ejecutar
) -> None:
    cuota = cuota_de(cliente_a)
    r = await pagar(cliente, cliente_a, cuota, numero_operacion="ab-1234")
    assert r.status_code == 201, r.text
    pago = r.json()
    assert pago["estado"] == "pendiente_validacion"
    assert (pago["metodo"], pago["monto"], pago["numero_operacion"]) == ("yape", "25.00", "AB-1234")
    assert pago["monto_coincide"] is True
    assert pago["motivo_rechazo"] is None
    assert pago["validado_en"] is None
    assert pago["cuota"] == {"id": cuota, "hito": "al_reservar", "monto": "25.00"}
    assert pago["reserva"]["folio"].startswith("R-")
    assert pago["reserva"]["estado"] == "confirmada"
    assert "cliente" not in pago
    assert objetos(sql, cliente_a) == [f"{cliente_a.id}/{pago['id']}.png"]


async def test_el_pago_registra_la_version_vigente_de_las_condiciones_sin_recibirla(
    cliente: AsyncClient, cliente_a: UsuarioDePrueba, cuota_de: Cuota, sql: Ejecutar
) -> None:
    r = await pagar(cliente, cliente_a, cuota_de(cliente_a))
    assert r.status_code == 201, r.text
    filas = sql(
        "select tipo, version, id_operacion from public.aceptacion "
        "where id_usuario = %s and contexto = 'pago'",
        cliente_a.id,
    )
    assert [(t, v, str(o)) for t, v, o in filas] == [
        ("condiciones_contratacion", "1.0.0", r.json()["id"])
    ]


async def test_un_pago_rechazado_no_deja_aceptacion(
    cliente: AsyncClient, cliente_a: UsuarioDePrueba, cuota_de: Cuota, sql: Ejecutar
) -> None:
    r = await pagar(cliente, cliente_a, cuota_de(cliente_a), b"no es una imagen")
    assert r.status_code == 422
    assert sql(
        "select count(*) from public.aceptacion where contexto = 'pago' and id_usuario = %s",
        cliente_a.id,
    ) == [(0,)]


async def test_registra_un_pdf_y_un_monto_distinto_no_coincide(
    cliente: AsyncClient, cliente_a: UsuarioDePrueba, cuota_de: Cuota, sql: Ejecutar
) -> None:
    r = await pagar(
        cliente, cliente_a, cuota_de(cliente_a), PDF, "x.pdf", "application/pdf", monto="30"
    )
    assert r.status_code == 201, r.text
    assert r.json()["monto_coincide"] is False
    assert objetos(sql, cliente_a) == [f"{cliente_a.id}/{r.json()['id']}.pdf"]


async def test_acepta_exactamente_cinco_megas(
    cliente: AsyncClient, cliente_a: UsuarioDePrueba, cuota_de: Cuota
) -> None:
    exacto = PNG + b"\0" * (LIMITE_BYTES - len(PNG))
    r = await pagar(cliente, cliente_a, cuota_de(cliente_a), exacto)
    assert r.status_code == 201, r.text


# --- registrar: captura invalida -----------------------------------------------------------------


async def test_un_ejecutable_renombrado_png_es_formato_no_admitido(
    cliente: AsyncClient, cliente_a: UsuarioDePrueba, cuota_de: Cuota, sql: Ejecutar
) -> None:
    r = await pagar(cliente, cliente_a, cuota_de(cliente_a), b"MZ\x90\x00" + b"\0" * 100)
    assert (r.status_code, codigo(r)) == (422, "formato_no_admitido")
    assert (pagos_de(sql, cliente_a), objetos(sql, cliente_a)) == (0, [])


async def test_mas_de_cinco_megas_es_413_sin_500(
    cliente: AsyncClient, cliente_a: UsuarioDePrueba, cuota_de: Cuota, sql: Ejecutar
) -> None:
    grande = PNG + b"\0" * (LIMITE_BYTES + 1 - len(PNG))
    assert len(grande) == LIMITE_BYTES + 1
    r = await pagar(cliente, cliente_a, cuota_de(cliente_a), grande)
    assert (r.status_code, codigo(r)) == (413, "archivo_muy_grande")
    assert (pagos_de(sql, cliente_a), objetos(sql, cliente_a)) == (0, [])


@pytest.mark.parametrize(
    "campo",
    [
        {"monto": "0"},
        {"monto": "-5"},
        {"monto": "10.123"},
        {"monto": "abc"},
        {"monto": "1e3"},
        {"numero_operacion": "AB1"},
        {"numero_operacion": "AB 12"},
        {"metodo": "efectivo"},
        {"id_cuota": "no-es-uuid"},
    ],
)
async def test_campos_invalidos_son_422_datos_invalidos(
    cliente: AsyncClient,
    cliente_a: UsuarioDePrueba,
    cuota_de: Cuota,
    sql: Ejecutar,
    campo: dict[str, str],
) -> None:
    r = await pagar(cliente, cliente_a, cuota_de(cliente_a), **campo)
    assert (r.status_code, codigo(r)) == (422, "datos_invalidos")
    assert r.json()["error"]["detalles"]["campo"] == next(iter(campo))
    assert (pagos_de(sql, cliente_a), objetos(sql, cliente_a)) == (0, [])


async def test_sin_captura_es_422(
    cliente: AsyncClient, cliente_a: UsuarioDePrueba, cuota_de: Cuota
) -> None:
    r = await cliente.post(
        PAGOS,
        data={
            "id_cuota": cuota_de(cliente_a),
            "metodo": "yape",
            "monto": "25",
            "numero_operacion": operacion(),
        },
        headers=con(cliente_a),
    )
    assert (r.status_code, codigo(r)) == (422, "datos_invalidos")


# --- registrar: reglas de negocio ----------------------------------------------------------------


async def test_sin_sesion_es_401(
    cliente: AsyncClient, cliente_a: UsuarioDePrueba, cuota_de: Cuota
) -> None:
    r = await pagar(cliente, None, cuota_de(cliente_a))
    assert (r.status_code, codigo(r)) == (401, "no_autenticado")


async def test_metodo_inactivo_es_422_metodo_no_disponible(
    cliente: AsyncClient, cliente_a: UsuarioDePrueba, cuota_de: Cuota, sql: Ejecutar
) -> None:
    sql("update public.instruccion_pago set activo = false, texto = '' where metodo = 'plin'")
    try:
        r = await pagar(cliente, cliente_a, cuota_de(cliente_a), metodo="plin")
    finally:
        sql(
            "update public.instruccion_pago set activo = true, texto = 'Plin de prueba' "
            "where metodo = 'plin'"
        )
    assert (r.status_code, codigo(r)) == (422, "metodo_no_disponible")
    assert (pagos_de(sql, cliente_a), objetos(sql, cliente_a)) == (0, [])


async def test_cuota_ajena_es_403_y_no_toca_storage(
    cliente: AsyncClient,
    cliente_a: UsuarioDePrueba,
    cliente_b: UsuarioDePrueba,
    cuota_de: Cuota,
    sql: Ejecutar,
) -> None:
    r = await pagar(cliente, cliente_b, cuota_de(cliente_a))
    assert (r.status_code, codigo(r)) == (403, "sin_permiso")
    assert (pagos_de(sql, cliente_b), objetos(sql, cliente_b)) == (0, [])


async def test_cuota_inexistente_es_404(
    cliente: AsyncClient, cliente_a: UsuarioDePrueba, sql: Ejecutar
) -> None:
    r = await pagar(cliente, cliente_a, "00000000-0000-0000-0000-00000000dead")
    assert (r.status_code, codigo(r)) == (404, "no_encontrado")
    assert objetos(sql, cliente_a) == []


async def test_cuota_de_reserva_cancelada_es_409_cuota_no_pagable(
    cliente: AsyncClient, cliente_a: UsuarioDePrueba, cuota_de: Cuota, sql: Ejecutar
) -> None:
    r = await pagar(cliente, cliente_a, cuota_de(cliente_a, "cancelada"))
    assert (r.status_code, codigo(r)) == (409, "cuota_no_pagable")
    assert objetos(sql, cliente_a) == []


async def test_operacion_repetida_con_el_mismo_metodo_es_409(
    cliente: AsyncClient, cliente_a: UsuarioDePrueba, cuota_de: Cuota, sql: Ejecutar
) -> None:
    numero = operacion()
    assert (
        await pagar(cliente, cliente_a, cuota_de(cliente_a), numero_operacion=numero)
    ).status_code == 201
    r = await pagar(cliente, cliente_a, cuota_de(cliente_a), numero_operacion=numero.lower())
    assert (r.status_code, codigo(r)) == (409, "operacion_duplicada")
    assert len(objetos(sql, cliente_a)) == 1


async def test_segundo_pago_en_validacion_de_la_misma_cuota_es_409(
    cliente: AsyncClient, cliente_a: UsuarioDePrueba, cuota_de: Cuota
) -> None:
    cuota = cuota_de(cliente_a)
    assert (await pagar(cliente, cliente_a, cuota)).status_code == 201
    r = await pagar(cliente, cliente_a, cuota)
    assert (r.status_code, codigo(r)) == (409, "pago_en_validacion")


async def test_dos_pagos_simultaneos_a_la_misma_cuota_son_201_y_409(
    cliente: AsyncClient, cliente_a: UsuarioDePrueba, cuota_de: Cuota, sql: Ejecutar
) -> None:
    cuota = cuota_de(cliente_a)
    a, b = await asyncio.gather(pagar(cliente, cliente_a, cuota), pagar(cliente, cliente_a, cuota))
    assert sorted([a.status_code, b.status_code]) == [201, 409]
    assert (pagos_de(sql, cliente_a), len(objetos(sql, cliente_a))) == (1, 1)


async def test_si_storage_falla_no_queda_el_pago_y_responde_503(
    cliente: AsyncClient,
    cliente_a: UsuarioDePrueba,
    cuota_de: Cuota,
    sql: Ejecutar,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        modulo_router,
        "AlmacenStorage",
        lambda url, clave, token: AlmacenStorage("http://127.0.0.1:1", clave, token),
    )
    r = await pagar(cliente, cliente_a, cuota_de(cliente_a))
    assert (r.status_code, codigo(r)) == (503, "almacenamiento_no_disponible")
    assert pagos_de(sql, cliente_a) == 0


# --- ver el pago y la captura --------------------------------------------------------------------


async def _registrar(
    cliente: AsyncClient, usuario: UsuarioDePrueba, cuota_de: Cuota, captura: bytes = PNG
) -> dict[str, Any]:
    r = await pagar(cliente, usuario, cuota_de(usuario), captura)
    assert r.status_code == 201, r.text
    return dict(r.json())


async def test_la_url_firmada_descarga_la_captura(
    cliente: AsyncClient, cliente_a: UsuarioDePrueba, cuota_de: Cuota
) -> None:
    pago = await _registrar(cliente, cliente_a, cuota_de)
    r = await cliente.get(f"{PAGOS}/{pago['id']}/captura", headers=con(cliente_a))
    assert r.status_code == 200, r.text
    assert set(r.json()) == {"url", "expira_en", "tipo"}
    assert r.json()["tipo"] == "imagen"
    descarga = httpx.get(r.json()["url"])
    assert (descarga.status_code, descarga.content) == (200, PNG)


async def test_el_pdf_se_declara_de_tipo_pdf(
    cliente: AsyncClient, cliente_a: UsuarioDePrueba, cuota_de: Cuota
) -> None:
    pago = await _registrar(cliente, cliente_a, cuota_de, PDF)
    r = await cliente.get(f"{PAGOS}/{pago['id']}/captura", headers=con(cliente_a))
    assert r.json()["tipo"] == "pdf"


async def test_dueno_y_administrador_ven_el_pago_y_el_otro_cliente_no(
    cliente: AsyncClient,
    cliente_a: UsuarioDePrueba,
    cliente_b: UsuarioDePrueba,
    administrador: UsuarioDePrueba,
    cuota_de: Cuota,
) -> None:
    pago = await _registrar(cliente, cliente_a, cuota_de)
    url = f"{PAGOS}/{pago['id']}"
    propio = await cliente.get(url, headers=con(cliente_a))
    assert (propio.status_code, propio.json()["id"]) == (200, pago["id"])
    assert "cliente" not in propio.json()
    admin = await cliente.get(url, headers=con(administrador))
    assert admin.status_code == 200
    assert admin.json()["cliente"] == {"id": str(cliente_a.id), "nombre": "Ana Torres"}
    assert (await cliente.get(f"{url}/captura", headers=con(administrador))).status_code == 200
    for ruta in (url, f"{url}/captura"):
        ajeno = await cliente.get(ruta, headers=con(cliente_b))
        assert (ajeno.status_code, codigo(ajeno)) == (403, "sin_permiso")


async def test_pago_inexistente_404_no_uuid_422_y_sin_sesion_401(
    cliente: AsyncClient, cliente_a: UsuarioDePrueba
) -> None:
    inexistente = f"{PAGOS}/00000000-0000-0000-0000-00000000dead"
    for ruta in (inexistente, f"{inexistente}/captura"):
        r = await cliente.get(ruta, headers=con(cliente_a))
        assert (r.status_code, codigo(r)) == (404, "no_encontrado")
    r = await cliente.get(f"{PAGOS}/no-es-uuid", headers=con(cliente_a))
    assert (r.status_code, codigo(r)) == (422, "datos_invalidos")
    assert (await cliente.get(inexistente)).status_code == 401


async def test_la_captura_no_se_puede_borrar_con_el_token_del_cliente(
    cliente: AsyncClient,
    cliente_a: UsuarioDePrueba,
    cuota_de: Cuota,
    configuracion: Configuracion,
    sql: Ejecutar,
) -> None:
    pago = await _registrar(cliente, cliente_a, cuota_de)
    ruta = f"{cliente_a.id}/{pago['id']}.png"
    cabeceras = {
        "Authorization": f"Bearer {cliente_a.token}",
        "apikey": configuracion.clave_publicable_supabase,
    }
    base = f"{configuracion.url_supabase}/storage/v1/object/comprobantes"
    httpx.delete(f"{base}/{ruta}", headers=cabeceras)
    httpx.request("DELETE", base, headers=cabeceras, json={"prefixes": [ruta]})
    assert objetos(sql, cliente_a) == [ruta]
    # y no se reemplaza (upsert) ni se sobrescribe
    r = httpx.post(
        f"{base}/{ruta}",
        headers={**cabeceras, "x-upsert": "true", "Content-Type": "image/png"},
        content=PNG + b"otro",
    )
    assert r.status_code >= 400
    assert (
        httpx.get(
            f"{configuracion.url_supabase}/storage/v1/object/authenticated/comprobantes/{ruta}",
            headers=cabeceras,
        ).content
        == PNG
    )


async def test_openapi_declara_respuesta_error_en_cada_codigo(app: FastAPI) -> None:
    esquema = app.openapi()["paths"]
    esperados = {
        ("post", "/api/v1/pagos"): {"201", "401", "403", "404", "409", "413", "422", "503"},
        ("get", "/api/v1/pagos/{id_pago}"): {"200", "401", "403", "404", "422", "503"},
        ("get", "/api/v1/pagos/{id_pago}/captura"): {"200", "401", "403", "404", "422", "503"},
    }
    for (metodo, ruta), codigos in esperados.items():
        respuestas = esquema[ruta][metodo]["responses"]
        assert codigos <= set(respuestas), (ruta, set(respuestas))
        for c in codigos - {"200", "201"}:
            assert respuestas[c]["content"]["application/json"]["schema"]["$ref"].endswith(
                "RespuestaError"
            ), (ruta, c)


async def test_un_cuerpo_gigante_es_413_antes_de_leer_el_formulario(
    cliente: AsyncClient, cliente_a: UsuarioDePrueba
) -> None:
    # Si se parseara el multipart, este cuerpo sin formato valido daria 422.
    cabeceras = {**con(cliente_a), "Content-Type": "multipart/form-data; boundary=x"}
    r = await cliente.post(PAGOS, content=b"0" * (LIMITE_BYTES + 200_000), headers=cabeceras)
    assert (r.status_code, codigo(r)) == (413, "archivo_muy_grande")


async def test_un_content_length_falso_y_enorme_es_413_sin_leer_el_cuerpo(
    cliente: AsyncClient, cliente_a: UsuarioDePrueba
) -> None:
    cabeceras = {**con(cliente_a), "Content-Length": str(10 * LIMITE_BYTES)}
    r = await cliente.post(PAGOS, content=b"x", headers=cabeceras)
    assert (r.status_code, codigo(r)) == (413, "archivo_muy_grande")
