"""Auth solo redirige al frontend (ADR-005): origen de Astro permitido, cualquier otro no."""

import httpx
import pytest

from bugalu.compartido.configuracion import Configuracion

pytestmark = pytest.mark.integracion


def _destino(configuracion: Configuracion, redirect_to: str) -> str:
    r = httpx.get(
        f"{configuracion.url_supabase}/auth/v1/verify",
        params={"token": "x", "type": "signup", "redirect_to": redirect_to},
        headers={"apikey": configuracion.clave_publicable_supabase},
        follow_redirects=False,
    )
    return r.headers["location"]


@pytest.mark.parametrize("origen", ["http://localhost:4321", "http://127.0.0.1:4321"])
@pytest.mark.parametrize(
    "ruta", ["/app/perfil", "/acceso/nueva-contrasena", "/app/perfil?verificar=1"]
)
def test_las_rutas_del_frontend_son_destinos_permitidos(
    configuracion: Configuracion, origen: str, ruta: str
) -> None:
    assert _destino(configuracion, f"{origen}{ruta}").startswith(f"{origen}{ruta}")


@pytest.mark.parametrize("origen", ["http://evil.example", "http://localhost.evil.example"])
def test_un_origen_ajeno_no_es_un_destino_permitido(
    configuracion: Configuracion, origen: str
) -> None:
    assert not _destino(configuracion, f"{origen}/app/perfil?verificar=1").startswith(origen)
