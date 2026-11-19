from collections.abc import Sequence
from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from psycopg import AsyncConnection, errors
from psycopg.types.json import Jsonb

from bugalu.compartido.errores import (
    DuracionNoOfrecida,
    FueraDeHorario,
    HorarioNoDisponible,
    NoEditable,
    NoEncontrado,
    SinPermiso,
    TextoDesactualizado,
)
from bugalu.modulos.asesorias.dominio.asesoria import (
    Asesoria,
    NuevaAsesoria,
    PersonaAsesoria,
)
from bugalu.modulos.asesorias.dominio.modelos import Horario, Profesional
from bugalu.modulos.asesorias.infraestructura.salida.repositorio_postgres import (
    RepositorioAsesoriasPostgres,
)
from bugalu.modulos.catalogo.dominio.precio import ConfiguracionImpuestos
from bugalu.modulos.reservas.dominio.modelos import Politica, RequisitosReserva
from bugalu.modulos.reservas.infraestructura.salida.repositorio_postgres import (
    RepositorioReservasPostgres,
)

_TOPE_LISTA = 500
_SELECT = (
    "select r.id, r.folio, r.estado, r.motivo_cancelacion, r.inicio, r.fin, r.precio, "
    "r.vence_pago, r.id_cliente, r.id_profesional, a.modalidad, a.lugar, a.enlace, "
    "a.realizada_en, r.parametros_aplicados "
    "from public.reserva r join public.asesoria a on a.id_reserva = r.id "
    "where r.tipo = 'asesoria' "
)
# Mensajes de la barrera de la base (validar_asesoria_nueva) a su error de negocio.
_BARRERA = {
    "fuera_de_horario": (FueraDeHorario, "La asesoria completa no cabe en un horario publicado."),
    "duracion_no_ofrecida": (DuracionNoOfrecida, "El profesional no ofrece esa duracion."),
    "profesional_no_publicado": (NoEncontrado, "No existe el profesional."),
}


class RepositorioAgendaPostgres:
    """Recibe una transaccion con identidad. Compone los repositorios de reservas y de
    profesionales para no repetir sus consultas."""

    def __init__(self, conexion: AsyncConnection) -> None:
        self._conexion = conexion
        self._reservas = RepositorioReservasPostgres(conexion)
        self._perfiles = RepositorioAsesoriasPostgres(conexion)

    async def _filas(self, consulta: str, parametros: Sequence[Any] = ()) -> list[Any]:
        cursor = await self._conexion.execute(consulta, parametros)
        return await cursor.fetchall()

    async def es_administrador(self) -> bool:
        return await self._reservas.es_administrador()

    async def es_profesional(self) -> bool:
        return bool((await self._filas("select public.es_profesional()"))[0][0])

    async def requisitos_para_reservar(self) -> RequisitosReserva:
        return await self._reservas.requisitos_para_reservar()

    async def limites_reserva(self) -> tuple[int, int]:
        return await self._reservas.limites_reserva()

    async def plazos_pago(self) -> tuple[int, int]:
        return await self._reservas.plazos_pago()

    async def obtener_profesional(self, id_profesional: UUID) -> Profesional | None:
        return await self._perfiles.obtener_profesional(id_profesional)

    async def obtener_impuestos(self) -> ConfiguracionImpuestos:
        return await self._perfiles.obtener_impuestos()

    async def listar_horarios(
        self, id_profesional: UUID, desde: datetime, hasta: datetime
    ) -> list[Horario]:
        return await self._perfiles.listar_horarios(id_profesional, desde, hasta)

    async def insertar_asesoria(self, nueva: NuevaAsesoria) -> UUID:
        try:
            id_asesoria: UUID = (
                await self._filas(
                    "insert into public.reserva (tipo, id_cliente, id_profesional, inicio, fin, "
                    "precio, total, vence_pago) "
                    "values ('asesoria', (select auth.uid()), %s, %s, %s, %s, %s, %s) "
                    "returning id",
                    (
                        nueva.id_profesional,
                        nueva.inicio,
                        nueva.fin,
                        Jsonb(nueva.precio),
                        nueva.total,
                        nueva.vence_pago,
                    ),
                )
            )[0][0]
        except errors.ExclusionViolation:  # CA-07: la base decide el solape
            raise HorarioNoDisponible("Ese horario ya no esta disponible.") from None
        except errors.RaiseException as error:
            clase, mensaje = _BARRERA.get(error.diag.message_primary or "", (None, ""))
            if clase is None:
                raise
            raise clase(mensaje) from None
        await self._conexion.execute(
            "insert into public.asesoria (id_reserva, modalidad) values (%s, %s)",
            (id_asesoria, nueva.modalidad),
        )
        await self._conexion.execute(
            "insert into public.cuota (id_reserva, hito, monto) values (%s, 'al_reservar', %s)",
            (id_asesoria, nueva.total),
        )
        return id_asesoria

    async def aceptar_condiciones(self, id_asesoria: UUID, version: str) -> None:
        try:
            await self._conexion.execute(
                "select public.aceptar_condiciones('asesoria', %s, %s)", (id_asesoria, version)
            )
        except errors.RaiseException as error:
            if error.diag.message_primary == "texto_desactualizado":
                raise TextoDesactualizado(
                    "Las condiciones dejaron de ser la version vigente."
                ) from None
            raise

    async def encolar_aviso(self, id_asesoria: UUID) -> None:
        await self._conexion.execute("select public.encolar_aviso_reserva(%s)", (id_asesoria,))

    async def _asesorias(
        self, condicion: str, parametros: Sequence[Any], detalle: bool
    ) -> list[Asesoria]:
        filas = await self._filas(
            f"{_SELECT} and {condicion} order by r.inicio, r.folio limit {_TOPE_LISTA}",
            parametros,
        )
        if not filas:
            return []
        ids = [f[0] for f in filas]
        profesionales = {
            f[0]: PersonaAsesoria(f[1], f[2], f[3])
            for f in await self._filas(
                "select id_reserva, id, nombre, nombre_artistico "
                "from public.profesional_de_asesorias(%s)",
                (ids,),
            )
        }
        contactos = {  # solo para el profesional de la cita y el administrador
            f[0]: PersonaAsesoria(f[1], f[2], f[3], f[4], f[5])
            for f in await self._filas(
                "select id_reserva, id, nombre, nombre_artistico, telefono, correo "
                "from public.contacto_de_asesorias(%s)",
                (ids,),
            )
        }
        cuotas = await self._reservas.cuotas_de({f[0]: f[2] for f in filas}) if detalle else {}
        resultado = []
        for f in filas:
            notas = None
            version = None
            if detalle:
                notas = (await self._filas("select public.notas_de_asesoria(%s)", (f[0],)))[0][0]
                version = (
                    await self._filas(
                        "select version from public.aceptacion "
                        "where contexto = 'asesoria' and id_operacion = %s",
                        (f[0],),
                    )
                    or [(None,)]
                )[0][0]
            de_la_cita = tuple(cuotas.get(f[0], ()))
            resultado.append(
                Asesoria(
                    id=f[0],
                    folio=f[1],
                    estado=f[2],
                    motivo_cancelacion=f[3],
                    inicio=f[4],
                    fin=f[5],
                    precio=f[6],
                    vence_pago=f[7],
                    id_cliente=f[8],
                    profesional=profesionales.get(f[0], PersonaAsesoria(f[9], None, None)),
                    modalidad=f[10],
                    lugar=f[11],
                    enlace=f[12],
                    realizada_en=f[13],
                    cuotas=de_la_cita if detalle else None,
                    pagado=sum((c.pagado for c in de_la_cita), Decimal("0.00"))
                    if detalle
                    else None,
                    politica=Politica.desde_parametros(f[14]) if detalle else None,
                    version_condiciones=version,
                    cliente=contactos.get(f[0]),
                    notas=notas,
                )
            )
        return resultado

    async def obtener_asesoria(self, id_asesoria: UUID) -> Asesoria | None:
        encontradas = await self._asesorias("r.id = %s", (id_asesoria,), True)
        return encontradas[0] if encontradas else None

    async def listar_mias(self) -> list[Asesoria]:
        return await self._asesorias("r.id_cliente = (select auth.uid())", (), False)

    async def listar(
        self,
        estado: str | None,
        desde: datetime | None,
        hasta: datetime | None,
        id_profesional: UUID | None,
        por_cerrar_antes_de: datetime | None,
    ) -> list[Asesoria]:
        condiciones, parametros = ["true"], []
        for sql, valor in (
            ("r.estado = %s", estado),
            ("r.inicio >= %s", desde),
            ("r.inicio < %s", hasta),
            ("r.id_profesional = %s", id_profesional),
            ("r.fin <= %s", por_cerrar_antes_de),
        ):
            if valor is not None:
                condiciones.append(sql)
                parametros.append(valor)
        return await self._asesorias(" and ".join(condiciones), parametros, False)

    async def cambiar_encuentro(
        self, id_asesoria: UUID, modalidad: str, lugar: str | None, enlace: str | None
    ) -> None:
        try:
            await self._conexion.execute(
                "select public.cambiar_encuentro(%s, %s, %s, %s)",
                (id_asesoria, modalidad, lugar, enlace),
            )
        except errors.NoDataFound:
            raise NoEncontrado("No existe la asesoria.") from None
        except errors.InsufficientPrivilege:
            raise SinPermiso(
                "Solo su profesional o un administrador cambia el encuentro."
            ) from None
        except errors.RaiseException as error:
            if error.diag.message_primary == "no_editable":
                raise NoEditable("La asesoria ya no admite cambios de encuentro.") from None
            raise
