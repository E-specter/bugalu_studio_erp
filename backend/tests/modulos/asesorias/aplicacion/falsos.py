from collections.abc import Collection, Mapping, Sequence
from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID, uuid4

from bugalu.compartido.errores import (
    AlmacenamientoNoDisponible,
    EspecialidadDuplicada,
    HorarioSolapado,
)
from bugalu.modulos.asesorias.dominio.modelos import Especialidad, Horario, Profesional
from bugalu.modulos.catalogo.dominio.precio import ConfiguracionImpuestos
from bugalu.modulos.reservas.dominio.disponibilidad import Tramo

D = Decimal
PABLO = uuid4()
PAULA = uuid4()
MEZCLA = Especialidad(uuid4(), "Mezcla", True)


def perfil(id_: UUID, **cambios: Any) -> Profesional:
    base = {
        "id": id_, "nombre": "Pablo Uno", "nombre_artistico": None, "presentacion": None,
        "redes": (), "especialidades": (MEZCLA,), "foto_ruta": None, "precios": {30: D("50.00")},
        "activo": True, "publicado": True,
    }  # fmt: skip
    return Profesional(**{**base, **cambios})


class RepositorioFalso:
    def __init__(self, administrador: bool = False) -> None:
        self.administrador = administrador
        self.perfiles = {PABLO: perfil(PABLO), PAULA: perfil(PAULA, nombre="Paula Dos")}
        self.especialidades = [MEZCLA]
        self.horarios: list[Horario] = []
        self.vivas: list[UUID] = []
        self.escrituras: list[str] = []
        self.impuestos = ConfiguracionImpuestos(D("18"), True)
        self.minima, self.maxima = 2, 8

    async def es_administrador(self) -> bool:
        return self.administrador

    async def listar_especialidades(self, todas: bool) -> list[Especialidad]:
        return [e for e in self.especialidades if todas or e.activa]

    async def crear_especialidad(self, nombre: str) -> Especialidad:
        if any(e.nombre.lower() == nombre.lower() for e in self.especialidades):
            raise EspecialidadDuplicada("duplicada")
        nueva = Especialidad(uuid4(), nombre, True)
        self.especialidades.append(nueva)
        self.escrituras.append("especialidad")
        return nueva

    async def actualizar_especialidad(
        self, id_especialidad: UUID, cambios: Mapping[str, Any]
    ) -> Especialidad | None:
        for i, e in enumerate(self.especialidades):
            if e.id == id_especialidad:
                self.especialidades[i] = Especialidad(
                    e.id, cambios.get("nombre", e.nombre), cambios.get("activa", e.activa)
                )
                return self.especialidades[i]
        return None

    async def listar_profesionales(
        self, id_especialidad: UUID | None, solo_publicados: bool
    ) -> list[Profesional]:
        return [
            p for p in self.perfiles.values()
            if (p.publicado or not solo_publicados)
            and (id_especialidad is None or id_especialidad in {e.id for e in p.especialidades})
        ]  # fmt: skip

    async def obtener_profesional(self, id_profesional: UUID) -> Profesional | None:
        return self.perfiles.get(id_profesional)

    async def actualizar_perfil(self, id_profesional: UUID, campos: Mapping[str, Any]) -> None:
        self.escrituras.append("perfil")

    async def reemplazar_especialidades(
        self, id_profesional: UUID, ids: Collection[UUID]
    ) -> None:
        self.escrituras.append("especialidades")

    async def cambiar_estado(self, id_profesional: UUID, activo: bool) -> None:
        self.escrituras.append("estado")

    async def precios_texto(self, id_profesional: UUID) -> dict[str, str]:
        p = self.perfiles[id_profesional].precios
        return {f"precio_{m}": f"{p[m]:.2f}" if m in p else "no_ofrece" for m in (30, 60)}

    async def obtener_impuestos(self) -> ConfiguracionImpuestos:
        return self.impuestos

    async def fijar_foto(self, id_profesional: UUID, ruta: str | None) -> None:
        self.escrituras.append(f"foto:{ruta}")

    async def listar_horarios(
        self, id_profesional: UUID, desde: datetime, hasta: datetime
    ) -> list[Horario]:
        return [h for h in self.horarios if h.inicio < hasta and h.fin > desde]

    async def horarios_antes_de(self, id_profesional: UUID, instante: datetime) -> list[Horario]:
        return [h for h in self.horarios if h.inicio < instante]

    async def insertar_horarios(
        self, id_profesional: UUID, tramos: Sequence[Tramo]
    ) -> list[Horario]:
        nuevos: list[Horario] = []
        for t in tramos:
            if any(Tramo(h.inicio, h.fin).solapa(t) for h in [*self.horarios, *nuevos]):
                raise HorarioSolapado("solapado")
            nuevos.append(Horario(uuid4(), id_profesional, t.inicio, t.fin))
        self.horarios += nuevos
        return nuevos

    async def obtener_horario(self, id_profesional: UUID, id_horario: UUID) -> Horario | None:
        return next((h for h in self.horarios if h.id == id_horario), None)

    async def asesorias_vivas_en(
        self, id_profesional: UUID, inicio: datetime, fin: datetime
    ) -> list[UUID]:
        return self.vivas

    async def retirar_horario(self, id_horario: UUID) -> None:
        self.horarios = [h for h in self.horarios if h.id != id_horario]
        self.escrituras.append("retiro")

    async def ocupados_en(
        self, id_profesional: UUID, desde: datetime, hasta: datetime
    ) -> list[Tramo]:
        return []

    async def limites_reserva(self) -> tuple[int, int]:
        return self.minima, self.maxima


class AlmacenFalso:
    def __init__(self, caido: bool = False) -> None:
        self.caido = caido
        self.subidos: list[tuple[str, str]] = []
        self.borrados: list[str] = []

    async def subir(self, ruta: str, contenido: bytes, mime: str) -> None:
        if self.caido:
            raise AlmacenamientoNoDisponible("caido")
        self.subidos.append((ruta, mime))

    async def borrar(self, ruta: str) -> None:
        if self.caido:
            raise AlmacenamientoNoDisponible("caido")
        self.borrados.append(ruta)
