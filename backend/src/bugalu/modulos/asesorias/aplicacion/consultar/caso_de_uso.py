from dataclasses import replace
from datetime import datetime
from uuid import UUID

from bugalu.compartido.errores import DatosInvalidos, NoEncontrado, SinPermiso
from bugalu.modulos.asesorias.dominio.asesoria import Asesoria, RepositorioAgenda

ESTADOS = ("pre_reservada", "confirmada", "realizada", "cancelada", "no_asistio")


def para_su_profesional(a: Asesoria) -> Asesoria:
    """CA-16: ni cuotas, ni pagado, ni condiciones; el contacto del cliente y las notas, si."""
    return replace(a, cuotas=None, pagado=None, version_condiciones=None, notas=a.notas or "")


def para_su_cliente(a: Asesoria) -> Asesoria:
    return replace(a, cliente=None, notas=None)


class ObtenerAsesoria:
    def __init__(self, repo: RepositorioAgenda) -> None:
        self._repo = repo

    async def ejecutar(self, id_actor: UUID, id_asesoria: UUID) -> Asesoria:
        a = await self._repo.obtener_asesoria(id_asesoria)
        if a is None:
            raise NoEncontrado("No existe la asesoria.")
        if await self._repo.es_administrador():
            return replace(a, notas=a.notas or "")
        if a.id_cliente == id_actor:
            return para_su_cliente(a)
        return para_su_profesional(a)


class ListarMisAsesorias:
    def __init__(self, repo: RepositorioAgenda) -> None:
        self._repo = repo

    async def ejecutar(self) -> list[Asesoria]:
        if await self._repo.es_profesional():
            raise SinPermiso("Un profesional no agenda asesorias.")
        return [para_su_cliente(a) for a in await self._repo.listar_mias()]


class ListarAsesorias:
    """Profesional (las suyas, por la RLS) o administrador (todas)."""

    def __init__(self, repo: RepositorioAgenda) -> None:
        self._repo = repo

    async def ejecutar(
        self,
        estado: str | None,
        desde: datetime | None,
        hasta: datetime | None,
        id_profesional: UUID | None,
        por_cerrar: bool,
        ahora: datetime,
    ) -> list[Asesoria]:
        administrador = await self._repo.es_administrador()
        if not administrador and not await self._repo.es_profesional():
            raise SinPermiso("Solo un profesional o un administrador ve esta lista.")
        if estado is not None and estado not in ESTADOS:
            raise DatosInvalidos("El estado no existe.", {"campo": "estado"})
        if desde and hasta and hasta <= desde:
            raise DatosInvalidos("El rango es invalido.", {"campo": "hasta"})
        if por_cerrar and estado not in (None, "confirmada"):
            return []
        return await self._repo.listar(
            "confirmada" if por_cerrar else estado,
            desde,
            hasta,
            id_profesional,
            ahora if por_cerrar else None,
        )
