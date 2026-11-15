from datetime import datetime
from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, StringConstraints, field_validator

from bugalu.modulos.identidad.dominio import solicitud as dominio_solicitud
from bugalu.modulos.identidad.dominio.solicitud import EstadoSolicitud
from bugalu.modulos.identidad.dominio.usuario import Rol, Usuario

Texto = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)]
Telefono = Annotated[str, StringConstraints(pattern=r"^\+?[0-9]{9,15}$")]


class Perfil(BaseModel):
    id: UUID
    correo: str | None
    correo_confirmado: bool
    nombre: str | None
    telefono: str | None
    nombre_artistico: str | None
    rol: Rol
    especialidad: str | None

    @classmethod
    def desde_dominio(cls, usuario: Usuario, correo: str | None = None) -> Perfil:
        """`correo`: el claim `email` del token cuando el perfil es el propio."""
        return cls(
            id=usuario.id,
            correo=correo or usuario.correo,
            correo_confirmado=usuario.correo_confirmado,
            nombre=usuario.nombre,
            telefono=usuario.telefono,
            nombre_artistico=usuario.nombre_artistico,
            rol=usuario.rol,
            especialidad=usuario.especialidad,
        )


class Solicitud(BaseModel):
    id: UUID
    id_usuario: UUID
    nombre: str | None
    correo: str | None
    especialidad: str
    mensaje: str | None
    estado: EstadoSolicitud
    motivo: str | None
    creada_en: datetime
    revisada_en: datetime | None

    @classmethod
    def desde_dominio(cls, s: dominio_solicitud.Solicitud) -> Solicitud:
        return cls(**vars(s))


class _Cuerpo(BaseModel):
    model_config = ConfigDict(extra="forbid")  # un campo de mas (rol, estado...) es 422


class CambiosPerfil(_Cuerpo):
    nombre: Texto | None = None
    telefono: Telefono | None = None
    nombre_artistico: Texto | None = None


class NuevaSolicitud(_Cuerpo):
    especialidad: Texto
    mensaje: Annotated[str, StringConstraints(max_length=500)] | None = None


class Aprobacion(_Cuerpo):
    rol: Literal[Rol.PERSONAL, Rol.ADMINISTRADOR]
    especialidad: Texto


class Rechazo(_Cuerpo):
    motivo: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=500)]


class CambiosUsuario(_Cuerpo):
    rol: Rol | None = None
    especialidad: Texto | None = None

    @field_validator("rol")
    @classmethod
    def _rol_no_nulo(cls, rol: Rol | None) -> Rol | None:
        if rol is None:
            raise ValueError("El rol no puede ser nulo.")
        return rol
