"""Repositorios en memoria para probar los casos de uso sin base de datos."""

from collections.abc import Mapping
from dataclasses import replace
from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from bugalu.compartido.errores import UltimoAdministrador
from bugalu.modulos.identidad.dominio.solicitud import EstadoSolicitud, Solicitud
from bugalu.modulos.identidad.dominio.usuario import (
    CONSENTIMIENTOS,
    Documento,
    Pendiente,
    Rol,
    Usuario,
)


def usuario(rol: Rol = Rol.CLIENTE, **campos: object) -> Usuario:
    return Usuario(id=uuid4(), nombre="Ana", rol=rol, especialidad=None, **campos)  # type: ignore[arg-type]


def solicitud(**campos: object) -> Solicitud:
    base: dict[str, object] = {
        "id": uuid4(),
        "id_usuario": uuid4(),
        "nombre": "Ana",
        "correo": "ana@t.pe",
        "especialidad": "ingenieria",
        "mensaje": None,
        "estado": EstadoSolicitud.PENDIENTE,
        "motivo": None,
        "creada_en": datetime.now(UTC),
        "revisada_en": None,
    }
    return Solicitud(**{**base, **campos})  # type: ignore[arg-type]


class UsuariosFalsos:
    def __init__(self, *usuarios: Usuario) -> None:
        self.usuarios = {u.id: u for u in usuarios}
        self.textos_pendientes: list[Pendiente] = []
        self.faltantes: list[str] = []
        self.activos: set[str] = set()
        self.cambios_de_consentimiento: list[tuple[str, bool]] = []

    async def obtener_por_id(self, id_usuario: UUID) -> Usuario | None:
        return self.usuarios.get(id_usuario)

    async def listar(
        self, rol: Rol | None, documento_repetido: bool | None = None
    ) -> list[Usuario]:
        return [
            u
            for u in self.usuarios.values()
            if (rol is None or u.rol is rol)
            and (documento_repetido is None or u.documento_repetido is documento_repetido)
        ]

    async def actualizar_perfil(self, id_usuario: UUID, cambios: Mapping[str, Any]) -> Usuario:
        cambios = dict(cambios)
        if "documento" in cambios:
            cambios["documento"] = Documento(**cambios["documento"])
        for campo in ("redes", "integrantes"):
            if campo in cambios:
                cambios[campo] = tuple(cambios[campo])
        self.usuarios[id_usuario] = replace(self.usuarios[id_usuario], **cambios)
        return self.usuarios[id_usuario]

    async def pendientes(self) -> list[Pendiente]:
        return list(self.textos_pendientes)

    async def campos_faltantes_para_reservar(self) -> list[str]:
        return list(self.faltantes)

    async def consentimientos(self, id_usuario: UUID) -> dict[str, bool]:
        return {c: c in self.activos for c in CONSENTIMIENTOS}

    async def cambiar_consentimiento(self, consentimiento: str, dar: bool) -> None:
        self.cambios_de_consentimiento.append((consentimiento, dar))
        (self.activos.add if dar else self.activos.discard)(consentimiento)

    async def marcar_correo_verificado(self, id_usuario: UUID) -> bool:
        self.usuarios[id_usuario] = replace(self.usuarios[id_usuario], correo_confirmado=True)
        return True

    async def asignar_rol(self, id_usuario: UUID, rol: Rol, especialidad: str | None) -> None:
        administradores = [u.id for u in self.usuarios.values() if u.rol is Rol.ADMINISTRADOR]
        if rol is not Rol.ADMINISTRADOR and administradores == [id_usuario]:
            raise UltimoAdministrador
        self.usuarios[id_usuario] = replace(
            self.usuarios[id_usuario], rol=rol, especialidad=especialidad
        )


class SolicitudesFalsas:
    def __init__(self, *solicitudes: Solicitud) -> None:
        self.solicitudes = {s.id: s for s in solicitudes}

    async def crear(self, id_usuario: UUID, especialidad: str, mensaje: str | None) -> Solicitud:
        s = solicitud(id_usuario=id_usuario, especialidad=especialidad, mensaje=mensaje)
        self.solicitudes[s.id] = s
        return s

    async def obtener_ultima_de(self, id_usuario: UUID) -> Solicitud | None:
        propias = [s for s in self.solicitudes.values() if s.id_usuario == id_usuario]
        return propias[-1] if propias else None

    async def listar(self, estado: EstadoSolicitud | None) -> list[Solicitud]:
        return [s for s in self.solicitudes.values() if estado is None or s.estado is estado]

    async def obtener(self, id_solicitud: UUID) -> Solicitud | None:
        return self.solicitudes.get(id_solicitud)

    async def resolver(
        self, id_solicitud: UUID, estado: EstadoSolicitud, id_revisor: UUID, motivo: str | None
    ) -> Solicitud | None:
        s = self.solicitudes[id_solicitud]
        if s.estado is not EstadoSolicitud.PENDIENTE:
            return None
        self.solicitudes[id_solicitud] = replace(
            s, estado=estado, motivo=motivo, revisada_en=datetime.now(UTC)
        )
        return self.solicitudes[id_solicitud]
