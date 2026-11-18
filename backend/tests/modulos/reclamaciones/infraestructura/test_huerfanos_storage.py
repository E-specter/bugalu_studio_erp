# ruff: noqa: E501 - rutas y SQL literales largos
"""Un adjunto huerfano solo se puede borrar con la clave publicable: no listar, descargar, firmar ni consultar (RF-16)."""

from typing import Any

import httpx
import pytest
from httpx import AsyncClient

from bugalu.compartido.configuracion import Configuracion
from bugalu.compartido.errores import AlmacenamientoNoDisponible
from bugalu.modulos.reclamaciones.infraestructura.entrada.http import router as modulo_router
from tests.modulos.reclamaciones.infraestructura.conftest import PNG, datos, enviar
from tests.modulos.reservas.infraestructura.conftest import Ejecutar

pytestmark = pytest.mark.integracion


async def test_un_huerfano_solo_admite_el_borrado_con_la_clave_publicable(
    anonimo: AsyncClient,
    sql: Ejecutar,
    configuracion: Configuracion,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def no_confirma(self: object, ruta: str) -> None:
        raise AlmacenamientoNoDisponible("sin confirmar")

    monkeypatch.setattr(modulo_router.RepositorioHojasPostgres, "confirmar_adjunto", no_confirma)
    r = await enviar(anonimo, datos(), [("a.png", PNG, "image/png")])
    id_ = r.json()["id"]
    sql(
        "update public.subida_reclamacion set caduca_en = now() - interval '2 hours' where id_hoja = %s",
        id_,
    )
    (ruta,) = sql("select ruta from public.subida_reclamacion where id_hoja = %s", id_)[0]

    base = f"{configuracion.url_supabase.rstrip('/')}/storage/v1"
    cabeceras = {"apikey": configuracion.clave_publicable_supabase}
    async with httpx.AsyncClient(base_url=base, headers=cabeceras) as c:

        async def nombres(respuesta: httpx.Response) -> list[str]:
            cuerpo: Any = respuesta.json()
            filas = (
                cuerpo
                if isinstance(cuerpo, list)
                else cuerpo.get("objects", cuerpo.get("folders", []))
            )
            return [f.get("name", "") for f in filas] if isinstance(filas, list) else []

        for prefijo in ("", id_, id_ + "/"):
            lista = await c.post(
                "/object/list/reclamaciones", json={"prefix": prefijo, "limit": 100}
            )
            assert ruta not in await nombres(lista) and not any(
                id_ in n for n in await nombres(lista)
            ), lista.text
            v2 = await c.post(
                "/object/list-v2/reclamaciones", json={"prefix": prefijo, "limit": 100}
            )
            assert not any(id_ in n or n == ruta for n in await nombres(v2)), v2.text
            assert id_ not in v2.text, v2.text
        assert (await c.get(f"/object/authenticated/reclamaciones/{ruta}")).status_code >= 400
        assert (
            await c.post(f"/object/sign/reclamaciones/{ruta}", json={"expiresIn": 60})
        ).status_code >= 400
        assert (await c.get(f"/object/info/authenticated/reclamaciones/{ruta}")).status_code >= 400

        assert (
            await c.delete(f"/object/reclamaciones/{ruta}")
        ).status_code == 200  # la limpieza sigue
    assert sql(
        "select count(*) from storage.objects where bucket_id = 'reclamaciones' and name = %s", ruta
    ) == [(0,)]


async def _crear_hoja(
    anonimo: AsyncClient, sql: Ejecutar, monkeypatch: pytest.MonkeyPatch, confirmar: bool
) -> tuple[str, str]:
    """Devuelve (id_hoja, ruta). Sin confirmar, el objeto queda en una subida pendiente."""
    if not confirmar:

        async def no_confirma(self: object, ruta: str) -> None:
            raise AlmacenamientoNoDisponible("sin confirmar")

        monkeypatch.setattr(
            modulo_router.RepositorioHojasPostgres, "confirmar_adjunto", no_confirma
        )
    r = await enviar(anonimo, datos(), [("a.png", PNG, "image/png")])
    id_ = r.json()["id"]
    tabla = "adjunto_reclamacion" if confirmar else "subida_reclamacion"
    (ruta,) = sql(f"select ruta from public.{tabla} where id_hoja = %s", id_)[0]
    return id_, ruta


def _cliente(configuracion: Configuracion) -> httpx.AsyncClient:
    return httpx.AsyncClient(
        base_url=f"{configuracion.url_supabase.rstrip('/')}/storage/v1",
        headers={"apikey": configuracion.clave_publicable_supabase},
    )


@pytest.fixture
async def huerfano(
    anonimo: AsyncClient,
    sql: Ejecutar,
    configuracion: Configuracion,
    monkeypatch: pytest.MonkeyPatch,
) -> tuple[str, str]:
    id_, ruta = await _crear_hoja(anonimo, sql, monkeypatch, confirmar=False)
    sql(
        "update public.subida_reclamacion set caduca_en = now() - interval '2 hours' where id_hoja = %s",
        id_,
    )
    return id_, ruta


def _operaciones(ruta: str, id_: str) -> dict[str, tuple[str, str, dict[str, Any] | None]]:
    r = f"reclamaciones/{ruta}"
    return {
        "get": ("GET", f"/object/{r}", None),
        "get_public": ("GET", f"/object/public/{r}", None),
        "head_authenticated": ("HEAD", f"/object/authenticated/{r}", None),
        "info": ("GET", f"/object/info/{r}", None),
        "info_public": ("GET", f"/object/info/public/{r}", None),
        "sign_multiple": ("POST", "/object/sign/reclamaciones", {"paths": [ruta]}),
        "upload_sign": ("POST", f"/object/upload/sign/{r}", {}),
        "copy": (
            "POST",
            "/object/copy",
            {"bucketId": "reclamaciones", "sourceKey": ruta, "destinationKey": f"{id_}/copia.png"},
        ),
        "move": (
            "POST",
            "/object/move",
            {"bucketId": "reclamaciones", "sourceKey": ruta, "destinationKey": f"{id_}/movido.png"},
        ),
        "render": ("GET", f"/render/image/authenticated/{r}", None),
    }


_NOMBRES = list(_operaciones("x/y", "x"))


@pytest.mark.parametrize("operacion", _NOMBRES)
async def test_anon_no_obtiene_nada_de_un_huerfano(
    operacion: str,
    huerfano: tuple[str, str],
    configuracion: Configuracion,
    sql: Ejecutar,
) -> None:
    id_, ruta = huerfano
    metodo, url, cuerpo = _operaciones(ruta, id_)[operacion]
    async with _cliente(configuracion) as c:
        r = await c.request(metodo, url, json=cuerpo)
    assert r.status_code >= 400, f"{operacion}: {r.status_code} {r.text[:200]}"
    assert PNG not in r.content
    assert sql(
        "select count(*) from storage.objects where bucket_id = 'reclamaciones' and name = any(%s)",
        [ruta, f"{id_}/copia.png", f"{id_}/movido.png"],
    ) == [(1,)]


@pytest.mark.parametrize("version", ["list", "list-v2"])
async def test_anon_no_lista_un_huerfano_por_su_ruta_completa(
    version: str, huerfano: tuple[str, str], configuracion: Configuracion
) -> None:
    id_, ruta = huerfano
    async with _cliente(configuracion) as c:
        r = await c.post(f"/object/{version}/reclamaciones", json={"prefix": ruta, "limit": 100})
    assert id_ not in r.text and ruta not in r.text, r.text


@pytest.mark.parametrize("confirmar", [False, True], ids=["subida_vigente", "adjunto_confirmado"])
async def test_anon_no_borra_una_subida_vigente_ni_un_adjunto_confirmado(
    confirmar: bool,
    anonimo: AsyncClient,
    sql: Ejecutar,
    configuracion: Configuracion,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _, ruta = await _crear_hoja(anonimo, sql, monkeypatch, confirmar)
    async with _cliente(configuracion) as c:
        r = await c.delete(f"/object/reclamaciones/{ruta}")
    assert r.status_code >= 400 or r.json() == [], r.text
    assert sql(
        "select count(*) from storage.objects where bucket_id = 'reclamaciones' and name = %s", ruta
    ) == [(1,)]
