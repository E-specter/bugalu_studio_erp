from uuid import UUID

from pydantic import BaseModel

from bugalu.modulos.identidad.dominio.usuario import Rol, Usuario


class PerfilRespuesta(BaseModel):
    id: UUID
    nombre: str | None
    rol: Rol
    especialidad: str | None

    @classmethod
    def desde_dominio(cls, usuario: Usuario) -> PerfilRespuesta:
        return cls(
            id=usuario.id, nombre=usuario.nombre, rol=usuario.rol, especialidad=usuario.especialidad
        )
