"""ADR-007: el backend es el unico camino a los datos; PostgREST no expone `public`."""

from collections.abc import Callable

import httpx
import pytest

from bugalu.compartido.configuracion import Configuracion
from tests.conftest import UsuarioDePrueba

pytestmark = pytest.mark.integracion


def _cabeceras(configuracion: Configuracion, usuario: UsuarioDePrueba) -> dict[str, str]:
    return {
        "apikey": configuracion.clave_publicable_supabase,
        "Authorization": f"Bearer {usuario.token}",
    }


def test_la_tabla_usuario_no_se_expone_por_postgrest(
    configuracion: Configuracion, crear_usuario: Callable[[], UsuarioDePrueba]
) -> None:
    r = httpx.get(
        f"{configuracion.url_supabase}/rest/v1/usuario",
        headers=_cabeceras(configuracion, crear_usuario()),
    )
    assert (r.status_code, r.json()["code"]) == (404, "PGRST205")  # tabla ausente del esquema


def test_la_funcion_es_administrador_no_se_expone_por_rpc(
    configuracion: Configuracion, crear_usuario: Callable[[], UsuarioDePrueba]
) -> None:
    r = httpx.post(
        f"{configuracion.url_supabase}/rest/v1/rpc/es_administrador",
        headers=_cabeceras(configuracion, crear_usuario()),
    )
    assert (r.status_code, r.json()["code"]) == (404, "PGRST202")  # funcion ausente del esquema


FUNCIONES_DE_LA_POLITICA = [
    "reprogramar_reserva",
    "cancelar_reserva",
    "aplicar_credito",
    "elegir_estudio_devolucion",
    "aplicar_excepcion",
    "aplicar_inasistencia",
]


@pytest.mark.parametrize("funcion", FUNCIONES_DE_LA_POLITICA)
def test_las_funciones_de_la_politica_no_se_exponen_por_rpc(
    configuracion: Configuracion, crear_usuario: Callable[[], UsuarioDePrueba], funcion: str
) -> None:
    r = httpx.post(
        f"{configuracion.url_supabase}/rest/v1/rpc/{funcion}",
        headers=_cabeceras(configuracion, crear_usuario()),
        json={},
    )
    assert (r.status_code, r.json()["code"]) == (404, "PGRST202")


def test_graphql_no_muestra_las_funciones_de_la_politica(
    configuracion: Configuracion, crear_usuario: Callable[[], UsuarioDePrueba]
) -> None:
    r = httpx.post(
        f"{configuracion.url_supabase}/graphql/v1",
        headers=_cabeceras(configuracion, crear_usuario()),
        json={"query": "{ __schema { types { name fields { name } } } }"},
    )
    texto = r.text.lower().replace("_", "")
    assert r.status_code in (200, 404), r.text
    for funcion in [*FUNCIONES_DE_LA_POLITICA, "reserva", "cuota", "credito", "devolucion"]:
        assert funcion.replace("_", "") not in texto, funcion
