from collections.abc import Collection, Iterator, Mapping, Sequence
from contextlib import contextmanager
from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from psycopg import AsyncConnection, Error, errors
from psycopg.types.json import Jsonb

from bugalu.compartido.errores import (
    DatosInvalidos,
    EspecialidadDuplicada,
    HorarioConAsesorias,
    HorarioSolapado,
    NoEncontrado,
    PerfilExistente,
    RolNoAdmitido,
    SinPermiso,
    asesorias_vivas_en_lima,
)
from bugalu.modulos.asesorias.dominio.modelos import Especialidad, Horario, Ocupado, Profesional
from bugalu.modulos.catalogo.dominio.precio import ConfiguracionImpuestos
from bugalu.modulos.reservas.dominio.disponibilidad import Tramo

_TOPE_SUGERENCIA = 200
_PERFIL = (
    "select p.id, public.nombre_profesional(p.id), p.nombre_artistico, p.presentacion, p.redes, "
    "p.foto_ruta, p.activo, public.perfil_publicado(p.id), "
    "coalesce((select jsonb_agg(jsonb_build_object("
    "'id', e.id, 'nombre', e.nombre, 'activa', e.activa) order by e.nombre) "
    "from public.perfil_especialidad pe "
    "join public.especialidad_asesoria e on e.id = pe.id_especialidad "
    "where pe.id_profesional = p.id and e.activa), '[]'), "
    "coalesce((select jsonb_object_agg(pr.minutos::text, to_char(pr.precio, 'FM999999990.00')) "
    "from public.precio_asesoria pr where pr.id_profesional = p.id), '{}') "
    "from public.perfil_profesional p "
)


@contextmanager
def _traduciendo() -> Iterator[None]:
    try:
        yield
    except errors.InsufficientPrivilege as error:
        raise SinPermiso("No tienes permiso para esta operacion.") from error
    except errors.RaiseException as error:
        mensajes = {
            "perfil_existente": (PerfilExistente, "Ese usuario ya tiene un perfil de profesional."),
            "rol_no_admitido": (
                RolNoAdmitido,
                "El rol de ese usuario no admite un perfil de profesional.",
            ),
        }
        if caso := mensajes.get(error.diag.message_primary or ""):
            raise caso[0](caso[1]) from error
        raise
    except errors.InvalidParameterValue as error:
        raise DatosInvalidos(
            "Elige de 1 a 5 especialidades activas.", {"campo": "especialidades"}
        ) from error
    except errors.NoDataFound as error:  # P0002
        raise NoEncontrado("No existe el recurso.") from error


def _profesional(f: tuple[Any, ...]) -> Profesional:
    id_, nombre, artistico, presentacion, redes, foto, activo, publicado = f[:8]
    especialidades, precios = f[8], f[9]
    return Profesional(
        id_,
        nombre,
        artistico,
        presentacion,
        tuple(redes),
        tuple(Especialidad(UUID(e["id"]), e["nombre"], e["activa"]) for e in especialidades),
        foto,
        {int(m): Decimal(p) for m, p in precios.items()},
        activo,
        publicado,
    )


class RepositorioAsesoriasPostgres:
    """Recibe una transaccion abierta con `anon` o con la identidad del usuario: decide la RLS."""

    def __init__(self, conexion: AsyncConnection) -> None:
        self._conexion = conexion

    async def _filas(self, consulta: str, parametros: tuple[Any, ...] = ()) -> list[Any]:
        with _traduciendo():
            return await (await self._conexion.execute(consulta, parametros)).fetchall()

    async def es_administrador(self) -> bool:
        return bool((await self._filas("select public.es_administrador()"))[0][0])

    async def listar_especialidades(self, todas: bool) -> list[Especialidad]:
        filas = await self._filas(
            "select id, nombre, activa from public.especialidad_asesoria "
            "where activa or %s order by nombre",
            (todas,),
        )
        return [Especialidad(*f) for f in filas]

    async def crear_especialidad(self, nombre: str) -> Especialidad:
        try:
            filas = await self._filas(
                "insert into public.especialidad_asesoria (nombre) values (%s) "
                "returning id, nombre, activa",
                (nombre,),
            )
        except errors.UniqueViolation:
            raise EspecialidadDuplicada("Ya existe una especialidad con ese nombre.") from None
        return Especialidad(*filas[0])

    async def actualizar_especialidad(
        self, id_especialidad: UUID, cambios: Mapping[str, Any]
    ) -> Especialidad | None:
        columnas = [c for c in ("nombre", "activa") if c in cambios]
        asignar = ", ".join(f"{c} = %s" for c in columnas) or "id = id"
        try:
            filas = await self._filas(
                f"update public.especialidad_asesoria set {asignar} where id = %s "
                "returning id, nombre, activa",
                (*(cambios[c] for c in columnas), id_especialidad),
            )
        except errors.UniqueViolation:
            raise EspecialidadDuplicada("Ya existe una especialidad con ese nombre.") from None
        return Especialidad(*filas[0]) if filas else None

    async def listar_profesionales(
        self, id_especialidad: UUID | None, solo_publicados: bool
    ) -> list[Profesional]:
        filas = await self._filas(
            f"{_PERFIL} where (not %s or public.perfil_publicado(p.id)) "
            "and (%s::uuid is null or exists (select 1 from public.perfil_especialidad pe "
            "join public.especialidad_asesoria e on e.id = pe.id_especialidad "
            "where pe.id_profesional = p.id and pe.id_especialidad = %s and e.activa)) "
            "order by lower(coalesce(public.nombre_profesional(p.id), '')), p.id",
            (solo_publicados, id_especialidad, id_especialidad),
        )
        return [_profesional(f) for f in filas]

    async def obtener_profesional(
        self, id_profesional: UUID, para_actualizar: bool = False
    ) -> Profesional | None:
        bloqueo = " for update of p" if para_actualizar else ""
        filas = await self._filas(f"{_PERFIL} where p.id = %s{bloqueo}", (id_profesional,))
        return _profesional(filas[0]) if filas else None

    async def crear_perfil(self, id_usuario: UUID) -> None:
        await self._filas("select public.crear_perfil_de_usuario(%s)", (id_usuario,))

    async def actualizar_perfil(self, id_profesional: UUID, campos: Mapping[str, Any]) -> None:
        columnas = [c for c in ("nombre_artistico", "presentacion", "redes") if c in campos]
        valores = [Jsonb(list(campos[c])) if c == "redes" else campos[c] for c in columnas]
        await self._filas(
            "update public.perfil_profesional set "
            + ", ".join(f"{c} = %s" for c in columnas)
            + " where id = %s returning id",
            (*valores, id_profesional),
        )

    async def reemplazar_especialidades(self, id_profesional: UUID, ids: Collection[UUID]) -> None:
        await self._filas(
            "select public.reemplazar_especialidades(%s, %s)", (id_profesional, list(ids))
        )

    async def cambiar_estado(self, id_profesional: UUID, activo: bool) -> None:
        await self._filas(
            "select public.cambiar_estado_profesional(%s, %s)", (id_profesional, activo)
        )

    async def precios_texto(self, id_profesional: UUID) -> dict[str, str]:
        filas = await self._filas(
            "select minutos, to_char(precio, 'FM999999990.00') from public.precio_asesoria "
            "where id_profesional = %s",
            (id_profesional,),
        )
        existentes = {int(m): p for m, p in filas}
        return {f"precio_{m}": existentes.get(m, "no_ofrece") for m in (30, 60)}

    async def obtener_impuestos(self) -> ConfiguracionImpuestos:
        porcentaje, incluido = (
            await self._filas(
                "select porcentaje_igv, precios_incluyen_igv from public.configuracion_impuestos"
            )
        )[0]
        return ConfiguracionImpuestos(porcentaje, incluido)

    async def fijar_foto(self, id_profesional: UUID, ruta: str | None) -> None:
        filas = await self._filas(
            "update public.perfil_profesional set foto_ruta = %s where id = %s returning id",
            (ruta, id_profesional),
        )
        if not filas:  # la RLS no deja cambiarlo: nadie queda con una foto que no se guardo
            raise SinPermiso("No tienes permiso para esta operacion.")

    async def listar_horarios(
        self, id_profesional: UUID, desde: datetime, hasta: datetime
    ) -> list[Horario]:
        filas = await self._filas(
            "select id, id_profesional, inicio, fin from public.horario_profesional "
            "where id_profesional = %s and inicio < %s and fin > %s order by inicio",
            (id_profesional, hasta, desde),
        )
        return [Horario(*f) for f in filas]

    async def horarios_antes_de(self, id_profesional: UUID, instante: datetime) -> list[Horario]:
        filas = await self._filas(
            "select id, id_profesional, inicio, fin from public.horario_profesional "
            "where id_profesional = %s and inicio < %s order by inicio desc limit %s",
            (id_profesional, instante, _TOPE_SUGERENCIA),
        )
        return [Horario(*f) for f in filas]

    async def insertar_horarios(
        self, id_profesional: UUID, tramos: Sequence[Tramo]
    ) -> list[Horario]:
        nuevos = []
        for tramo in tramos:
            try:
                filas = await self._filas(
                    "insert into public.horario_profesional "
                    "(id_profesional, inicio, fin, id_publicador) "
                    "values (%s, %s, %s, (select auth.uid())) "
                    "returning id, id_profesional, inicio, fin",
                    (id_profesional, tramo.inicio, tramo.fin),
                )
            except errors.ExclusionViolation:
                raise HorarioSolapado("El bloque se solapa con otro del profesional.") from None
            nuevos.append(Horario(*filas[0]))
        return nuevos

    async def obtener_horario(self, id_profesional: UUID, id_horario: UUID) -> Horario | None:
        filas = await self._filas(
            "select id, id_profesional, inicio, fin from public.horario_profesional "
            "where id = %s and id_profesional = %s",
            (id_horario, id_profesional),
        )
        return Horario(*filas[0]) if filas else None

    async def retirar_horario(self, id_horario: UUID) -> None:
        try:
            await self._filas("select public.retirar_horario(%s)", (id_horario,))
        except Error as error:
            if error.sqlstate != "BG005":
                raise
            raise HorarioConAsesorias(
                "El horario tiene asesorias vivas.",
                {"asesorias": asesorias_vivas_en_lima(error.diag.message_detail)},
            ) from None

    async def ocupados_en(
        self, id_profesional: UUID, desde: datetime, hasta: datetime, excluir: UUID | None = None
    ) -> list[Ocupado]:
        filas = await self._filas(
            "select inicio, fin, propia from public.ocupacion_profesional(%s, %s, %s, %s)",
            (id_profesional, desde, hasta, excluir),
        )
        return [Ocupado(*f) for f in filas]

    async def limites_reserva(self) -> tuple[int, int]:
        minima, maxima = (await self._filas("select * from public.limites_reserva()"))[0]
        return int(minima), int(maxima)
