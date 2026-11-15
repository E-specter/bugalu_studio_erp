from dataclasses import FrozenInstanceError
from uuid import uuid4

import pytest

from bugalu.modulos.identidad.dominio.usuario import Rol, Usuario


def test_usuario_es_inmutable() -> None:
    usuario = Usuario(id=uuid4(), nombre="Ana", rol=Rol.CLIENTE, especialidad=None)
    with pytest.raises(FrozenInstanceError):
        usuario.rol = Rol.ADMINISTRADOR  # type: ignore[misc]


def test_rol_se_construye_desde_su_valor_de_base_de_datos() -> None:
    assert Rol("personal") is Rol.PERSONAL
    assert {r.value for r in Rol} == {"cliente", "personal", "administrador"}
