from collections.abc import Collection, Mapping, Sequence
from datetime import date
from decimal import Decimal
from typing import Any
from uuid import UUID

from psycopg import AsyncConnection, errors, sql

from bugalu.compartido.errores import FeriadoRepetido
from bugalu.modulos.catalogo.dominio.precio import (
    Especialista,
    Feriado,
    Recargos,
    Servicio,
    Unidad,
)

_CAMPOS_SERVICIO = frozenset({"tarifa_hora", "monto_fijo", "activo"})
_CAMPOS_ESPECIALISTA = frozenset({"monto_fijo", "monto_variable", "unidad", "activo"})
_SERVICIO = sql.SQL(
    "select s.id, s.nombre, s.categoria, s.ocupa_sala, s.tarifa_hora, s.monto_fijo, "
    "array(select se.id_especialista from public.servicio_especialista se "
    "join public.especialista e on e.id = se.id_especialista "
    "where se.id_servicio = s.id order by e.nombre), s.activo from public.servicio s"
)
_ESPECIALISTA = sql.SQL(
    "select id, nombre, monto_fijo, monto_variable, unidad, activo from public.especialista"
)


class RepositorioCatalogoPostgres:
    """Recibe una transaccion ya abierta (publica o con identidad): la RLS decide el acceso."""

    def __init__(self, conexion: AsyncConnection) -> None:
        self._conexion = conexion

    async def _filas(
        self, consulta: str | sql.SQL | sql.Composed, parametros: Sequence[Any] = ()
    ) -> list[Any]:
        cursor = await self._conexion.execute(consulta, parametros)
        return await cursor.fetchall()

    async def es_administrador(self) -> bool:
        return bool((await self._filas("select public.es_administrador()"))[0][0])

    async def existe_sala(self, id_sala: UUID) -> bool:
        filas = await self._filas(
            "select 1 from public.sala_tecnica where id = %s and activa", (id_sala,)
        )
        return bool(filas)

    async def listar_servicios(self) -> list[Servicio]:
        return [_servicio(f) for f in await self._filas(_SERVICIO + sql.SQL(" order by s.nombre"))]

    async def obtener_servicio(self, id_servicio: UUID) -> Servicio | None:
        filas = await self._filas(_SERVICIO + sql.SQL(" where s.id = %s"), (id_servicio,))
        return _servicio(filas[0]) if filas else None

    async def actualizar_servicio(
        self, id_servicio: UUID, cambios: Mapping[str, Decimal | bool]
    ) -> None:
        await self._actualizar("servicio", _CAMPOS_SERVICIO, id_servicio, cambios)

    async def reemplazar_especialistas_por_defecto(
        self, id_servicio: UUID, ids: Sequence[UUID]
    ) -> None:
        await self._conexion.execute(
            "delete from public.servicio_especialista where id_servicio = %s", (id_servicio,)
        )
        for id_especialista in ids:
            await self._conexion.execute(
                "insert into public.servicio_especialista (id_servicio, id_especialista) "
                "values (%s, %s)",
                (id_servicio, id_especialista),
            )

    async def listar_especialistas(self) -> list[Especialista]:
        filas = await self._filas(_ESPECIALISTA + sql.SQL(" order by nombre"))
        return [_especialista(f) for f in filas]

    async def obtener_especialistas(self, ids: Collection[UUID]) -> list[Especialista]:
        filas = await self._filas(_ESPECIALISTA + sql.SQL(" where id = any(%s)"), (list(ids),))
        return [_especialista(f) for f in filas]

    async def actualizar_especialista(
        self, id_especialista: UUID, cambios: Mapping[str, Decimal | bool | str]
    ) -> Especialista | None:
        await self._actualizar("especialista", _CAMPOS_ESPECIALISTA, id_especialista, cambios)
        encontrados = await self.obtener_especialistas([id_especialista])
        return encontrados[0] if encontrados else None

    async def _actualizar(
        self, tabla: str, permitidos: frozenset[str], id_fila: UUID, cambios: Mapping[str, Any]
    ) -> None:
        if not cambios.keys() <= permitidos:
            raise ValueError("Campo no editable.")
        asignaciones = sql.SQL(", ").join(
            sql.SQL("{} = %s").format(sql.Identifier(campo)) for campo in cambios
        )
        await self._conexion.execute(
            sql.SQL("update public.{} set {} where id = %s").format(
                sql.Identifier(tabla), asignaciones
            ),
            (*(v.value if isinstance(v, Unidad) else v for v in cambios.values()), id_fila),
        )

    async def obtener_recargos(self) -> Recargos:
        filas = {
            f[0]: f
            for f in await self._filas("select tipo, porcentaje, desde, hasta from public.recargo")
        }
        noche = filas["noche"]
        return Recargos(
            noche=noche[1],
            desde_noche=noche[2],
            hasta_noche=noche[3],
            fin_de_semana=filas["fin_de_semana"][1],
            feriado=filas["feriado"][1],
        )

    async def guardar_recargos(self, recargos: Recargos) -> None:
        # Una sola transaccion: o se guardan los tres tipos o ninguno.
        for tipo, porcentaje, desde, hasta in (
            ("noche", recargos.noche, recargos.desde_noche, recargos.hasta_noche),
            ("fin_de_semana", recargos.fin_de_semana, None, None),
            ("feriado", recargos.feriado, None, None),
        ):
            await self._conexion.execute(
                "insert into public.recargo (tipo, porcentaje, desde, hasta) "
                "values (%s, %s, %s, %s) "
                "on conflict (tipo) do update set porcentaje = excluded.porcentaje, "
                "desde = excluded.desde, hasta = excluded.hasta",
                (tipo, porcentaje, desde, hasta),
            )

    async def listar_feriados(self, anio: int | None) -> list[Feriado]:
        filas = await self._filas(
            "select fecha, nombre from public.feriado "
            "where (%s::int is null or extract(year from fecha) = %s) order by fecha",
            (anio, anio),
        )
        return [Feriado(*f) for f in filas]

    async def feriados_en(self, fechas: Collection[date]) -> frozenset[date]:
        filas = await self._filas(
            "select fecha from public.feriado where fecha = any(%s)", (list(fechas),)
        )
        return frozenset(f[0] for f in filas)

    async def agregar_feriado(self, feriado: Feriado) -> None:
        try:
            await self._conexion.execute(
                "insert into public.feriado (fecha, nombre) values (%s, %s)",
                (feriado.fecha, feriado.nombre),
            )
        except errors.UniqueViolation as error:
            raise FeriadoRepetido("Ya existe un feriado en esa fecha.") from error

    async def eliminar_feriado(self, fecha: date) -> bool:
        cursor = await self._conexion.execute(
            "delete from public.feriado where fecha = %s", (fecha,)
        )
        return cursor.rowcount > 0


def _servicio(f: Sequence[Any]) -> Servicio:
    return Servicio(f[0], f[1], f[2], f[3], f[4], f[5], tuple(f[6]), f[7])


def _especialista(f: Sequence[Any]) -> Especialista:
    return Especialista(f[0], f[1], f[2], f[3], Unidad(f[4]), f[5])
