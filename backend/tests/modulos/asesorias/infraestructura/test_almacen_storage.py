import httpx
import pytest

from bugalu.compartido.errores import AlmacenamientoNoDisponible
from bugalu.modulos.asesorias.infraestructura.salida.almacen_storage import (
    AlmacenFotosStorage,
    url_publica,
)


def _almacen(responder: httpx.MockTransport) -> AlmacenFotosStorage:
    return AlmacenFotosStorage("http://s", "clave", "tok", responder)


async def test_subir_usa_el_token_del_usuario_y_sobrescribe_su_ruta() -> None:
    vistas: list[httpx.Request] = []

    def responder(p: httpx.Request) -> httpx.Response:
        vistas.append(p)
        return httpx.Response(200, json={})

    await _almacen(httpx.MockTransport(responder)).subir("id/a.png", b"datos", "image/png")
    (p,) = vistas
    assert str(p.url) == "http://s/storage/v1/object/profesionales/id/a.png"
    assert (p.headers["authorization"], p.headers["x-upsert"], p.content) == (
        "Bearer tok",
        "true",
        b"datos",
    )


@pytest.mark.parametrize("estado", [400, 403, 500])
async def test_un_error_de_storage_es_503(estado: int) -> None:
    almacen = _almacen(httpx.MockTransport(lambda _: httpx.Response(estado, json={})))
    with pytest.raises(AlmacenamientoNoDisponible):
        await almacen.subir("id/a.png", b"x", "image/png")
    with pytest.raises(AlmacenamientoNoDisponible):
        await almacen.borrar("id/a.png")


async def test_storage_caido_es_503_y_borrar_lo_ya_borrado_no_falla() -> None:
    def caido(_: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("no")

    with pytest.raises(AlmacenamientoNoDisponible):
        await _almacen(httpx.MockTransport(caido)).borrar("id/a.png")
    await _almacen(httpx.MockTransport(lambda _: httpx.Response(404, json={}))).borrar("id/a.png")


def test_la_url_publica_apunta_al_bucket_publico() -> None:
    assert url_publica("http://s/", "id/a.png") == (
        "http://s/storage/v1/object/public/profesionales/id/a.png"
    )
