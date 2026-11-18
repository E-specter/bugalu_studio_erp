import httpx
import pytest

from bugalu.compartido.errores import AlmacenamientoNoDisponible
from bugalu.modulos.reclamaciones.infraestructura.salida.almacen_storage import AlmacenStorage


def _almacen(manejador: httpx.MockTransport, token: str | None = None) -> AlmacenStorage:
    return AlmacenStorage("http://s", "clave-publicable", token, manejador)


async def test_el_alta_publica_sube_solo_con_la_clave_publicable_y_sin_authorization() -> None:
    vistas: list[httpx.Request] = []

    def responder(peticion: httpx.Request) -> httpx.Response:
        vistas.append(peticion)
        return httpx.Response(200, json={})

    await _almacen(httpx.MockTransport(responder)).subir("id/1.png", b"datos", "image/png")
    (p,) = vistas
    assert str(p.url) == "http://s/storage/v1/object/reclamaciones/id/1.png"
    assert p.headers["apikey"] == "clave-publicable"
    assert "authorization" not in p.headers
    assert (p.headers["content-type"], p.headers["x-upsert"], p.content) == (
        "image/png",
        "false",
        b"datos",
    )


async def test_firmar_usa_el_token_del_administrador_y_devuelve_la_url_completa() -> None:
    def responder(p: httpx.Request) -> httpx.Response:
        assert p.headers["authorization"] == "Bearer tok"
        assert p.read() == b'{"expiresIn":300}'
        return httpx.Response(
            200, json={"signedURL": "/object/sign/reclamaciones/id/1.png?token=t"}
        )

    url = await _almacen(httpx.MockTransport(responder), "tok").firmar("id/1.png", 300)
    assert url == "http://s/storage/v1/object/sign/reclamaciones/id/1.png?token=t"


@pytest.mark.parametrize("estado", [400, 403, 500])
async def test_un_error_de_storage_es_503(estado: int) -> None:
    almacen = _almacen(httpx.MockTransport(lambda _: httpx.Response(estado, json={})))
    with pytest.raises(AlmacenamientoNoDisponible):
        await almacen.subir("id/1.png", b"x", "image/png")


async def test_storage_caido_es_503() -> None:
    def caido(_: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("no")

    with pytest.raises(AlmacenamientoNoDisponible):
        await _almacen(httpx.MockTransport(caido)).subir("id/1.png", b"x", "image/png")


async def test_una_firma_con_respuesta_rara_es_503() -> None:
    almacen = _almacen(httpx.MockTransport(lambda _: httpx.Response(200, json={"otra": 1})), "t")
    with pytest.raises(AlmacenamientoNoDisponible):
        await almacen.firmar("id/1.png", 300)


async def test_borrar_usa_solo_la_clave_publicable_y_el_metodo_delete() -> None:
    vistas: list[httpx.Request] = []

    def responder(peticion: httpx.Request) -> httpx.Response:
        vistas.append(peticion)
        return httpx.Response(200, json={})

    await _almacen(httpx.MockTransport(responder)).borrar("id/uuid.pdf")
    (p,) = vistas
    assert (p.method, str(p.url)) == (
        "DELETE",
        "http://s/storage/v1/object/reclamaciones/id/uuid.pdf",
    )
    assert p.headers["apikey"] == "clave-publicable" and "authorization" not in p.headers
