from datetime import datetime
from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, StringConstraints, field_validator

from bugalu.compartido.esquemas import TextoCorto, TextoLargo
from bugalu.modulos.identidad.dominio import solicitud as dominio_solicitud
from bugalu.modulos.identidad.dominio.solicitud import EstadoSolicitud
from bugalu.modulos.identidad.dominio.usuario import Rol, Usuario

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
    nombre: TextoCorto | None = None
    telefono: Telefono | None = None
    nombre_artistico: TextoCorto | None = None


class NuevaSolicitud(_Cuerpo):
    especialidad: TextoCorto
    mensaje: TextoLargo | None = None


class Aprobacion(_Cuerpo):
    rol: Literal[Rol.PERSONAL, Rol.ADMINISTRADOR]
    especialidad: TextoCorto


class Rechazo(_Cuerpo):
    motivo: TextoLargo


class CambiosUsuario(_Cuerpo):
    rol: Rol | None = None
    especialidad: TextoCorto | None = None

    @field_validator("rol")
    @classmethod
    def _rol_no_nulo(cls, rol: Rol | None) -> Rol | None:
        if rol is None:
            raise ValueError("El rol no puede ser nulo.")
        return rol
