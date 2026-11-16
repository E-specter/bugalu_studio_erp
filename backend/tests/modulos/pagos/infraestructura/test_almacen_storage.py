import json

import httpx
import pytest

from bugalu.compartido.errores import AlmacenamientoNoDisponible
from bugalu.modulos.pagos.infraestructura.salida.almacen_storage import AlmacenStorage

BASE = "http://supabase.local"


def almacen(transporte: httpx.MockTransport) -> AlmacenStorage:
    return AlmacenStorage(BASE, "sb_publishable_x", "token-usuario", transporte=transporte)


async def test_sube_con_el_token_del_usuario_y_la_clave_publicable() -> None:
    vistas: list[httpx.Request] = []

    def responder(peticion: httpx.Request) -> httpx.Response:
        vistas.append(peticion)
        return httpx.Response(200, json={"Key": "x"})

    await almacen(httpx.MockTransport(responder)).subir("u/p.png", b"datos", "image/png")
    (p,) = vistas
    assert (p.method, str(p.url)) == ("POST", f"{BASE}/storage/v1/object/comprobantes/u/p.png")
    assert p.headers["authorization"] == "Bearer token-usuario"
    assert p.headers["apikey"] == "sb_publishable_x"
    assert p.headers["content-type"] == "image/png"
    assert p.headers["x-upsert"] == "false"
    assert p.content == b"datos"


async def test_firma_una_url_de_300_segundos() -> None:
    def responder(peticion: httpx.Request) -> httpx.Response:
        assert str(peticion.url) == f"{BASE}/storage/v1/object/sign/comprobantes/u/p.png"
        assert json.loads(peticion.content) == {"expiresIn": 300}
        return httpx.Response(200, json={"signedURL": "/object/sign/comprobantes/u/p.png?token=t"})

    url = await almacen(httpx.MockTransport(responder)).firmar("u/p.png", 300)
    assert url == f"{BASE}/storage/v1/object/sign/comprobantes/u/p.png?token=t"


@pytest.mark.parametrize(
    "respuesta",
    [
        httpx.Response(500),
        httpx.Response(400, json={"error": "x"}),
        httpx.ConnectError("caido"),
        httpx.ReadTimeout("lento"),
    ],
)
async def test_un_fallo_o_tiempo_agotado_es_almacenamiento_no_disponible(
    respuesta: httpx.Response | Exception,
) -> None:
    def responder(_: httpx.Request) -> httpx.Response:
        if isinstance(respuesta, Exception):
            raise respuesta
        return respuesta

    destino = almacen(httpx.MockTransport(responder))
    with pytest.raises(AlmacenamientoNoDisponible):
        await destino.subir("u/p.png", b"d", "image/png")
    with pytest.raises(AlmacenamientoNoDisponible):
        await destino.firmar("u/p.png", 300)
