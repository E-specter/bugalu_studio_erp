# ruff: noqa: E501, F811 - SQL literal y fixtures compartidas
import hashlib
import json
import os
import random
import uuid
from collections.abc import AsyncIterator, Iterator
from pathlib import Path
from typing import Any

import httpx
import psycopg
import pytest
from dotenv import dotenv_values
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from bugalu.compartido.configuracion import Configuracion
from tests.conftest import UsuarioDePrueba
from tests.modulos.reservas.infraestructura.conftest import (  # noqa: F401 - fixtures compartidas
    Ejecutar,
    administrador,
    app,
    cliente_a,
    cliente_b,
    con,
    sql,
)

_ENV = Path(__file__).parents[4] / ".env"
PNG = b"\x89PNG\r\n\x1a\n" + b"contenido-de-prueba" * 10
PDF = b"%PDF-1.7\n" + b"contenido-de-prueba" * 10
JPG = b"\xff\xd8\xff\xe0" + b"contenido-de-prueba" * 10
HOJAS = "/api/v1/reclamaciones"


def _clave_de_servicio() -> str:
    clave = os.environ.get("CLAVE_SERVICIO_SUPABASE_PRUEBAS") or dotenv_values(_ENV).get(
        "CLAVE_SERVICIO_SUPABASE_PRUEBAS"
    )
    assert clave, "Falta CLAVE_SERVICIO_SUPABASE_PRUEBAS en el entorno o en backend/.env"
    return clave


def datos(**cambios: Any) -> dict[str, Any]:
    """Cuerpo `NuevaHoja` valido; el correo de prueba permite limpiar lo que dejen las pruebas."""
    base: dict[str, Any] = {
        "confirmado": True,
        "consumidor": {
            "nombre": "Ana Prueba",
            "tipo_documento": "dni",
            "documento": "12345678",
            "domicilio": "Av. Lima 123, Miraflores",
            "telefono": "987654321",
            "correo": f"{uuid.uuid4().hex}@prueba.bugalu.pe",
        },
        "es_menor": False,
        "bien": {"tipo": "servicio", "monto": "50.00", "descripcion": "Ensayo del 10 de marzo"},
        "tipo": "reclamo",
        "detalle": "El servicio no fue el pactado.",
        "pedido": "Quiero la devolucion de lo pagado.",
        "medio_respuesta": "correo",
    }
    return base | cambios


async def enviar(
    cliente: AsyncClient,
    cuerpo: dict[str, Any],
    adjuntos: list[tuple[str, bytes, str]] | None = None,
    usuario: UsuarioDePrueba | None = None,
    ruta: str = HOJAS,
    cabeceras: dict[str, str] | None = None,
    **extra: Any,
) -> Any:
    archivos = [("adjuntos", a) for a in adjuntos or []]
    return await cliente.post(
        ruta,
        data={"datos": json.dumps(cuerpo), **extra},
        files=archivos or None,
        headers=cabeceras or (con(usuario) if usuario else None),
    )


@pytest.fixture
def ips_usadas() -> list[str]:
    return []


@pytest.fixture
def ip(ips_usadas: list[str]) -> str:
    direccion = f"10.{random.randint(0, 255)}.{random.randint(0, 255)}.{random.randint(1, 254)}"
    ips_usadas.append(direccion)
    return direccion


@pytest.fixture
async def anonimo(app: FastAPI, ip: str) -> AsyncIterator[AsyncClient]:
    """Cliente con IP propia: el limite por IP no cruza pruebas."""
    transporte = ASGITransport(app=app, client=(ip, 5000))
    async with AsyncClient(transport=transporte, base_url="http://t") as c:
        yield c


@pytest.fixture(autouse=True)
def hojas_limpias(
    request: pytest.FixtureRequest, configuracion: Configuracion, ips_usadas: list[str]
) -> Iterator[None]:
    """Borra lo que crean las pruebas (las hojas son inmutables: se apagan solo sus triggers de usuario)."""
    yield
    if request.node.get_closest_marker("integracion") is None:
        return
    like = "%%@prueba.bugalu.pe"
    with psycopg.connect(configuracion.url_base_datos_admin) as c:
        ids = [
            f[0]
            for f in c.execute(
                "select id from public.hoja_reclamacion where correo like %s", (like,)
            )
        ]
        objetos = [
            f[0]
            for f in c.execute(
                "select name from storage.objects where bucket_id = 'reclamaciones' "
                "and (storage.foldername(name))[1] = any(%s)",
                ([str(i) for i in ids],),
            )
        ]
        c.execute("alter table public.hoja_reclamacion disable trigger user")
        c.execute("alter table public.adjunto_reclamacion disable trigger user")
        c.execute("delete from public.adjunto_reclamacion where id_hoja = any(%s)", (ids,))
        c.execute("delete from public.hoja_reclamacion where id = any(%s)", (ids,))
        c.execute("alter table public.hoja_reclamacion enable trigger user")
        c.execute("alter table public.adjunto_reclamacion enable trigger user")
        c.execute(
            "delete from public.notificacion where tipo like 'reclamacion%%' "
            "and (datos ->> 'id' = any(%s) or destinatario like %s)",
            ([str(i) for i in ids], like),
        )
        hashes = [hashlib.sha256(i.encode()).hexdigest() for i in ips_usadas]
        c.execute("delete from public.intento_reclamacion where ip_hash = any(%s)", (hashes,))
    if objetos:
        r = httpx.request(
            "DELETE",
            f"{configuracion.url_supabase}/storage/v1/object/reclamaciones",
            headers={"Authorization": f"Bearer {_clave_de_servicio()}"},
            json={"prefixes": objetos},
        )
        r.raise_for_status()
    with psycopg.connect(configuracion.url_base_datos_admin) as c:
        quedan = c.execute(
            "select (select count(*) from public.hoja_reclamacion where correo like %s) "
            "+ (select count(*) from storage.objects o where o.bucket_id = 'reclamaciones' "
            "and (storage.foldername(o.name))[1] = any(%s))",
            (like, [str(i) for i in ids]),
        ).fetchone()
    assert quedan == (0,), f"las pruebas dejaron hojas u objetos huerfanos: {quedan}"
