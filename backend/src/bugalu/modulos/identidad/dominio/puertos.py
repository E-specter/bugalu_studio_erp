from typing import Protocol
from uuid import UUID

from bugalu.modulos.identidad.dominio.usuario import Usuario


class RepositorioUsuarios(Protocol):
    async def obtener_por_id(self, id_usuario: UUID) -> Usuario | None: ...
