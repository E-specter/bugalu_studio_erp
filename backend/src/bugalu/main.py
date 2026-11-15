from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from bugalu.compartido.base_datos import crear_pool
from bugalu.compartido.configuracion import obtener_configuracion
from bugalu.compartido.esquemas import RespuestaError
from bugalu.compartido.manejadores_http import registrar_manejadores
from bugalu.modulos.identidad.infraestructura.entrada.http.router import router as router_identidad


@asynccontextmanager
async def _ciclo_de_vida(app: FastAPI) -> AsyncIterator[None]:
    configuracion = obtener_configuracion()
    async with crear_pool(
        configuracion.url_base_datos, configuracion.timeout_pool_segundos
    ) as pool:
        app.state.pool = pool
        yield


def crear_app() -> FastAPI:
    app = FastAPI(
        title="Bugalu Studio ERP",
        version="0.1.0",
        lifespan=_ciclo_de_vida,
        responses={422: {"model": RespuestaError, "description": "Datos invalidos"}},
    )
    if origenes := obtener_configuracion().lista_origenes_permitidos:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=origenes,
            allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
            allow_headers=["Authorization", "Content-Type"],
            allow_credentials=False,
        )
    registrar_manejadores(app)
    app.include_router(router_identidad, prefix="/api/v1")
    return app
