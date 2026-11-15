from collections.abc import Mapping
from uuid import UUID

from psycopg import AsyncConnection, sql

from bugalu.modulos.identidad.dominio.usuario import Rol, Usuario
from bugalu.modulos.identidad.infraestructura.salida.errores_postgres import (
    traduciendo_errores_de_postgres,
)

_EDITABLES = frozenset({"nombre", "telefono", "nombre_artistico"})
_SELECT = sql.SQL(
    "select u.id, u.nombre, u.rol, u.especialidad, u.telefono, u.nombre_artistico, "
    "public.correo_de_usuario(u.id), u.correo_verificado_en is not null "
    "from public.usuario u"
)


class RepositorioPostgres:
    """Recibe la transaccion con identidad (ADR-007): la RLS decide que filas ve el usuario."""

    def __init__(self, conexion: AsyncConnection) -> None:
        self._conexion = conexion

    async def obtener_por_id(self, id_usuario: UUID) -> Usuario | None:
        async with self._conexion.cursor() as cursor:
            await cursor.execute(_SELECT + sql.SQL(" where u.id = %s"), (id_usuario,))
            fila = await cursor.fetchone()
        return _usuario(fila) if fila else None

    async def listar(self, rol: Rol | None) -> list[Usuario]:
        async with self._conexion.cursor() as cursor:
            await cursor.execute(
                _SELECT + sql.SQL(" where (%s::text is null or u.rol = %s) order by u.creado_en"),
                (rol, rol),
            )
            return [_usuario(fila) for fila in await cursor.fetchall()]

    async def actualizar_perfil(
        self, id_usuario: UUID, cambios: Mapping[str, str | None]
    ) -> Usuario:
        if not cambios.keys() <= _EDITABLES:
            raise ValueError("Campo no editable por el usuario.")
        asignaciones = sql.SQL(", ").join(
            sql.SQL("{} = %s").format(sql.Identifier(campo)) for campo in cambios
        )
        consulta = sql.SQL("update public.usuario set {} where id = %s").format(asignaciones)
        await self._conexion.execute(consulta, (*cambios.values(), id_usuario))
        usuario = await self.obtener_por_id(id_usuario)
        if usuario is None:
            raise LookupError("El perfil desaparecio durante la transaccion.")
        return usuario

    async def marcar_correo_verificado(self, id_usuario: UUID) -> bool:
        # La funcion usa auth.uid() (la identidad de la transaccion); id_usuario es el mismo.
        with traduciendo_errores_de_postgres():
            cursor = await self._conexion.execute("select public.marcar_correo_verificado()")
            fila = await cursor.fetchone()
        return bool(fila and fila[0])

    async def asignar_rol(self, id_usuario: UUID, rol: Rol, especialidad: str | None) -> None:
        with traduciendo_errores_de_postgres():
            await self._conexion.execute(
                "select public.asignar_rol(%s, %s, %s)", (id_usuario, rol.value, especialidad)
            )


def _usuario(fila: tuple[object, ...]) -> Usuario:
    id_, nombre, rol, especialidad, telefono, nombre_artistico, correo, confirmado = fila
    return Usuario(
        id=id_,  # type: ignore[arg-type]
        nombre=nombre,  # type: ignore[arg-type]
        rol=Rol(rol),  # type: ignore[arg-type]
        especialidad=especialidad,  # type: ignore[arg-type]
        telefono=telefono,  # type: ignore[arg-type]
        nombre_artistico=nombre_artistico,  # type: ignore[arg-type]
        correo=correo,  # type: ignore[arg-type]
        correo_confirmado=bool(confirmado),
    )
