"""CA-11: el primer administrador se crea por CLI sobre un usuario ya registrado."""

from collections.abc import Callable

import psycopg
import pytest

from bugalu.compartido.configuracion import Configuracion
from bugalu.herramientas.crear_administrador import main
from tests.conftest import UsuarioDePrueba

pytestmark = pytest.mark.integracion


def _consultar(configuracion: Configuracion, sql: str, *parametros: object) -> tuple:  # type: ignore[type-arg]
    with psycopg.connect(configuracion.url_base_datos_admin) as c:
        return c.execute(sql, parametros).fetchone()  # type: ignore[return-value]


def test_promueve_a_administrador_por_correo_y_es_idempotente(
    configuracion: Configuracion,
    crear_usuario: Callable[[], UsuarioDePrueba],
    capsys: pytest.CaptureFixture[str],
) -> None:
    usuario = crear_usuario()
    (correo,) = _consultar(configuracion, "select email from auth.users where id = %s", usuario.id)
    try:
        assert main([correo]) == 0
        assert main([correo]) == 0  # segunda vez: sin error ni cambios
        assert _consultar(
            configuracion, "select rol from public.usuario where id = %s", usuario.id
        ) == ("administrador",)
    finally:
        with psycopg.connect(
            configuracion.url_base_datos_admin
        ) as c:  # sin el trigger del ultimo administrador
            c.execute("alter table public.usuario disable trigger usuario_conserva_administrador")
            c.execute("update public.usuario set rol = 'cliente' where id = %s", (usuario.id,))
            c.execute("alter table public.usuario enable trigger usuario_conserva_administrador")


def test_correo_inexistente_falla_con_mensaje_claro(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["no-existe@prueba.bugalu.pe"]) == 1
    assert "no existe" in capsys.readouterr().err


def test_sin_correo_falla_con_uso(capsys: pytest.CaptureFixture[str]) -> None:
    assert main([]) == 2
    assert "uso" in capsys.readouterr().err.lower()
