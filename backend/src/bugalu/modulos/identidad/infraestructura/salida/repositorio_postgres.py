from collections.abc import Mapping
from typing import Any
from uuid import UUID

from psycopg import AsyncConnection, errors, sql
from psycopg.types.json import Jsonb

from bugalu.compartido.errores import TextoDesactualizado
from bugalu.modulos.identidad.dominio.usuario import (
    CONSENTIMIENTOS,
    Documento,
    Pendiente,
    Rol,
    Usuario,
)
from bugalu.modulos.identidad.infraestructura.salida.errores_postgres import (
    traduciendo_errores_de_postgres,
)

_EDITABLES = frozenset(
    {
        "nombre",
        "telefono",
        "nombre_artistico",
        "modalidad",
        "documento",
        "domicilio",
        "redes",
        "integrantes",
        "es_menor",
    }
)
_SELECT = sql.SQL(
    "select u.id, u.nombre, u.rol, u.especialidad, u.telefono, u.nombre_artistico, "
    "public.correo_de_usuario(u.id), u.correo_verificado_en is not null, u.modalidad, "
    "u.documento_tipo, u.documento_numero, u.domicilio, u.redes, u.integrantes, u.es_menor, "
    "u.documento_numero is not null and exists (select 1 from public.usuario o "
    "where o.documento_tipo = u.documento_tipo and o.documento_numero = u.documento_numero "
    "and o.id <> u.id) as documento_repetido "
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

    async def listar(
        self, rol: Rol | None, documento_repetido: bool | None = None
    ) -> list[Usuario]:
        async with self._conexion.cursor() as cursor:
            await cursor.execute(
                _SELECT + sql.SQL(" where (%s::text is null or u.rol = %s) order by u.creado_en"),
                (rol, rol),
            )
            usuarios = [_usuario(fila) for fila in await cursor.fetchall()]
        # shortcut: marca calculada al leer, filtrada aqui; subir a SQL si la lista crece.
        return [
            u
            for u in usuarios
            if documento_repetido is None or u.documento_repetido == documento_repetido
        ]

    async def actualizar_perfil(self, id_usuario: UUID, cambios: Mapping[str, Any]) -> Usuario:
        if not cambios.keys() <= _EDITABLES:
            raise ValueError("Campo no editable por el usuario.")
        columnas = _columnas(cambios)
        asignaciones = sql.SQL(", ").join(
            sql.SQL("{} = %s").format(sql.Identifier(campo)) for campo in columnas
        )
        consulta = sql.SQL("update public.usuario set {} where id = %s").format(asignaciones)
        await self._conexion.execute(consulta, (*columnas.values(), id_usuario))
        usuario = await self.obtener_por_id(id_usuario)
        if usuario is None:
            raise LookupError("El perfil desaparecio durante la transaccion.")
        return usuario

    async def pendientes(self) -> list[Pendiente]:
        cursor = await self._conexion.execute(
            "select tipo, version, contexto, motivo from public.mis_pendientes()"
        )
        return [Pendiente(*fila) for fila in await cursor.fetchall()]

    async def campos_faltantes_para_reservar(self) -> list[str]:
        cursor = await self._conexion.execute("select public.campos_faltantes_para_reservar()")
        fila = await cursor.fetchone()
        return list(fila[0]) if fila and fila[0] else []

    async def consentimientos(self, id_usuario: UUID) -> dict[str, bool]:
        cursor = await self._conexion.execute(
            "select consentimiento from public.aceptacion "
            "where id_usuario = %s and consentimiento is not null and retirada_en is null",
            (id_usuario,),
        )
        activos = {fila[0] for fila in await cursor.fetchall()}
        return {c: c in activos for c in CONSENTIMIENTOS}

    async def cambiar_consentimiento(self, consentimiento: str, dar: bool) -> None:
        try:
            await self._conexion.execute(
                "select public.cambiar_consentimiento(%s, %s)", (consentimiento, dar)
            )
        except errors.RaiseException as error:
            if error.diag.message_primary == "texto_desactualizado":  # texto sin version vigente
                raise TextoDesactualizado(
                    "No hay una version vigente del texto.", {"vigente": None}
                ) from None
            raise

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


def _columnas(cambios: Mapping[str, Any]) -> dict[str, Any]:
    columnas: dict[str, Any] = {}
    for campo, valor in cambios.items():
        if campo == "documento":
            columnas["documento_tipo"], columnas["documento_numero"] = (
                valor["tipo"],
                valor["numero"],
            )
        elif campo in ("redes", "integrantes"):
            columnas[campo] = Jsonb(list(valor))
        else:
            columnas[campo] = valor
    return columnas


def _usuario(fila: tuple[object, ...]) -> Usuario:
    (
        id_,
        nombre,
        rol,
        especialidad,
        telefono,
        nombre_artistico,
        correo,
        confirmado,
        modalidad,
        doc_tipo,
        doc_numero,
        domicilio,
        redes,
        integrantes,
        es_menor,
        repetido,
    ) = fila
    return Usuario(
        id=id_,  # type: ignore[arg-type]
        nombre=nombre,  # type: ignore[arg-type]
        rol=Rol(rol),  # type: ignore[arg-type]
        especialidad=especialidad,  # type: ignore[arg-type]
        telefono=telefono,  # type: ignore[arg-type]
        nombre_artistico=nombre_artistico,  # type: ignore[arg-type]
        correo=correo,  # type: ignore[arg-type]
        correo_confirmado=bool(confirmado),
        modalidad=modalidad,  # type: ignore[arg-type]
        documento=Documento(doc_tipo, doc_numero) if doc_tipo else None,  # type: ignore[arg-type]
        domicilio=domicilio,  # type: ignore[arg-type]
        redes=tuple(redes),  # type: ignore[arg-type]
        integrantes=tuple(integrantes),  # type: ignore[arg-type]
        es_menor=bool(es_menor),
        documento_repetido=bool(repetido),
    )
