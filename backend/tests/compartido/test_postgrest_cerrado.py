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


U = "00000000-0000-0000-0000-000000000001"
# Con los nombres reales, `public` expuesto la resolveria (distinto de 404 PGRST202); con `{}` no.
ARGUMENTOS_DE_LA_POLITICA: dict[str, dict[str, object]] = {
    "reprogramar_reserva": {
        "p_id": U,
        "p_nuevo_inicio": "2027-06-01T10:00:00-05:00",
        "p_nivel_esperado": None,
        "p_total_esperado": None,
        "p_id_franja": None,
        "p_precio": {},
        "p_total_nuevo": None,
    },
    "cancelar_reserva": {"p_id": U},
    "aplicar_credito": {"p_id_cuota": U, "p_monto": 1},
    "elegir_estudio_devolucion": {"p_id": U},
    "aplicar_excepcion": {"p_id": U, "p_motivo": "Motivo de la excepcion"},
    "aplicar_inasistencia": {"p_id": U, "p_id_autor": U},
}
FUNCIONES_DE_LA_POLITICA = list(ARGUMENTOS_DE_LA_POLITICA)


@pytest.mark.parametrize("funcion", FUNCIONES_DE_LA_POLITICA)
def test_las_funciones_de_la_politica_no_se_exponen_por_rpc(
    configuracion: Configuracion, crear_usuario: Callable[[], UsuarioDePrueba], funcion: str
) -> None:
    r = httpx.post(
        f"{configuracion.url_supabase}/rest/v1/rpc/{funcion}",
        headers=_cabeceras(configuracion, crear_usuario()),
        json=ARGUMENTOS_DE_LA_POLITICA[funcion],
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
