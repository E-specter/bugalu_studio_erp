import pytest

from bugalu.compartido.configuracion import Configuracion, obtener_configuracion


@pytest.fixture(autouse=True)
def _entorno_vacio(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setitem(Configuracion.model_config, "env_file", None)  # sin .env a la vista
    for variable in ("URL_BASE_DATOS", "URL_SUPABASE", "CLAVE_PUBLICABLE_SUPABASE"):
        monkeypatch.delenv(variable, raising=False)
    obtener_configuracion.cache_clear()
    yield  # type: ignore[misc]
    obtener_configuracion.cache_clear()


def test_sin_url_de_base_de_datos_falla_con_un_mensaje_claro() -> None:
    with pytest.raises(RuntimeError, match="URL_BASE_DATOS"):
        obtener_configuracion()


def test_sin_url_de_supabase_falla_con_un_mensaje_claro(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("URL_BASE_DATOS", "postgresql://u:p@h/db")
    with pytest.raises(RuntimeError, match="URL_SUPABASE"):
        obtener_configuracion()


def test_sin_clave_publicable_falla_con_un_mensaje_claro(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("URL_BASE_DATOS", "postgresql://u:p@h/db")
    monkeypatch.setenv("URL_SUPABASE", "http://127.0.0.1:45621")
    with pytest.raises(RuntimeError, match="CLAVE_PUBLICABLE_SUPABASE"):
        obtener_configuracion()


def test_src_no_conoce_la_clave_de_servicio() -> None:
    from bugalu.compartido.configuracion import Configuracion

    assert not any("servicio" in campo for campo in Configuracion.model_fields)
