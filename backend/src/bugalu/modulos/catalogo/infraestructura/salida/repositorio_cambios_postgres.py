from collections.abc import Mapping
from datetime import datetime
from typing import Any
from uuid import UUID

from psycopg import AsyncConnection
from psycopg.types.json import Jsonb

from bugalu.modulos.catalogo.dominio.cambios_sensibles import CambioRegistrado, Confirmacion

_COLUMNAS = (
    "id, cambiado_en, id_autor, autor_nombre, recurso, id_recurso, nombre_recurso, campo, "
    "anterior, nuevo"
)


class RepositorioCambiosPostgres:
    """Recibe una transaccion con identidad: RLS y funciones de la base exigen administrador."""

    def __init__(self, conexion: AsyncConnection) -> None:
        self._conexion = conexion

    async def _filas(self, consulta: str, parametros: tuple[Any, ...] = ()) -> list[Any]:
        return await (await self._conexion.execute(consulta, parametros)).fetchall()

    async def id_usuario(self) -> UUID:
        return UUID(str((await self._filas("select auth.uid()"))[0][0]))

    async def guardar_confirmacion(
        self,
        hash_token: str,
        recurso: str,
        id_recurso: UUID | None,
        nombre_recurso: str,
        cambios: Mapping[str, tuple[str, str]],
        minutos: int,
    ) -> datetime:
        guardados = {c: {"anterior": a, "nuevo": n} for c, (a, n) in cambios.items()}
        filas = await self._filas(
            "select public.crear_confirmacion(%s, %s, %s, %s, %s, %s)",
            (hash_token, recurso, id_recurso, nombre_recurso, Jsonb(guardados), minutos),
        )
        expira: datetime = filas[0][0]
        return expira

    async def tomar_confirmacion(self, hash_token: str) -> Confirmacion | None:
        filas = await self._filas(
            "select id, id_autor, recurso, id_recurso, nombre_recurso, cambios, vigente "
            "from public.confirmacion_para_aplicar(%s)",
            (hash_token,),
        )
        if not filas:
            return None
        i, autor, recurso, id_recurso, nombre, cambios, vigente = filas[0]
        return Confirmacion(
            i,
            autor,
            recurso,
            id_recurso,
            nombre,
            {c: (v["anterior"], v["nuevo"]) for c, v in cambios.items()},
            vigente,
        )

    async def aplicar(self, confirmacion: Confirmacion) -> list[CambioRegistrado]:
        await self._conexion.execute(
            "select public.aplicar_cambio_confirmado(%s)", (confirmacion.id,)
        )
        # Las filas de esta transaccion comparten `cambiado_en` (now()).
        filas = await self._filas(
            f"select {_COLUMNAS} from public.registro_cambio "
            "where cambiado_en = now() and id_autor = %s and recurso = %s "
            "and id_recurso is not distinct from %s order by campo",
            (confirmacion.id_autor, confirmacion.recurso, confirmacion.id_recurso),
        )
        return [CambioRegistrado(*f) for f in filas]

    async def listar(
        self, desde: datetime, hasta: datetime, recurso: str | None
    ) -> list[CambioRegistrado]:
        filas = await self._filas(
            f"select {_COLUMNAS} from public.registro_cambio "
            "where cambiado_en >= %s and cambiado_en < %s and (%s::text is null or recurso = %s) "
            "order by cambiado_en desc, campo",
            (desde, hasta, recurso, recurso),
        )
        return [CambioRegistrado(*f) for f in filas]
