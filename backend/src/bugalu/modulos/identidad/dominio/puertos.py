from collections.abc import Mapping
from typing import Protocol
from uuid import UUID

from bugalu.modulos.identidad.dominio.solicitud import EstadoSolicitud, Solicitud
from bugalu.modulos.identidad.dominio.usuario import Rol, Usuario


class RepositorioUsuarios(Protocol):
    async def obtener_por_id(self, id_usuario: UUID) -> Usuario | None: ...

    async def listar(self, rol: Rol | None) -> list[Usuario]: ...

    async def actualizar_perfil(
        self, id_usuario: UUID, cambios: Mapping[str, str | None]
    ) -> Usuario: ...

    async def marcar_correo_verificado(self, id_usuario: UUID) -> bool: ...

    async def asignar_rol(self, id_usuario: UUID, rol: Rol, especialidad: str | None) -> None: ...


class RepositorioSolicitudes(Protocol):
    async def crear(
        self, id_usuario: UUID, especialidad: str, mensaje: str | None
    ) -> Solicitud: ...

    async def obtener_ultima_de(self, id_usuario: UUID) -> Solicitud | None: ...

    async def listar(self, estado: EstadoSolicitud | None) -> list[Solicitud]: ...

    async def obtener(self, id_solicitud: UUID) -> Solicitud | None: ...

    async def resolver(
        self, id_solicitud: UUID, estado: EstadoSolicitud, id_revisor: UUID, motivo: str | None
    ) -> Solicitud | None:
        """Resuelve solo si sigue pendiente; devuelve None si otro la resolvio antes."""
        ...
