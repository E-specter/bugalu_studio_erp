from uuid import UUID

from psycopg import AsyncConnection

from bugalu.modulos.identidad.dominio.usuario import Rol, Usuario


class RepositorioPostgres:
    """Recibe la transaccion con identidad (ADR-007): la RLS decide que filas ve el usuario."""

    def __init__(self, conexion: AsyncConnection) -> None:
        self._conexion = conexion

    async def obtener_por_id(self, id_usuario: UUID) -> Usuario | None:
        async with self._conexion.cursor() as cursor:
            await cursor.execute(
                "select id, nombre, rol, especialidad from public.usuario where id = %s",
                (id_usuario,),
            )
            fila = await cursor.fetchone()
        if fila is None:
            return None
        id_, nombre, rol, especialidad = fila
        return Usuario(id=id_, nombre=nombre, rol=Rol(rol), especialidad=especialidad)
