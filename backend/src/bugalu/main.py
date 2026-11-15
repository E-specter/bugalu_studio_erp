from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from bugalu.compartido.base_datos import crear_pool
from bugalu.compartido.configuracion import obtener_configuracion
from bugalu.compartido.manejadores_http import registrar_manejadores
from bugalu.modulos.identidad.infraestructura.entrada.http.router import router as router_identidad


@asynccontextmanager
async def _ciclo_de_vida(app: FastAPI) -> AsyncIterator[None]:
    async with crear_pool(obtener_configuracion().url_base_datos) as pool:
        app.state.pool = pool
        yield


def crear_app() -> FastAPI:
    app = FastAPI(title="Bugalu Studio ERP", version="0.1.0", lifespan=_ciclo_de_vida)
    registrar_manejadores(app)
    app.include_router(router_identidad, prefix="/api/v1")
    return app


app = crear_app()
