"""RF-01 CA-02: Supabase Auth exige 8+ caracteres con minuscula, mayuscula, numero y simbolo."""

import uuid

import httpx
import psycopg
import pytest

from bugalu.compartido.configuracion import Configuracion

pytestmark = pytest.mark.integracion


def _alta(configuracion: Configuracion, contrasena: str) -> httpx.Response:
    return httpx.post(
        f"{configuracion.url_supabase}/auth/v1/signup",
        headers={"apikey": configuracion.clave_publicable_supabase},
        json={"email": f"{uuid.uuid4().hex}@prueba.bugalu.pe", "password": contrasena},
    )


@pytest.mark.parametrize(
    "debil", ["Ab1!", "clave-segura-123", "CLAVE-SEGURA-123", "Clave-Segura-x", "Clave Segura 12"]
)
def test_una_contrasena_debil_se_rechaza(configuracion: Configuracion, debil: str) -> None:
    r = _alta(configuracion, debil)
    assert (r.status_code, r.json()["error_code"]) == (422, "weak_password")


def test_una_contrasena_fuerte_se_acepta(configuracion: Configuracion) -> None:
    r = _alta(configuracion, "Clave-Segura-123")
    assert r.status_code == 200
    with psycopg.connect(configuracion.url_base_datos_admin) as c:
        c.execute("delete from auth.users where id = %s", (r.json().get("user", r.json())["id"],))
