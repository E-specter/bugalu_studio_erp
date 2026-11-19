from collections.abc import Collection, Mapping, Sequence
from datetime import date
from decimal import Decimal
from typing import Any
from uuid import UUID

from psycopg import AsyncConnection, errors, sql

from bugalu.compartido.errores import FeriadoRepetido
from bugalu.modulos.catalogo.dominio.precio import (
    ConfiguracionImpuestos,
    Especialista,
    Feriado,
    Recargos,
    Servicio,
    Unidad,
)

# Solo lo no sensible se escribe directo: los campos sensibles los aplica aplicar_cambio_confirmado.
_CAMPOS_SERVICIO = frozenset({"activo"})
_CAMPOS_ESPECIALISTA = frozenset({"activo"})
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
        # Serializa reemplazos concurrentes (si no: UniqueViolation o listas mezcladas); "no key"
        # no frena el insert de reservas (FK, key share).
        await self._conexion.execute(
            "select 1 from public.servicio where id = %s for no key update", (id_servicio,)
        )
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
        await self._actualizar_columnas(tabla, permitidos, cambios, id_fila)

    async def _actualizar_columnas(
        self,
        tabla: str,
        permitidos: frozenset[str],
        cambios: Mapping[str, Any],
        id_fila: UUID | None = None,
    ) -> None:
        """`id_fila` nulo: la tabla tiene una sola fila (configuracion_impuestos)."""
        if not cambios.keys() <= permitidos:
            raise ValueError("Campo no editable.")
        asignaciones = sql.SQL(", ").join(
            sql.SQL("{} = %s").format(sql.Identifier(campo)) for campo in cambios
        )
        valores = [v.value if isinstance(v, Unidad) else v for v in cambios.values()]
        consulta = sql.SQL("update public.{} set {}").format(sql.Identifier(tabla), asignaciones)
        if id_fila is not None:
            consulta += sql.SQL(" where id = %s")
            valores.append(id_fila)
        await self._conexion.execute(consulta, valores)

    async def obtener_parametros(self) -> dict[str, Any]:
        filas = await self._filas("select clave, valor from public.parametro")
        tarifa = (await self._filas("select tarifa_hora_gestion from public.configuracion_danos"))[
            0
        ][0]
        return {**{clave: int(valor) for clave, valor in filas}, "tarifa_hora_gestion": tarifa}

    async def bloquear_recurso(self, recurso: str, id_recurso: UUID | None) -> None:
        await self._conexion.execute(
            "select public.bloquear_recurso_sensible(%s, %s)", (recurso, id_recurso)
        )

    async def obtener_precios_profesional(
        self, id_profesional: UUID
    ) -> tuple[str, dict[str, str]] | None:
        filas = await self._filas(
            "select coalesce(public.nombre_profesional(p.id), 'Profesional'), "
            "(select to_char(precio, 'FM999999990.00') from public.precio_asesoria "
            " where id_profesional = p.id and minutos = 30), "
            "(select to_char(precio, 'FM999999990.00') from public.precio_asesoria "
            " where id_profesional = p.id and minutos = 60) "
            "from public.perfil_profesional p where p.id = %s",
            (id_profesional,),
        )
        if not filas:
            return None
        nombre, p30, p60 = filas[0]
        return nombre, {"precio_30": p30 or "no_ofrece", "precio_60": p60 or "no_ofrece"}

    async def contar_operaciones_vigentes(self) -> int:
        filas = await self._filas(
            "select count(*) from public.reserva "
            "where estado in ('pre_reservada', 'confirmada') and inicio > now()"
        )
        return int(filas[0][0])

    async def contar_asesorias_vigentes(self, id_profesional: UUID) -> int:
        filas = await self._filas(
            "select count(*) from public.reserva where tipo = 'asesoria' and id_profesional = %s "
            "and estado in ('pre_reservada', 'confirmada') and inicio > now()",
            (id_profesional,),
        )
        return int(filas[0][0])

    async def obtener_impuestos(self) -> ConfiguracionImpuestos:
        porcentaje, incluido = (
            await self._filas(
                "select porcentaje_igv, precios_incluyen_igv from public.configuracion_impuestos"
            )
        )[0]
        return ConfiguracionImpuestos(porcentaje, incluido)

    async def parametros_vigentes(self) -> dict[str, Any]:
        vigentes: dict[str, Any] = (await self._filas("select public.parametros_vigentes()"))[0][0]
        return vigentes

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
