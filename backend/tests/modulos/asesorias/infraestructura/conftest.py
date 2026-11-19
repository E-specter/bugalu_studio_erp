# ruff: noqa: F811 - fixtures compartidas importadas
import os
import uuid
from collections.abc import Callable, Iterator
from pathlib import Path

import httpx
import psycopg
import pytest
from dotenv import dotenv_values

from bugalu.compartido.configuracion import Configuracion
from tests.conftest import UsuarioDePrueba
from tests.modulos.pagos.infraestructura.conftest import pagos_limpios  # noqa: F401, E402
from tests.modulos.reservas.infraestructura.conftest import (  # noqa: F401 - fixtures compartidas
    Ejecutar,
    administrador,
    app,
    cliente,
    cliente_a,
    cliente_b,
    con,
    personal,
    reservas_intactas,
    sql,
)

_ENV = Path(__file__).parents[4] / ".env"


def _clave_de_servicio() -> str:
    clave = os.environ.get("CLAVE_SERVICIO_SUPABASE_PRUEBAS") or dotenv_values(_ENV).get(
        "CLAVE_SERVICIO_SUPABASE_PRUEBAS"
    )
    assert clave, "Falta CLAVE_SERVICIO_SUPABASE_PRUEBAS en el entorno o en backend/.env"
    return clave


@pytest.fixture(autouse=True)
def asesorias_intactas(
    configuracion: Configuracion, request: pytest.FixtureRequest
) -> Iterator[None]:
    """Las pruebas no dejan especialidades, registro de cambios, confirmaciones ni fotos."""
    yield
    if request.node.get_closest_marker("integracion") is None:
        return
    with psycopg.connect(configuracion.url_base_datos_admin, autocommit=True) as c:
        fotos = [
            f[0]
            for f in c.execute(
                "select o.name from storage.objects o where o.bucket_id = 'profesionales' "
                "and (storage.foldername(o.name))[1] in (select p.id::text "
                "from public.perfil_profesional p join auth.users u on u.id = p.id "
                "where u.email like '%@prueba.bugalu.pe')"
            ).fetchall()
        ]
        c.execute("alter table public.registro_cambio disable trigger user")
        c.execute("delete from public.registro_cambio where recurso = 'profesional'")
        c.execute("alter table public.registro_cambio enable trigger user")
        c.execute("delete from public.confirmacion_cambio where recurso = 'profesional'")
        c.execute(
            "delete from public.perfil_especialidad where id_especialidad in "
            "(select id from public.especialidad_asesoria where nombre like 'Prueba %')"
        )
        c.execute("delete from public.especialidad_asesoria where nombre like 'Prueba %'")
    if fotos:
        httpx.request(
            "DELETE",
            f"{configuracion.url_supabase}/storage/v1/object/profesionales",
            headers={"Authorization": f"Bearer {_clave_de_servicio()}"},
            json={"prefixes": fotos},
        ).raise_for_status()


@pytest.fixture
def nombre_especialidad() -> Callable[[], str]:
    return lambda: f"Prueba {uuid.uuid4().hex[:8]}"


@pytest.fixture
async def profesional(
    cliente: httpx.AsyncClient,
    administrador: UsuarioDePrueba,
    crear_usuario: Callable[[], UsuarioDePrueba],
) -> UsuarioDePrueba:
    """Una cuenta a la que el Administrador asigna el rol por la API: su perfil nace inactivo."""
    u = crear_usuario()
    r = await cliente.patch(
        f"/api/v1/usuarios/{u.id}", headers=con(administrador), json={"rol": "profesional"}
    )
    assert r.status_code == 200, r.text
    return u


@pytest.fixture
async def otro_profesional(
    cliente: httpx.AsyncClient,
    administrador: UsuarioDePrueba,
    crear_usuario: Callable[[], UsuarioDePrueba],
) -> UsuarioDePrueba:
    u = crear_usuario()
    r = await cliente.patch(
        f"/api/v1/usuarios/{u.id}", headers=con(administrador), json={"rol": "profesional"}
    )
    assert r.status_code == 200, r.text
    return u
