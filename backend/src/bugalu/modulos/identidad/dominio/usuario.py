from dataclasses import dataclass, field
from enum import StrEnum
from uuid import UUID


class Rol(StrEnum):
    CLIENTE = "cliente"
    PERSONAL = "personal"
    ADMINISTRADOR = "administrador"
    PROFESIONAL = "profesional"  # RF-15: perfil publico y horarios propios; sin acceso de personal


@dataclass(frozen=True)
class Documento:
    tipo: str
    numero: str


@dataclass(frozen=True)
class Usuario:
    id: UUID
    nombre: str | None
    rol: Rol
    especialidad: str | None
    telefono: str | None = None
    nombre_artistico: str | None = None
    correo: str | None = None
    correo_confirmado: bool = False
    modalidad: str = "individual"
    documento: Documento | None = None
    domicilio: str | None = None
    redes: tuple[dict[str, str], ...] = field(default=())
    integrantes: tuple[dict[str, str], ...] = field(default=())
    es_menor: bool = False
    documento_repetido: bool = False  # solo lo ve el Administrador


@dataclass(frozen=True)
class Pendiente:
    """Un texto del registro por aceptar (RF-17, CA-05)."""

    tipo: str
    version: str
    contexto: str
    motivo: str


CONSENTIMIENTOS = ("promociones_correo", "promociones_whatsapp", "fotos_videos", "excluir_material")


@dataclass(frozen=True)
class PerfilCompleto:
    usuario: Usuario
    consentimientos: dict[str, bool]
    pendientes: tuple[Pendiente, ...]
    datos_para_reservar: bool
