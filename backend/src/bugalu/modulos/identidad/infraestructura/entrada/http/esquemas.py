import re
from datetime import datetime
from typing import Annotated, Literal
from uuid import UUID

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    field_validator,
    model_validator,
)

from bugalu.compartido.esquemas import TextoCorto, TextoLargo
from bugalu.modulos.identidad.dominio import solicitud as dominio_solicitud
from bugalu.modulos.identidad.dominio.solicitud import EstadoSolicitud
from bugalu.modulos.identidad.dominio.usuario import PerfilCompleto, Rol, Usuario

Telefono = Annotated[str, StringConstraints(pattern=r"^\+?[0-9]{9,15}$")]
Modalidad = Literal["individual", "agrupacion"]
RedSocial = Literal["instagram", "tiktok", "facebook", "youtube", "spotify", "otra"]
_EXTRANJERIA = re.compile(r"[A-Z0-9]{6,12}")
_NUMERO = {"dni": re.compile(r"[0-9]{8}"), "ce": _EXTRANJERIA, "pasaporte": _EXTRANJERIA}


class _Cuerpo(BaseModel):
    model_config = ConfigDict(extra="forbid")  # un campo de mas (rol, estado...) es 422


class Documento(_Cuerpo):
    tipo: Literal["dni", "ce", "pasaporte"]
    numero: str

    @model_validator(mode="after")
    def _formato(self) -> Documento:
        self.numero = "".join(self.numero.split()).upper()
        if not _NUMERO[self.tipo].fullmatch(self.numero):
            raise ValueError("Numero de documento invalido.")
        return self


class Red(_Cuerpo):
    red: RedSocial
    valor: TextoCorto


class Integrante(_Cuerpo):
    nombre: TextoCorto
    rol: TextoCorto


class Consentimientos(BaseModel):
    promociones_correo: bool
    promociones_whatsapp: bool
    fotos_videos: bool
    excluir_material: bool


class Pendiente(BaseModel):
    tipo: str
    version: str
    contexto: str
    motivo: str


class PerfilBasico(BaseModel):
    id: UUID
    correo: str | None
    correo_confirmado: bool
    nombre: str | None
    telefono: str | None
    nombre_artistico: str | None
    rol: Rol
    especialidad: str | None
    modalidad: Modalidad
    documento: Documento | None
    domicilio: str | None
    redes: list[Red]
    integrantes: list[Integrante]
    es_menor: bool

    @staticmethod
    def _campos(usuario: Usuario, correo: str | None) -> dict[str, object]:
        """`correo`: el claim `email` del token cuando el perfil es el propio."""
        return {
            "id": usuario.id,
            "correo": correo or usuario.correo,
            "correo_confirmado": usuario.correo_confirmado,
            "nombre": usuario.nombre,
            "telefono": usuario.telefono,
            "nombre_artistico": usuario.nombre_artistico,
            "rol": usuario.rol,
            "especialidad": usuario.especialidad,
            "modalidad": usuario.modalidad,
            "documento": vars(usuario.documento) if usuario.documento else None,
            "domicilio": usuario.domicilio,
            "redes": list(usuario.redes),
            "integrantes": list(usuario.integrantes),
            "es_menor": usuario.es_menor,
        }


class PerfilListado(PerfilBasico):
    """Lo que ve el Administrador de otras cuentas, con la marca de documento repetido."""

    documento_repetido: bool

    @classmethod
    def desde_dominio(cls, usuario: Usuario) -> PerfilListado:
        return cls.model_validate(
            {**cls._campos(usuario, None), "documento_repetido": usuario.documento_repetido}
        )


class Perfil(PerfilBasico):
    consentimientos: Consentimientos
    pendientes: list[Pendiente]
    datos_para_reservar: bool

    @classmethod
    def desde_dominio(cls, perfil: PerfilCompleto, correo: str | None = None) -> Perfil:
        return cls.model_validate(
            {
                **cls._campos(perfil.usuario, correo),
                "consentimientos": perfil.consentimientos,
                "pendientes": [vars(p) for p in perfil.pendientes],
                "datos_para_reservar": perfil.datos_para_reservar,
            }
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


def _no_nulo(valor: object) -> object:
    if valor is None:
        raise ValueError("No puede ser nulo.")
    return valor


class CambiosPerfil(_Cuerpo):
    nombre: TextoCorto | None = None
    telefono: Telefono | None = None
    nombre_artistico: TextoCorto | None = None
    modalidad: Modalidad | None = None
    documento: Documento | None = None
    domicilio: TextoCorto | None = None
    redes: Annotated[list[Red], Field(max_length=5)] | None = None
    integrantes: Annotated[list[Integrante], Field(max_length=20)] | None = None
    es_menor: bool | None = None

    # Las columnas obligatorias no admiten null: se omiten o se envian con valor.
    _sin_nulos = field_validator("modalidad", "documento", "redes", "integrantes", "es_menor")(
        _no_nulo
    )


class CambiosConsentimientos(_Cuerpo):
    promociones_correo: bool | None = None
    promociones_whatsapp: bool | None = None
    fotos_videos: bool | None = None
    excluir_material: bool | None = None

    _sin_nulos = field_validator(
        "promociones_correo", "promociones_whatsapp", "fotos_videos", "excluir_material"
    )(_no_nulo)


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
