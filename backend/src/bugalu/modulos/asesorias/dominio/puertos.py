from collections.abc import Collection, Mapping, Sequence
from datetime import datetime
from typing import Any, Protocol
from uuid import UUID

from bugalu.modulos.asesorias.dominio.modelos import Especialidad, Horario, Profesional
from bugalu.modulos.catalogo.dominio.precio import ConfiguracionImpuestos
from bugalu.modulos.reservas.dominio.disponibilidad import Tramo


class RepositorioAsesorias(Protocol):
    async def es_administrador(self) -> bool: ...

    async def listar_especialidades(self, todas: bool) -> list[Especialidad]: ...

    async def crear_especialidad(self, nombre: str) -> Especialidad:
        """Lanza EspecialidadDuplicada si el nombre ya existe (sin mayusculas ni tildes)."""
        ...

    async def actualizar_especialidad(
        self, id_especialidad: UUID, cambios: Mapping[str, Any]
    ) -> Especialidad | None: ...

    async def listar_profesionales(
        self, id_especialidad: UUID | None, solo_publicados: bool
    ) -> list[Profesional]: ...

    async def obtener_profesional(
        self, id_profesional: UUID, para_actualizar: bool = False
    ) -> Profesional | None:
        """La RLS decide: publicado, o el propio, o todo para el administrador."""
        ...

    async def crear_perfil(self, id_usuario: UUID) -> None:
        """Perfil inactivo de un usuario `administrador` (decision 8). Lanza PerfilExistente
        o RolNoAdmitido."""
        ...

    async def actualizar_perfil(self, id_profesional: UUID, campos: Mapping[str, Any]) -> None: ...

    async def reemplazar_especialidades(
        self, id_profesional: UUID, ids: Collection[UUID]
    ) -> None: ...

    async def cambiar_estado(self, id_profesional: UUID, activo: bool) -> None: ...

    async def precios_texto(self, id_profesional: UUID) -> dict[str, str]:
        """{precio_30, precio_60} en texto canonico (`50.00` o `no_ofrece`), para los sensibles."""
        ...

    async def obtener_impuestos(self) -> ConfiguracionImpuestos: ...

    async def fijar_foto(self, id_profesional: UUID, ruta: str | None) -> None: ...

    async def listar_horarios(
        self, id_profesional: UUID, desde: datetime, hasta: datetime
    ) -> list[Horario]: ...

    async def horarios_antes_de(
        self, id_profesional: UUID, instante: datetime
    ) -> list[Horario]: ...

    async def insertar_horarios(
        self, id_profesional: UUID, tramos: Sequence[Tramo]
    ) -> list[Horario]:
        """Lanza HorarioSolapado si algun bloque se solapa con otro del profesional."""
        ...

    async def obtener_horario(self, id_profesional: UUID, id_horario: UUID) -> Horario | None: ...

    async def asesorias_vivas_en(
        self, id_profesional: UUID, inicio: datetime, fin: datetime
    ) -> list[UUID]:
        """Etapa B: las asesorias `pre_reservada` o `confirmada` dentro del bloque."""
        ...

    async def retirar_horario(self, id_horario: UUID) -> None: ...

    async def ocupados_en(
        self, id_profesional: UUID, desde: datetime, hasta: datetime
    ) -> list[Tramo]:
        """Etapa B: asesorias vivas o ya dadas; sin ellas, vacio."""
        ...

    async def limites_reserva(self) -> tuple[int, int]:
        """Anticipacion minima en horas y maxima en semanas (RN-17, los de la sala)."""
        ...


class AlmacenFotos(Protocol):
    async def subir(self, ruta: str, contenido: bytes, mime: str) -> None: ...

    async def borrar(self, ruta: str) -> None: ...
