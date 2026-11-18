from collections.abc import Mapping
from typing import Any
from uuid import UUID

from bugalu.compartido.errores import NoEncontrado, SinPermiso
from bugalu.modulos.asesorias.aplicacion.permisos import exigir_administrador, exigir_gestion
from bugalu.modulos.asesorias.dominio.modelos import Profesional
from bugalu.modulos.asesorias.dominio.puertos import RepositorioAsesorias
from bugalu.modulos.catalogo.dominio import cambios_sensibles as sensibles

_SOLO_ADMINISTRADOR = frozenset({"activo", "precios"})


class ListarProfesionales:
    def __init__(self, repo: RepositorioAsesorias) -> None:
        self._repo = repo

    async def ejecutar(
        self, id_especialidad: UUID | None, con_sesion: bool
    ) -> tuple[list[Profesional], bool]:
        """(perfiles, ve_estado): el administrador ve tambien los no publicados y su estado."""
        administrador = con_sesion and await self._repo.es_administrador()
        perfiles = await self._repo.listar_profesionales(id_especialidad, not administrador)
        return perfiles, administrador


class ObtenerProfesional:
    def __init__(self, repo: RepositorioAsesorias) -> None:
        self._repo = repo

    async def ejecutar(
        self, id_profesional: UUID, id_actor: UUID | None
    ) -> tuple[Profesional, bool]:
        """(perfil, ve_estado): `activo` y `publicado` son del propio y del administrador."""
        profesional = await self._repo.obtener_profesional(id_profesional)
        if profesional is None:
            raise NoEncontrado("No existe el profesional.")
        ve_estado = id_actor is not None and (
            id_actor == id_profesional or await self._repo.es_administrador()
        )
        return profesional, ve_estado


class CrearPerfil:
    def __init__(self, repo: RepositorioAsesorias) -> None:
        self._repo = repo

    async def ejecutar(self, id_usuario: UUID) -> Profesional:
        await exigir_administrador(self._repo)
        await self._repo.crear_perfil(id_usuario)
        perfil = await self._repo.obtener_profesional(id_usuario)
        if perfil is None:
            raise LookupError("El perfil desaparecio durante la transaccion.")
        return perfil


class ActualizarProfesional:
    def __init__(self, repo: RepositorioAsesorias) -> None:
        self._repo = repo

    async def ejecutar(
        self, id_actor: UUID, id_profesional: UUID, cambios: Mapping[str, Any]
    ) -> Profesional:
        if await self._repo.obtener_profesional(id_profesional) is None:
            raise NoEncontrado("No existe el profesional.")
        await exigir_gestion(self._repo, id_actor, id_profesional)
        if _SOLO_ADMINISTRADOR & cambios.keys() and not await self._repo.es_administrador():
            raise SinPermiso("Solo un administrador cambia el estado y los precios.")
        if (precios := cambios.get("precios")) is not None:
            sensibles.exigir_confirmacion(
                "profesional",
                await self._repo.precios_texto(id_profesional),
                {f"precio_{m}": sensibles.texto(v) for m, v in precios.items()},
            )
        if (ids := cambios.get("especialidades")) is not None:
            await self._repo.reemplazar_especialidades(id_profesional, ids)
        campos = {
            k: v for k, v in cambios.items() if k in ("nombre_artistico", "presentacion", "redes")
        }
        if campos:
            await self._repo.actualizar_perfil(id_profesional, campos)
        if "activo" in cambios:
            await self._repo.cambiar_estado(id_profesional, cambios["activo"])
        perfil = await self._repo.obtener_profesional(id_profesional)
        if perfil is None:
            raise LookupError("El perfil desaparecio durante la transaccion.")
        return perfil
