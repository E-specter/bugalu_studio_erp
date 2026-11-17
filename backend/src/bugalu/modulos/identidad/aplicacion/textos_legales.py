"""Casos de uso de los textos legales y las aceptaciones (RF-17, etapa A)."""

from collections.abc import Callable, Mapping, Sequence
from datetime import UTC, datetime
from uuid import UUID

from bugalu.compartido.errores import NoEncontrado, TextoDesactualizado
from bugalu.modulos.identidad.aplicacion.permisos import exigir_administrador
from bugalu.modulos.identidad.dominio.puertos import RepositorioTextos, RepositorioUsuarios
from bugalu.modulos.identidad.dominio.textos_legales import (
    Aceptacion,
    TextoLegal,
    validar_aceptacion_de_registro,
    validar_publicacion,
)


class ListarTextos:
    def __init__(self, textos: RepositorioTextos) -> None:
        self._textos = textos

    async def ejecutar(self) -> list[TextoLegal]:
        return await self._textos.listar_publicos()


class ObtenerTexto:
    def __init__(self, textos: RepositorioTextos) -> None:
        self._textos = textos

    async def ejecutar(self, tipo: str, version: str) -> TextoLegal:
        texto = await self._textos.obtener(tipo, version)
        if texto is None:
            raise NoEncontrado("No existe esa version del texto.")
        return texto


class PublicarTexto:
    def __init__(
        self,
        usuarios: RepositorioUsuarios,
        textos: RepositorioTextos,
        ahora: Callable[[], datetime] = lambda: datetime.now(UTC),
    ) -> None:
        self._usuarios = usuarios
        self._textos = textos
        self._ahora = ahora

    async def ejecutar(
        self,
        id_actor: UUID,
        tipo: str,
        version: str,
        tipo_cambio: str,
        contenido: str,
        resumenes: Mapping[str, str],
        resumen_cambios: str | None,
        vigente_desde: datetime | None,
    ) -> TextoLegal:
        await exigir_administrador(self._usuarios, id_actor)
        ultima = await self._textos.ultima_version(tipo)
        efectiva = validar_publicacion(version, tipo_cambio, vigente_desde, ultima, self._ahora())
        return await self._textos.publicar(
            tipo, version, tipo_cambio, contenido, resumenes, resumen_cambios, efectiva
        )


class RetirarTexto:
    def __init__(self, usuarios: RepositorioUsuarios, textos: RepositorioTextos) -> None:
        self._usuarios = usuarios
        self._textos = textos

    async def ejecutar(self, id_actor: UUID, tipo: str, version: str) -> None:
        await exigir_administrador(self._usuarios, id_actor)
        await self._textos.retirar(tipo, version)


class AceptarTextos:
    """Aceptacion del registro (CA-04): solo se acepta la version vigente (CA-03)."""

    def __init__(self, textos: RepositorioTextos) -> None:
        self._textos = textos

    async def ejecutar(self, textos: Sequence[tuple[str, str]]) -> list[Aceptacion]:
        validar_aceptacion_de_registro(textos)
        vigentes = await self._textos.vigentes()
        for tipo, version in textos:
            vigente = vigentes.get(tipo)
            if vigente is None or vigente.version != version:
                raise TextoDesactualizado(
                    f"La version {version} de {tipo} no es la vigente.",
                    {
                        "vigente": None
                        if vigente is None
                        else {
                            "tipo": vigente.tipo,
                            "version": vigente.version,
                            "vigente_desde": vigente.vigente_desde.isoformat(),
                        }
                    },
                )
        return await self._textos.aceptar_registro(textos)


class ListarMisAceptaciones:
    def __init__(self, textos: RepositorioTextos) -> None:
        self._textos = textos

    async def ejecutar(self, id_actor: UUID) -> list[Aceptacion]:
        return await self._textos.listar_aceptaciones(id_actor)


class ListarAceptacionesDeUsuario:
    def __init__(self, usuarios: RepositorioUsuarios, textos: RepositorioTextos) -> None:
        self._usuarios = usuarios
        self._textos = textos

    async def ejecutar(self, id_actor: UUID, id_usuario: UUID) -> list[Aceptacion]:
        await exigir_administrador(self._usuarios, id_actor)
        if await self._usuarios.obtener_por_id(id_usuario) is None:
            raise NoEncontrado("No existe el usuario.")
        return await self._textos.listar_aceptaciones(id_usuario)
