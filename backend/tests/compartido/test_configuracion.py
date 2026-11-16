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


def _base(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("URL_BASE_DATOS", "postgresql://u:p@h/db")
    monkeypatch.setenv("URL_SUPABASE", "http://127.0.0.1:45621")
    monkeypatch.setenv("CLAVE_PUBLICABLE_SUPABASE", "k")
    for variable in ("SMTP_USUARIO", "SMTP_CLAVE", "SMTP_STARTTLS"):
        monkeypatch.delenv(variable, raising=False)


def test_smtp_por_defecto_es_sin_credenciales_ni_starttls(monkeypatch: pytest.MonkeyPatch) -> None:
    _base(monkeypatch)
    c = obtener_configuracion()
    assert (c.smtp_usuario, c.smtp_starttls) == ("", False)
    assert c.smtp_clave.get_secret_value() == ""


@pytest.mark.parametrize(
    ("entorno", "falta"),
    [
        ({"SMTP_USUARIO": "a@b.c", "SMTP_STARTTLS": "true"}, "SMTP_CLAVE"),
        ({"SMTP_USUARIO": "a@b.c", "SMTP_CLAVE": "x"}, "SMTP_STARTTLS"),
    ],
)
def test_usuario_smtp_exige_clave_y_starttls(
    monkeypatch: pytest.MonkeyPatch, entorno: dict[str, str], falta: str
) -> None:
    _base(monkeypatch)
    for nombre, valor in entorno.items():
        monkeypatch.setenv(nombre, valor)
    with pytest.raises(RuntimeError, match=falta):
        obtener_configuracion()


def test_la_clave_smtp_no_aparece_en_repr(monkeypatch: pytest.MonkeyPatch) -> None:
    _base(monkeypatch)
    monkeypatch.setenv("SMTP_USUARIO", "a@b.c")
    monkeypatch.setenv("SMTP_CLAVE", "secreto-123")
    monkeypatch.setenv("SMTP_STARTTLS", "true")
    assert "secreto-123" not in repr(obtener_configuracion())
