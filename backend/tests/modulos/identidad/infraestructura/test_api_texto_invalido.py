"""Un byte NUL o un caracter de control en cualquier texto de entrada es 422, nunca 500."""

from collections.abc import Callable
from uuid import uuid4

import pytest
from httpx import AsyncClient

from tests.conftest import UsuarioDePrueba

pytestmark = pytest.mark.integracion

ID = uuid4()
# (metodo, ruta, campo, texto_largo)
CAMPOS = [
    ("PATCH", "/perfil", "nombre", False),
    ("PATCH", "/perfil", "nombre_artistico", False),
    ("POST", "/solicitudes-acceso", "especialidad", False),
    ("POST", "/solicitudes-acceso", "mensaje", True),
    ("POST", f"/solicitudes-acceso/{ID}/aprobar", "especialidad", False),
    ("POST", f"/solicitudes-acceso/{ID}/rechazar", "motivo", True),
    ("PATCH", f"/usuarios/{ID}", "especialidad", False),
]
BASE = {"aprobar": {"rol": "personal"}, "solicitudes-acceso": {"especialidad": "mezcla"}}


def _cuerpo(ruta: str, campo: str, valor: str) -> dict[str, str]:
    return {**BASE.get(ruta.rsplit("/", 1)[-1], {}), campo: valor}


@pytest.mark.parametrize(
    "valor",
    [
        "a\u0000b",
        "a\x07b",
        "a\x1fb",
        "a\x7fb",
        "a\x85b",
        "a\x9fb",
        "a b",
        "a b",
    ],
)
@pytest.mark.parametrize(("metodo", "ruta", "campo", "_largo"), CAMPOS)
async def test_texto_con_nul_o_control_es_422(
    cliente: AsyncClient,
    crear_usuario: Callable[[], UsuarioDePrueba],
    poner_rol: Callable[[UsuarioDePrueba, str, str | None], None],
    metodo: str,
    ruta: str,
    campo: str,
    _largo: bool,
    valor: str,
) -> None:
    u = crear_usuario()
    poner_rol(u, "administrador", None)
    r = await cliente.request(
        metodo,
        f"/api/v1{ruta}",
        headers={"Authorization": f"Bearer {u.token}"},
        json=_cuerpo(ruta, campo, valor),
    )
    assert r.status_code == 422
    assert r.json()["error"]["codigo"] == "datos_invalidos"


async def test_los_textos_largos_admiten_saltos_de_linea_y_tabuladores(
    cliente: AsyncClient, crear_usuario: Callable[[], UsuarioDePrueba]
) -> None:
    r = await cliente.post(
        "/api/v1/solicitudes-acceso",
        headers={"Authorization": f"Bearer {crear_usuario().token}"},
        json={"especialidad": "mezcla", "mensaje": "linea 1\n\tlinea 2"},
    )
    assert r.status_code == 201
    assert r.json()["mensaje"] == "linea 1\n\tlinea 2"


async def test_los_textos_largos_aceptan_crlf_y_lo_normalizan(
    cliente: AsyncClient, crear_usuario: Callable[[], UsuarioDePrueba]
) -> None:
    r = await cliente.post(
        "/api/v1/solicitudes-acceso",
        headers={"Authorization": f"Bearer {crear_usuario().token}"},
        json={"especialidad": "mezcla", "mensaje": "linea 1\r\nlinea 2"},
    )
    assert r.status_code == 201
    assert r.json()["mensaje"] == "linea 1\nlinea 2"
