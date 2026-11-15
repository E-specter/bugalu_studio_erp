from collections.abc import AsyncIterator

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from bugalu.main import crear_app


@pytest.fixture
async def app() -> AsyncIterator[FastAPI]:
    app = crear_app()
    async with app.router.lifespan_context(app):
        yield app


@pytest.fixture
async def cliente(app: FastAPI) -> AsyncIterator[AsyncClient]:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
        yield c
