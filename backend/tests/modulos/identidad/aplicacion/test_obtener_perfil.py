from uuid import UUID, uuid4

import pytest

from bugalu.modulos.identidad.aplicacion.obtener_perfil.caso_de_uso import (
    ObtenerPerfil,
    PerfilNoEncontrado,
)
from bugalu.modulos.identidad.dominio.usuario import Rol, Usuario


class RepositorioFalso:
    def __init__(self, usuarios: list[Usuario]) -> None:
        self._usuarios = {u.id: u for u in usuarios}

    async def obtener_por_id(self, id_usuario: UUID) -> Usuario | None:
        return self._usuarios.get(id_usuario)


async def test_devuelve_el_perfil_existente() -> None:
    ana = Usuario(id=uuid4(), nombre="Ana", rol=Rol.CLIENTE, especialidad=None)
    assert await ObtenerPerfil(RepositorioFalso([ana])).ejecutar(ana.id) == ana


async def test_perfil_inexistente_lanza_perfil_no_encontrado() -> None:
    with pytest.raises(PerfilNoEncontrado):
        await ObtenerPerfil(RepositorioFalso([])).ejecutar(uuid4())
