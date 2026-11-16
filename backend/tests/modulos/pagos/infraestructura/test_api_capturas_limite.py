"""Capturas limite por la API: 4xx y nunca 500, y la ruta en Storage es siempre la del dueno."""

import re
from collections.abc import Callable
from uuid import UUID

import pytest
from httpx import AsyncClient

from tests.conftest import UsuarioDePrueba
from tests.modulos.pagos.infraestructura.conftest import PDF, PNG, operacion
from tests.modulos.pagos.infraestructura.test_api_pagos import PAGOS, objetos, pagar
from tests.modulos.reservas.infraestructura.conftest import Ejecutar, con

pytestmark = pytest.mark.integracion

Cuota = Callable[..., str]
COMILLA = bytes([34])
LIMITE = b"LIMITE-FALSO-123"


def _campos(cuota: str) -> dict[str, bytes]:
    return {
        "id_cuota": cuota.encode(),
        "metodo": b"yape",
        "monto": b"25.00",
        "numero_operacion": operacion().encode(),
    }


def _parte(nombre: bytes, valor: bytes, archivo: bytes | None = None) -> bytes:
    cabecera = b"Content-Disposition: form-data; name=" + COMILLA + nombre + COMILLA
    if archivo is not None:
        cabecera += b"; filename=" + COMILLA + archivo + COMILLA + b"\r\nContent-Type: image/png"
    return b"--" + LIMITE + b"\r\n" + cabecera + b"\r\n\r\n" + valor + b"\r\n"


def _cuerpo(cuota: str, nombre_archivo: bytes = b"c.png", contenido: bytes = PNG) -> bytes:
    partes = b"".join(_parte(k.encode(), v) for k, v in _campos(cuota).items())
    return partes + _parte(b"captura", contenido, nombre_archivo) + b"--" + LIMITE + b"--\r\n"


async def _enviar(
    cliente: AsyncClient, usuario: UsuarioDePrueba, cuerpo: bytes, tipo: bytes | None = None
) -> tuple[int, str]:
    tipo = tipo if tipo is not None else b"multipart/form-data; boundary=" + LIMITE
    r = await cliente.post(
        PAGOS, content=cuerpo, headers={**con(usuario), "Content-Type": tipo.decode("latin-1")}
    )
    return r.status_code, r.text


@pytest.mark.parametrize(
    ("contenido", "campo"),
    [
        (b"", "captura"),
        (b"<svg xmlns=" + COMILLA + b"http://www.w3.org/2000/svg" + COMILLA + b"/>", "captura"),
        (b"%PD", "captura"),
        (b"%PDF", "captura"),  # sin el guion de la firma %PDF-
        (b"\x89PNG\r\n\x1a", "captura"),  # firma de PNG truncada un byte
        (b"\xff\xd8", "captura"),  # JPEG sin su tercer byte
    ],
)
async def test_archivos_que_no_son_captura_son_4xx_y_no_dejan_pago_ni_objeto(
    cliente: AsyncClient,
    cliente_a: UsuarioDePrueba,
    cuota_de: Cuota,
    sql: Ejecutar,
    contenido: bytes,
    campo: str,
) -> None:
    r = await pagar(cliente, cliente_a, cuota_de(cliente_a), contenido)
    assert 400 <= r.status_code < 500, r.text
    assert r.json()["error"]["detalles"]["campo"] == campo
    assert sql("select count(*) from public.comprobante_pago")[0][0] == 0
    assert objetos(sql, cliente_a) == []


async def test_png_con_solo_la_firma_se_guarda_con_su_ruta_de_dueno(
    cliente: AsyncClient, cliente_a: UsuarioDePrueba, cuota_de: Cuota, sql: Ejecutar
) -> None:
    # El tipo sale de la firma (ADR); un PNG sin datos es de 8 bytes validos para Storage.
    r = await pagar(cliente, cliente_a, cuota_de(cliente_a), PNG[:8])
    assert r.status_code == 201, r.text
    assert objetos(sql, cliente_a) == [f"{cliente_a.id}/{r.json()['id']}.png"]


async def test_multipart_sin_boundary_es_4xx(
    cliente: AsyncClient, cliente_a: UsuarioDePrueba, cuota_de: Cuota, sql: Ejecutar
) -> None:
    estado, texto = await _enviar(
        cliente, cliente_a, _cuerpo(cuota_de(cliente_a)), b"multipart/form-data"
    )
    assert 400 <= estado < 500, texto
    assert sql("select count(*) from public.comprobante_pago")[0][0] == 0


async def test_multipart_con_boundary_falso_es_4xx(
    cliente: AsyncClient, cliente_a: UsuarioDePrueba, cuota_de: Cuota, sql: Ejecutar
) -> None:
    estado, texto = await _enviar(
        cliente,
        cliente_a,
        _cuerpo(cuota_de(cliente_a)),
        b"multipart/form-data; boundary=OTRO-LIMITE",
    )
    assert 400 <= estado < 500, texto
    assert sql("select count(*) from public.comprobante_pago")[0][0] == 0


@pytest.mark.parametrize("recorte", [10, 120, 400])
async def test_multipart_truncado_es_4xx(
    cliente: AsyncClient,
    cliente_a: UsuarioDePrueba,
    cuota_de: Cuota,
    sql: Ejecutar,
    recorte: int,
) -> None:
    cuerpo = _cuerpo(cuota_de(cliente_a))
    estado, texto = await _enviar(cliente, cliente_a, cuerpo[:recorte])
    assert 400 <= estado < 500, texto
    assert sql("select count(*) from public.comprobante_pago")[0][0] == 0


async def test_multipart_sin_cierre_final_no_es_500(
    cliente: AsyncClient, cliente_a: UsuarioDePrueba, cuota_de: Cuota, sql: Ejecutar
) -> None:
    cuerpo = _cuerpo(cuota_de(cliente_a))
    estado, texto = await _enviar(cliente, cliente_a, cuerpo[: -len(b"--" + LIMITE + b"--\r\n")])
    assert estado < 500, texto
    assert sql("select count(*) from public.comprobante_pago")[0][0] in (0, 1)


@pytest.mark.parametrize(
    "nombre",
    [
        b"../../otro/x.png",
        b"..%2f..%2fx.png",
        b"..\\..\\x.png",
        b"a\xffb.png",  # no es UTF-8
        b"\xed\xa0\x80.png",  # sustituto codificado
        b"x" * 3000 + b".png",
        b"",
    ],
)
async def test_el_nombre_del_archivo_no_cambia_la_ruta_ni_da_500(
    cliente: AsyncClient,
    cliente_a: UsuarioDePrueba,
    cuota_de: Cuota,
    sql: Ejecutar,
    nombre: bytes,
) -> None:
    estado, texto = await _enviar(cliente, cliente_a, _cuerpo(cuota_de(cliente_a), nombre))
    assert estado < 500, texto
    for ruta in objetos(sql, cliente_a):
        assert re.fullmatch(rf"{cliente_a.id}/[0-9a-f-]{{36}}\.png", ruta), ruta
    rutas = sql(
        "select ruta_captura from public.comprobante_pago where id_cliente = %s", cliente_a.id
    )
    assert [f[0] for f in rutas] == objetos(sql, cliente_a)
    if estado == 201:
        assert len(rutas) == 1
        assert UUID(rutas[0][0].split("/")[1].split(".")[0])


async def test_la_extension_sale_de_los_bytes_y_no_del_nombre_ni_del_mime(
    cliente: AsyncClient, cliente_a: UsuarioDePrueba, cuota_de: Cuota, sql: Ejecutar
) -> None:
    r = await pagar(
        cliente, cliente_a, cuota_de(cliente_a), PDF, nombre="../../x.png", tipo="image/png"
    )
    assert r.status_code == 201, r.text
    assert objetos(sql, cliente_a) == [f"{cliente_a.id}/{r.json()['id']}.pdf"]


async def test_el_multipart_a_mano_es_valido_y_un_nombre_con_barras_se_guarda_con_ruta_de_dueno(
    cliente: AsyncClient, cliente_a: UsuarioDePrueba, cuota_de: Cuota, sql: Ejecutar
) -> None:
    estado, texto = await _enviar(
        cliente, cliente_a, _cuerpo(cuota_de(cliente_a), b"../../otro/x.png")
    )
    assert estado == 201, texto  # el constructor es correcto: los 4xx de arriba no son un artefacto
    ruta = objetos(sql, cliente_a)[0]
    assert re.fullmatch(rf"{cliente_a.id}/[0-9a-f-]{{36}}\.png", ruta), ruta
