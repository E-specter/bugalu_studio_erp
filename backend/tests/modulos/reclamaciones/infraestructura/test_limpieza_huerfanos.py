# ruff: noqa: E501 - SQL literal largo
"""Subida terminada con la confirmacion fallida: el objeto huerfano se borra de Storage (RF-16)."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import pytest
from httpx import AsyncClient

from bugalu.compartido.base_datos import crear_pool
from bugalu.compartido.configuracion import Configuracion
from bugalu.compartido.errores import AlmacenamientoNoDisponible
from bugalu.modulos.reclamaciones.aplicacion.limpiar.caso_de_uso import LimpiarAdjuntosHuerfanos
from bugalu.modulos.reclamaciones.infraestructura.entrada.http import router as modulo_router
from bugalu.modulos.reclamaciones.infraestructura.salida.almacen_storage import AlmacenStorage
from bugalu.modulos.reclamaciones.infraestructura.salida.repositorio_postgres import (
    RepositorioHojasPostgres,
)
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

    # Solo sus rutas: la base es compartida y la API de desarrollo limpia sus propios huerfanos cada hora.
    propias = [
        f[0] for f in sql("select ruta from public.subida_reclamacion where id_hoja = %s", id_)
    ]

    class SoloPropias(RepositorioHojasPostgres):
        async def rutas_huerfanas(self) -> list[str]:
            return [r for r in await super().rutas_huerfanas() if r in propias]

    async with crear_pool(configuracion.url_base_datos) as pool:

        @asynccontextmanager
        async def como_api() -> AsyncIterator[SoloPropias]:
            async with pool.connection() as conexion, conexion.transaction():
                yield SoloPropias(conexion)

        limpiar = LimpiarAdjuntosHuerfanos(
            como_api,
            AlmacenStorage(configuracion.url_supabase, configuracion.clave_publicable_supabase),
        )
        assert await limpiar.ejecutar() == 0  # aun no caduco
        assert sql(cuenta, id_) == [(1,)]
        sql(
            "update public.subida_reclamacion set caduca_en = now() - interval '2 hours' where id_hoja = %s",
            id_,
        )
        assert await limpiar.ejecutar() == 1
    assert sql(cuenta, id_) == [(0,)]
    assert sql("select count(*) from public.subida_reclamacion where id_hoja = %s", id_) == [(1,)]
