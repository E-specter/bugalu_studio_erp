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
