from collections.abc import Mapping, Sequence
from datetime import datetime
from typing import Any, Protocol
from uuid import UUID

from bugalu.modulos.identidad.dominio.solicitud import EstadoSolicitud, Solicitud
from bugalu.modulos.identidad.dominio.textos_legales import Aceptacion, TextoLegal
from bugalu.modulos.identidad.dominio.usuario import Pendiente, Rol, Usuario


class RepositorioUsuarios(Protocol):
    async def obtener_por_id(self, id_usuario: UUID) -> Usuario | None: ...

    async def listar(
        self, rol: Rol | None, documento_repetido: bool | None = None
    ) -> list[Usuario]: ...

    async def actualizar_perfil(self, id_usuario: UUID, cambios: Mapping[str, Any]) -> Usuario: ...

    async def pendientes(self) -> list[Pendiente]:
        """Textos del registro que falta aceptar al usuario de la transaccion."""
        ...

    async def campos_faltantes_para_reservar(self) -> list[str]: ...

    async def consentimientos(self, id_usuario: UUID) -> dict[str, bool]: ...

    async def cambiar_consentimiento(self, consentimiento: str, dar: bool) -> None: ...

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


class RepositorioTextos(Protocol):
    async def listar_publicos(self) -> list[TextoLegal]:
        """Los vigentes y los programados."""
        ...

    async def obtener(self, tipo: str, version: str) -> TextoLegal | None: ...

    async def vigentes(self) -> dict[str, TextoLegal]: ...

    async def ultima_version(self, tipo: str) -> str | None:
        """La mayor version publicada (con programadas); bloquea las publicaciones del tipo."""
        ...

    async def publicar(
        self,
        tipo: str,
        version: str,
        tipo_cambio: str,
        contenido: str,
        resumenes: Mapping[str, str],
        resumen_cambios: str | None,
        vigente_desde: datetime | None,
    ) -> TextoLegal: ...

    async def retirar(self, tipo: str, version: str) -> None: ...

    async def aceptar_registro(self, textos: Sequence[tuple[str, str]]) -> list[Aceptacion]: ...

    async def listar_aceptaciones(self, id_usuario: UUID) -> list[Aceptacion]: ...
