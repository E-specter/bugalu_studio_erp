import asyncio
from typing import Any

import pytest

from bugalu.compartido.configuracion import Configuracion, obtener_configuracion
from bugalu.modulos.notificaciones.infraestructura.entrada.ejecucion import repetir


def test_la_configuracion_de_correo_tiene_valores_locales_por_defecto(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setitem(Configuracion.model_config, "env_file", None)  # sin .env a la vista
    for variable in (
        "SMTP_HOST",
        "SMTP_PUERTO",
        "CORREO_REMITENTE",
        "INTERVALO_ENVIO_CORREOS",
        "URL_PUBLICA",
    ):
        monkeypatch.delenv(variable, raising=False)
    obtener_configuracion.cache_clear()
    c = obtener_configuracion()
    assert (c.smtp_host, c.smtp_puerto) == ("127.0.0.1", 45625)
    assert "@" in c.correo_remitente
    assert c.intervalo_envio_correos >= 0
    assert c.url_publica == "http://127.0.0.1:4321"


def test_la_url_publica_se_toma_del_entorno(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("URL_PUBLICA", "https://erp.bugalu.pe")
    obtener_configuracion.cache_clear()
    assert obtener_configuracion().url_publica == "https://erp.bugalu.pe"
    obtener_configuracion.cache_clear()


async def test_repetir_sigue_tras_un_fallo_y_se_puede_cancelar() -> None:
    llamadas: list[int] = []

    async def accion() -> Any:
        llamadas.append(1)
        if len(llamadas) == 1:
            raise ConnectionRefusedError("SMTP caido")

    tarea = asyncio.create_task(repetir(accion, 0.01))
    while len(llamadas) < 3:
        await asyncio.sleep(0.01)
    tarea.cancel()
    with pytest.raises(asyncio.CancelledError):
        await tarea
