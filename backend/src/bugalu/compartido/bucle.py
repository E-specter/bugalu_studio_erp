"""psycopg asincrono no funciona con ProactorEventLoop (el de Windows por defecto)."""

import asyncio


def crear_bucle() -> asyncio.AbstractEventLoop:
    return asyncio.SelectorEventLoop()
