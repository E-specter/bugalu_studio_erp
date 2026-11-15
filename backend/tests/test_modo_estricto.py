import pytest

from tests.conftest import saltar_o_fallar


def test_sin_exigir_integracion_se_salta(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("EXIGIR_INTEGRACION", raising=False)
    with pytest.raises(pytest.skip.Exception):
        saltar_o_fallar("stack caido")


def test_con_exigir_integracion_falla_con_mensaje_claro(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("EXIGIR_INTEGRACION", "1")
    with pytest.raises(pytest.fail.Exception, match="EXIGIR_INTEGRACION.*stack caido"):
        saltar_o_fallar("stack caido")
