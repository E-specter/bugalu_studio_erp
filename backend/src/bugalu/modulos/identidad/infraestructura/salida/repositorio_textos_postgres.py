from collections.abc import Mapping, Sequence
from typing import Any
from uuid import UUID

import psycopg
from psycopg import AsyncConnection
from psycopg.types.json import Jsonb

from bugalu.compartido.errores import (
    AvisoInsuficiente,
    NoEncontrado,
    SinPermiso,
    TextoDesactualizado,
    VersionInvalida,
    VersionProgramada,
    VersionVigente,
)
from bugalu.modulos.identidad.dominio.textos_legales import Aceptacion, TextoLegal

_TEXTO = (
    "tipo, version, tipo_cambio, contenido, resumenes, resumen_cambios, vigente_desde, "
    "publicado_en, vigente_desde > now()"
)
_ACEPTACION = "id, tipo, version, contexto, id_operacion, aceptada_en, retirada_en, aceptante"
# Mismo bloqueo que `publicar_texto_legal`: las publicaciones de un tipo se serializan.
_BLOQUEO = "select pg_advisory_xact_lock(20261208, hashtext(%s))"


def _texto(fila: Any) -> TextoLegal:
    return TextoLegal(*fila)


def _aceptacion(fila: Any) -> Aceptacion:
    return Aceptacion(*fila)


class RepositorioTextosPostgres:
    """Recibe la transaccion (publica o con identidad): la RLS y las funciones deciden el acceso."""

    def __init__(self, conexion: AsyncConnection) -> None:
        self._conexion = conexion

    async def _filas(self, consulta: str, parametros: Sequence[Any] = ()) -> list[Any]:
        cursor = await self._conexion.execute(consulta, parametros)
        return await cursor.fetchall()

    async def listar_publicos(self) -> list[TextoLegal]:
        filas = await self._filas(
            f"select {_TEXTO} from public.texto_legal where vigente_desde > now() "
            "or (tipo, version) in (select tipo, version from public.textos_vigentes()) "
            "order by tipo, vigente_desde"
        )
        return [_texto(f) for f in filas]

    async def obtener(self, tipo: str, version: str) -> TextoLegal | None:
        filas = await self._filas(
            f"select {_TEXTO} from public.texto_legal where tipo = %s and version = %s",
            (tipo, version),
        )
        return _texto(filas[0]) if filas else None

    async def vigentes(self) -> dict[str, TextoLegal]:
        filas = await self._filas(f"select {_TEXTO} from public.textos_vigentes()")
        return {f[0]: _texto(f) for f in filas}

    async def ultima_version(self, tipo: str) -> str | None:
        await self._conexion.execute(_BLOQUEO, (tipo,))
        filas = await self._filas(
            "select version from public.texto_legal where tipo = %s "
            "order by string_to_array(version, '.')::int[] desc limit 1",
            (tipo,),
        )
        return str(filas[0][0]) if filas else None

    async def publicar(
        self,
        tipo: str,
        version: str,
        tipo_cambio: str,
        contenido: str,
        resumenes: Mapping[str, str],
        resumen_cambios: str | None,
        vigente_desde: Any,
    ) -> TextoLegal:
        try:
            filas = await self._filas(
                f"select {_TEXTO} from public.publicar_texto_legal(%s, %s, %s, %s, %s, %s, %s)",
                (
                    tipo,
                    version,
                    tipo_cambio,
                    contenido,
                    Jsonb(dict(resumenes)),
                    resumen_cambios,
                    vigente_desde,
                ),
            )
        except psycopg.errors.InsufficientPrivilege as error:
            raise SinPermiso("Solo un administrador puede hacer esto.") from error
        except psycopg.errors.RaiseException as error:
            if error.diag.message_primary == "version_programada":
                raise VersionProgramada("Ya hay una version programada de este texto.") from error
            if (
                error.diag.message_primary == "version_invalida"
            ):  # la base repite las reglas de CA-02
                raise VersionInvalida("La version no es mayor que la ultima.") from error
            if error.diag.message_primary == "aviso_insuficiente":
                raise AvisoInsuficiente(
                    "Una version mayor o menor exige 15 dias de aviso."
                ) from error
            raise
        return _texto(filas[0])

    async def retirar(self, tipo: str, version: str) -> None:
        try:
            await self._conexion.execute(
                "select public.retirar_texto_legal(%s, %s)", (tipo, version)
            )
        except psycopg.errors.InsufficientPrivilege as error:
            raise SinPermiso("Solo un administrador puede hacer esto.") from error
        except psycopg.errors.NoDataFound as error:  # P0002
            raise NoEncontrado("No existe esa version del texto.") from error
        except psycopg.errors.RaiseException as error:
            if error.diag.message_primary == "version_vigente":
                raise VersionVigente("Una version vigente no se retira.") from error
            raise

    async def aceptar_registro(self, textos: Sequence[tuple[str, str]]) -> list[Aceptacion]:
        try:
            filas = await self._filas(
                f"select {_ACEPTACION} from public.aceptar_textos('registro', %s)",
                (Jsonb([{"tipo": t, "version": v} for t, v in textos]),),
            )
        except psycopg.errors.RaiseException as error:
            if error.diag.message_primary == "texto_desactualizado":  # carrera con una publicacion
                raise TextoDesactualizado("Un texto dejo de ser el vigente.") from error
            raise
        return [_aceptacion(f) for f in filas]

    async def listar_aceptaciones(self, id_usuario: UUID) -> list[Aceptacion]:
        filas = await self._filas(
            f"select {_ACEPTACION} from public.aceptacion where id_usuario = %s "
            "order by aceptada_en desc, tipo",
            (id_usuario,),
        )
        return [_aceptacion(f) for f in filas]
