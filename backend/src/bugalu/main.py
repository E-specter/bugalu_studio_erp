import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from bugalu.compartido.base_datos import crear_pool
from bugalu.compartido.configuracion import obtener_configuracion
from bugalu.compartido.esquemas import RespuestaError
from bugalu.compartido.manejadores_http import registrar_manejadores
from bugalu.modulos.catalogo.infraestructura.entrada.http.router import router as router_catalogo
from bugalu.modulos.catalogo.infraestructura.entrada.http.router_cambios import (
    router as router_cambios,
)
from bugalu.modulos.identidad.infraestructura.entrada.http.router import router as router_identidad
from bugalu.modulos.notificaciones.infraestructura.entrada.ejecucion import (
    enviar_una_vez,
    repetir,
)
from bugalu.modulos.pagos.infraestructura.entrada.http.limite import LimitePagos
from bugalu.modulos.pagos.infraestructura.entrada.http.router import router as router_pagos
from bugalu.modulos.reservas.infraestructura.entrada.http.router import router as router_reservas


@asynccontextmanager
async def _ciclo_de_vida(app: FastAPI) -> AsyncIterator[None]:
    configuracion = obtener_configuracion()
    async with crear_pool(
        configuracion.url_base_datos, configuracion.timeout_pool_segundos
    ) as pool:
        app.state.pool = pool
        tarea = None
        if configuracion.intervalo_envio_correos > 0:
            tarea = asyncio.create_task(
                repetir(
                    lambda: enviar_una_vez(pool, configuracion),
                    configuracion.intervalo_envio_correos,
                )
            )
        try:
            yield
        finally:
            if tarea:
                tarea.cancel()
                await asyncio.gather(tarea, return_exceptions=True)


def crear_app() -> FastAPI:
    app = FastAPI(
        title="Bugalu Studio ERP",
        version="0.1.0",
        lifespan=_ciclo_de_vida,
        responses={422: {"model": RespuestaError, "description": "Datos invalidos"}},
    )
    app.add_middleware(LimitePagos)  # antes de CORS: la respuesta 413 conserva sus cabeceras
    if origenes := obtener_configuracion().lista_origenes_permitidos:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=origenes,
            allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
            allow_headers=["Authorization", "Content-Type"],
            allow_credentials=False,
        )
    registrar_manejadores(app)
    app.include_router(router_identidad, prefix="/api/v1")
    app.include_router(router_catalogo, prefix="/api/v1")
    app.include_router(router_cambios, prefix="/api/v1")
    app.include_router(router_reservas, prefix="/api/v1")
    app.include_router(router_pagos, prefix="/api/v1")
    return app
