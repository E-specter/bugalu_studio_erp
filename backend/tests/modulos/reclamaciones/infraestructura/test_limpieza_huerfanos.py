# ruff: noqa: E501 - SQL literal largo
"""Subida terminada con la confirmacion fallida: el objeto huerfano se borra de Storage (RF-16)."""

import pytest
from httpx import AsyncClient

from bugalu.compartido.base_datos import crear_pool
from bugalu.compartido.configuracion import Configuracion
from bugalu.compartido.errores import AlmacenamientoNoDisponible
from bugalu.modulos.reclamaciones.infraestructura.entrada.ejecucion import limpiar_una_vez
from bugalu.modulos.reclamaciones.infraestructura.entrada.http import router as modulo_router
from tests.modulos.reclamaciones.infraestructura.conftest import PNG, datos, enviar
from tests.modulos.reservas.infraestructura.conftest import Ejecutar

pytestmark = pytest.mark.integracion


async def test_la_limpieza_borra_de_storage_el_objeto_sin_adjunto_y_luego_la_base_la_fila(
    anonimo: AsyncClient,
    sql: Ejecutar,
    configuracion: Configuracion,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def no_confirma(self: object, ruta: str) -> None:
        raise AlmacenamientoNoDisponible("sin confirmar")

    monkeypatch.setattr(modulo_router.RepositorioHojasPostgres, "confirmar_adjunto", no_confirma)
    r = await enviar(anonimo, datos(), [("a.png", PNG, "image/png")])
    assert r.status_code == 201 and r.json()["adjuntos_no_guardados"] == [1], r.text
    id_ = r.json()["id"]
    cuenta = "select count(*) from storage.objects where bucket_id = 'reclamaciones' and (storage.foldername(name))[1] = %s"
    assert sql(cuenta, id_) == [(1,)]  # el objeto quedo subido y sin adjunto

    async with crear_pool(configuracion.url_base_datos) as pool:
        assert await limpiar_una_vez(pool, configuracion) == 0  # aun no caduco
        assert sql(cuenta, id_) == [(1,)]
        sql(
            "update public.subida_reclamacion set caduca_en = now() - interval '2 hours' where id_hoja = %s",
            id_,
        )
        assert await limpiar_una_vez(pool, configuracion) == 1
    assert sql(cuenta, id_) == [(0,)]
    assert sql("select count(*) from public.subida_reclamacion where id_hoja = %s", id_) == [(1,)]
    assert sql("select public.limpiar_subidas_reclamacion()") == [(1,)]
    assert sql("select count(*) from public.subida_reclamacion where id_hoja = %s", id_) == [(0,)]
