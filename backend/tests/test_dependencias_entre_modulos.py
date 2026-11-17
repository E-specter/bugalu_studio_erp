"""Dependencias entre modulos en un solo sentido (docs/01-arquitectura/backend-hexagonal.md)."""

import re
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[1] / "src" / "bugalu" / "modulos"
# modulo -> modulos de los que puede importar (pagos -> reservas -> catalogo; sin ciclos)
PERMITIDOS: dict[str, set[str]] = {
    "catalogo": set(),
    "identidad": set(),
    "notificaciones": set(),
    "reservas": {"catalogo"},
    "pagos": {"catalogo", "reservas"},
}


@pytest.mark.parametrize("modulo", sorted(PERMITIDOS))
def test_la_carpeta_de_cada_modulo_existe_con_codigo(modulo: str) -> None:
    # Sin esto, un modulo renombrado o movido pasaria la prueba de abajo en vacio.
    assert any((RAIZ / modulo).rglob("*.py")), f"no hay codigo en {RAIZ / modulo}"


@pytest.mark.parametrize("modulo", sorted(PERMITIDOS))
def test_un_modulo_solo_importa_de_los_que_le_corresponden(modulo: str) -> None:
    usados = {
        m
        for archivo in (RAIZ / modulo).rglob("*.py")
        for m in re.findall(r"bugalu\.modulos\.(\w+)", archivo.read_text(encoding="utf-8"))
    } - {modulo}
    assert usados <= PERMITIDOS[modulo], (
        f"{modulo} importa de {sorted(usados - PERMITIDOS[modulo])}"
    )
