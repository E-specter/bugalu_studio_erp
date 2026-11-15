from uuid import UUID

from psycopg import AsyncConnection, errors, sql

from bugalu.compartido.errores import Conflicto
from bugalu.modulos.identidad.dominio.solicitud import EstadoSolicitud, Solicitud

_SELECT = sql.SQL(
    "select s.id, s.id_usuario, u.nombre, public.correo_de_usuario(s.id_usuario), "
    "s.especialidad, s.mensaje, s.estado, s.motivo, s.creada_en, s.revisada_en "
    "from public.solicitud_acceso s join public.usuario u on u.id = s.id_usuario"
)


class RepositorioSolicitudesPostgres:
    """Recibe la transaccion con identidad (ADR-007): la RLS decide que solicitudes se ven."""

    def __init__(self, conexion: AsyncConnection) -> None:
        self._conexion = conexion

    async def crear(self, id_usuario: UUID, especialidad: str, mensaje: str | None) -> Solicitud:
        try:
            cursor = await self._conexion.execute(
                "insert into public.solicitud_acceso (id_usuario, especialidad, mensaje) "
                "values (%s, %s, %s) returning id",
                (id_usuario, especialidad, mensaje),
            )
        except errors.UniqueViolation as error:  # indice unico parcial: una sola pendiente
            raise Conflicto("Ya tienes una solicitud pendiente.") from error
        fila = await cursor.fetchone()
        solicitud = await self.obtener(fila[0]) if fila else None
        if solicitud is None:
            raise LookupError("La solicitud desaparecio durante la transaccion.")
        return solicitud

    async def obtener_ultima_de(self, id_usuario: UUID) -> Solicitud | None:
        return await self._uno(
            _SELECT + sql.SQL(" where s.id_usuario = %s order by s.creada_en desc limit 1"),
            (id_usuario,),
        )

    async def listar(self, estado: EstadoSolicitud | None) -> list[Solicitud]:
        async with self._conexion.cursor() as cursor:
            await cursor.execute(
                _SELECT
                + sql.SQL(" where (%s::text is null or s.estado = %s) order by s.creada_en"),
                (estado, estado),
            )
            return [_solicitud(fila) for fila in await cursor.fetchall()]

    async def obtener(self, id_solicitud: UUID) -> Solicitud | None:
        return await self._uno(_SELECT + sql.SQL(" where s.id = %s"), (id_solicitud,))

    async def resolver(
        self, id_solicitud: UUID, estado: EstadoSolicitud, id_revisor: UUID, motivo: str | None
    ) -> Solicitud | None:
        cursor = await self._conexion.execute(
            "update public.solicitud_acceso "
            "set estado = %s, motivo = %s, id_revisor = %s, revisada_en = now() "
            "where id = %s and estado = 'pendiente' returning id",
            (estado, motivo, id_revisor, id_solicitud),
        )
        return await self.obtener(id_solicitud) if await cursor.fetchone() else None

    async def _uno(
        self, consulta: sql.Composed, parametros: tuple[object, ...]
    ) -> Solicitud | None:
        async with self._conexion.cursor() as cursor:
            await cursor.execute(consulta, parametros)
            fila = await cursor.fetchone()
        return _solicitud(fila) if fila else None


def _solicitud(fila: tuple[object, ...]) -> Solicitud:
    id_, id_usuario, nombre, correo, especialidad, mensaje, estado, motivo, creada, revisada = fila
    return Solicitud(
        id=id_,  # type: ignore[arg-type]
        id_usuario=id_usuario,  # type: ignore[arg-type]
        nombre=nombre,  # type: ignore[arg-type]
        correo=correo,  # type: ignore[arg-type]
        especialidad=especialidad,  # type: ignore[arg-type]
        mensaje=mensaje,  # type: ignore[arg-type]
        estado=EstadoSolicitud(estado),  # type: ignore[arg-type]
        motivo=motivo,  # type: ignore[arg-type]
        creada_en=creada,  # type: ignore[arg-type]
        revisada_en=revisada,  # type: ignore[arg-type]
    )
