import json
from collections.abc import Mapping, Sequence
from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from psycopg import AsyncConnection, Error, errors
from psycopg.types.json import Jsonb

from bugalu.compartido.errores import (
    AvisoInvalido,
    DatosInvalidos,
    EleccionNoDisponible,
    ErrorDeNegocio,
    ExcepcionNoAplicable,
    ExcepcionYaAplicada,
    FranjaSolapada,
    LimiteReprogramaciones,
    NivelCambiado,
    NoAplicable,
    NoCancelable,
    NoEncontrado,
    NotaRequerida,
    PrecioCambiado,
    ReprogramacionNoPermitida,
    SinPermiso,
    TextoDesactualizado,
    ToleranciaNoCumplida,
    TramoNoDisponible,
)
from bugalu.modulos.catalogo.dominio.precio import desglosar_igv_incluido
from bugalu.modulos.reservas.dominio.disponibilidad import Tramo
from bugalu.modulos.reservas.dominio.modelos import (
    PARAMETROS,
    CancelacionReserva,
    Cierre,
    ContextoReprogramacion,
    CuotaReserva,
    EspecialistaAplicado,
    Excepcion,
    Franja,
    NuevaReserva,
    PagoCuota,
    Politica,
    Referencia,
    Reprogramacion,
    RequisitosReserva,
    Reserva,
    ReservaVisible,
    Sala,
    ServicioReservado,
    VistaCancelacion,
    VistaReprogramacion,
)
from bugalu.modulos.reservas.dominio.reserva import cuota_pagable, estado_de_cuota
from bugalu.modulos.reservas.infraestructura.salida.devoluciones_sql import (
    DEVOLUCION,
    devolucion_desde_fila,
)

_TOPE_SUGERENCIA = 300
_RESERVA = (
    "select r.id, r.folio, r.estado, r.motivo_cancelacion, r.inicio, r.fin, r.fin_buffer, "
    "r.precio, r.vence_pago, r.id_cliente, sa.id, sa.nombre, se.id, se.nombre, se.categoria, "
    "case when r.id_cliente = (select auth.uid()) or public.es_administrador() "
    "then r.nota_cancelacion end, public.hay_pago_por_validar(r.id), r.parametros_aplicados, "
    "(select a.version from public.aceptacion a "
    "where a.contexto = 'reserva' and a.id_operacion = r.id), "
    "r.eleccion_estudio, r.aviso_en, r.nivel_cancelacion, r.cancelacion_por, "
    "r.pagado_cancelacion, r.retenido, r.credito_generado, r.id_cancelador, "
    "r.excepcion_motivo, r.excepcion_por, r.excepcion_en "
    "from public.reserva r join public.sala_tecnica sa on sa.id = r.id_sala "
    "join public.servicio se on se.id = r.id_servicio "
)


# P0001/22023 de las funciones de cancelacion (mensaje = codigo) y su error de negocio.
_NEGOCIO = {
    "no_cancelable": (NoCancelable, "La reserva ya no se puede cancelar."),
    "no_aplicable": (NoAplicable, "La reserva no admite esa accion ahora."),
    "tolerancia_no_cumplida": (ToleranciaNoCumplida, "Aun no pasa la tolerancia de inasistencia."),
    "excepcion_no_aplicable": (ExcepcionNoAplicable, "Esa reserva no admite el caso excepcional."),
    "excepcion_ya_aplicada": (ExcepcionYaAplicada, "El caso excepcional ya se aplico."),
}
_INVALIDOS = {
    "nota_invalida": ("La nota debe tener de 1 a 300 caracteres.", "nota"),
    "por_invalido": ("`por` es cliente o estudio.", "por"),
    "motivo_invalido": ("El motivo debe tener de 10 a 500 caracteres.", "motivo"),
}


def _vista(f: tuple[Any, ...]) -> VistaCancelacion:
    centimos = Decimal("0.01")  # la base devuelve `0` sin escala en los ceros
    return VistaCancelacion(f[0], f[1], *(f[i].quantize(centimos) for i in (2, 3, 4, 5)), *f[6:])


def _traducir(error: Error) -> ErrorDeNegocio:
    """Errores de las funciones de cancelacion, inasistencia y excepcion a errores de negocio."""
    if isinstance(error, errors.NoDataFound):
        return NoEncontrado("No existe la reserva.")
    if isinstance(error, errors.InsufficientPrivilege):
        return SinPermiso("No tienes permiso para esa accion.")
    if isinstance(error, errors.InvalidParameterValue):
        mensaje, campo = _INVALIDOS.get(
            error.diag.message_primary or "", ("Datos invalidos.", "cuerpo")
        )
        return DatosInvalidos(mensaje, {"campo": campo})
    codigo = error.diag.message_primary
    if codigo == "nota_requerida":
        return NotaRequerida("Indica una nota.", {"campo": "nota"})
    if codigo == "aviso_invalido":
        return AvisoInvalido(
            "El aviso no puede ser futuro ni anterior a la reserva.", {"campo": "aviso_en"}
        )
    if codigo == "nivel_cambiado":
        vista = _vista(tuple(_detalle_vista(error.diag.message_detail or "{}")))
        return NivelCambiado("El nivel cambio: revisa la vista previa.", vista.a_json())
    clase, mensaje = _NEGOCIO.get(
        codigo or "", (NoCancelable, "La reserva ya no se puede cancelar.")
    )
    return clase(mensaje)


_REPROGRAMACION = {
    "reprogramacion_no_permitida": (
        ReprogramacionNoPermitida,
        "La reserva no se puede reprogramar ahora.",
    ),
    "limite_reprogramaciones": (
        LimiteReprogramaciones,
        "Ya hiciste las reprogramaciones posibles.",
    ),
    "eleccion_no_disponible": (
        EleccionNoDisponible,
        "No hay una eleccion pendiente en esa reserva.",
    ),
}


def _traducir_reprogramacion(error: Error) -> ErrorDeNegocio:
    """Errores de las funciones de reprogramar y de la eleccion tras el estudio."""
    if isinstance(error, errors.NoDataFound):
        return NoEncontrado("No existe la reserva.")
    if isinstance(error, errors.InsufficientPrivilege):
        return SinPermiso("No tienes permiso para esa accion.")
    if isinstance(error, errors.InvalidParameterValue):
        return DatosInvalidos("Datos invalidos: inicio.", {"campo": "inicio"})
    if isinstance(error, errors.ExclusionViolation):  # RN-01: la base decide el solape
        return TramoNoDisponible("Ese horario ya no está disponible.")
    codigo = error.diag.message_primary or ""
    if codigo in ("nivel_cambiado", "precio_cambiado"):
        d = json.loads(error.diag.message_detail or "{}")  # sin el desglose: lo suma el caso de uso
        centimos = Decimal("0.01")
        detalles = {
            "nivel": d["nivel"],
            **{
                k: str(Decimal(d[k]).quantize(centimos))
                for k in ("penalizacion", "saldo", "credito")
            },
            "reprogramaciones_restantes": d["reprogramaciones_restantes"],
        }
        if codigo == "nivel_cambiado":
            return NivelCambiado("El nivel cambio: revisa la vista previa.", detalles)
        return PrecioCambiado("El precio cambio: revisa la vista previa.", detalles)
    clase, mensaje = _REPROGRAMACION.get(codigo, (ReprogramacionNoPermitida, "No se puede ahora."))
    return clase(mensaje)


def _detalle_vista(texto: str) -> list[Any]:
    d = json.loads(texto)
    return [
        d["nivel"],
        Decimal(str(d["anticipacion_horas"])),
        *(Decimal(d[k]) for k in ("pagado", "en_validacion", "retenido", "credito")),
        datetime.fromisoformat(d["credito_vence"]) if d["credito_vence"] else None,
        d["puede_reprogramar"],
        d["reprogramaciones_restantes"],
    ]


def _con_impuesto(precio: dict[str, Any], aplicados: dict[str, Any]) -> dict[str, Any]:
    """Las reservas anteriores a RF-20 no guardaron el desglose: sale del total con IGV incluido."""
    if "impuesto" in precio:
        return precio
    porcentaje = Decimal(aplicados["porcentaje_igv"])
    base, monto = desglosar_igv_incluido(Decimal(precio["total"]), porcentaje)
    impuesto = {
        "nombre": "IGV",
        "porcentaje": str(porcentaje),
        "incluido": True,
        "base": str(base),
        "monto": str(monto),
    }
    adelanto = str(Decimal(aplicados["porcentaje_adelanto"]).quantize(Decimal("0.01")))
    return {**precio, "impuesto": impuesto, "porcentaje_adelanto": adelanto}


def _cancelacion(
    f: tuple[Any, ...], nombres: Mapping[UUID, str | None]
) -> CancelacionReserva | None:
    """Solo si la reserva se cancelo o se marco no asistio por la politica de RF-18."""
    if f[20] is None or f[2] not in ("cancelada", "no_asistio"):
        return (
            None  # al reprogramar tras el estudio vuelve a estar viva; el registro queda en la base
        )

    def quien(id_: UUID | None) -> Referencia | None:
        return Referencia(id_, nombres[id_]) if id_ is not None and id_ in nombres else None

    excepcion = Excepcion(f[27], quien(f[28]), f[29]) if f[29] is not None else None
    return CancelacionReserva(
        nivel=f[21],
        aviso_en=f[20],
        por=f[22],
        pagado=f[23],
        retenido=f[24],
        credito=f[25],
        nota=f[15],
        registrada_por=quien(f[26]),
        excepcion=excepcion,
    )


class RepositorioReservasPostgres:
    """Recibe una transaccion ya abierta (publica o con identidad): la RLS decide el acceso."""

    def __init__(self, conexion: AsyncConnection) -> None:
        self._conexion = conexion

    async def _filas(self, consulta: str, parametros: Sequence[Any] = ()) -> list[Any]:
        cursor = await self._conexion.execute(consulta, parametros)
        return await cursor.fetchall()

    async def es_administrador(self) -> bool:
        return bool((await self._filas("select public.es_administrador()"))[0][0])

    async def es_personal(self) -> bool:
        return bool((await self._filas("select public.es_personal()"))[0][0])

    async def listar_salas(self) -> list[Sala]:
        filas = await self._filas(
            "select id, nombre, sede from public.sala_tecnica where activa order by sede, nombre"
        )
        return [Sala(*f) for f in filas]

    async def existe_sala(self, id_sala: UUID) -> bool:
        filas = await self._filas(
            "select 1 from public.sala_tecnica where id = %s and activa", (id_sala,)
        )
        return bool(filas)

    async def limites_reserva(self) -> tuple[int, int]:
        minima, maxima = (await self._filas("select * from public.limites_reserva()"))[0]
        return int(minima), int(maxima)

    async def franjas_en(self, id_sala: UUID, desde: datetime, hasta: datetime) -> list[Franja]:
        filas = await self._filas(
            "select id, id_sala, inicio, fin from public.franja_sala "
            "where id_sala = %s and inicio < %s and fin > %s order by inicio",
            (id_sala, hasta, desde),
        )
        return [Franja(*f) for f in filas]

    async def franjas_antes_de(self, id_sala: UUID, instante: datetime) -> list[Franja]:
        filas = await self._filas(
            "select id, id_sala, inicio, fin from public.franja_sala "
            "where id_sala = %s and inicio < %s order by inicio desc limit %s",
            (id_sala, instante, _TOPE_SUGERENCIA),
        )
        return [Franja(*f) for f in filas]

    async def cierres_en(self, id_sala: UUID, desde: datetime, hasta: datetime) -> list[Cierre]:
        filas = await self._filas(
            "select id, id_sala, inicio, fin, motivo from public.cierre_sala "
            "where id_sala = %s and inicio < %s and fin > %s order by inicio",
            (id_sala, hasta, desde),
        )
        return [Cierre(*f) for f in filas]

    async def ocupacion(self, id_sala: UUID, desde: datetime, hasta: datetime) -> list[Tramo]:
        filas = await self._filas(
            "select inicio, fin_buffer from public.ocupacion_sala(%s, %s, %s)",
            (id_sala, desde, hasta),
        )
        return [Tramo(*f) for f in filas]

    async def reservas_visibles(
        self, id_sala: UUID, desde: datetime, hasta: datetime
    ) -> list[ReservaVisible]:
        filas = await self._filas(
            "select r.id, r.folio, r.id_cliente, s.nombre, r.estado, r.inicio, r.fin_buffer, "
            "public.hay_pago_por_validar(r.id) "
            "from public.reserva r join public.servicio s on s.id = r.id_servicio "
            "where r.id_sala = %s and r.estado <> 'cancelada' "
            "and r.inicio < %s and r.fin_buffer > %s order by r.inicio",
            (id_sala, hasta, desde),
        )
        return [ReservaVisible(*f) for f in filas]

    async def nombres_de_clientes(self, ids: Sequence[UUID]) -> Mapping[UUID, str | None]:
        if not ids:
            return {}
        filas = await self._filas(
            "select id, nombre from public.nombres_de_clientes(%s)", (list(ids),)
        )
        return {f[0]: f[1] for f in filas}

    async def insertar_franjas(self, id_sala: UUID, tramos: Sequence[Tramo]) -> list[Franja]:
        nuevas = []
        for tramo in tramos:
            try:
                filas = await self._filas(
                    "insert into public.franja_sala (id_sala, inicio, fin, id_publicador) "
                    "values (%s, %s, %s, (select auth.uid())) "
                    "returning id, id_sala, inicio, fin",
                    (id_sala, tramo.inicio, tramo.fin),
                )
            except errors.ExclusionViolation:
                raise FranjaSolapada("La franja se solapa con otra de la sala.") from None
            nuevas.append(Franja(*filas[0]))
        return nuevas

    async def bloquear_sala(self, id_sala: UUID) -> None:
        # Bloqueo hasta el fin de la transaccion; todas las lecturas del caso de uso van despues.
        await self._conexion.execute(
            "select pg_advisory_xact_lock(hashtextextended(%s, 0))", (str(id_sala),)
        )

    async def obtener_franja(self, id_franja: UUID) -> Franja | None:
        filas = await self._filas(
            "select id, id_sala, inicio, fin from public.franja_sala where id = %s", (id_franja,)
        )
        return Franja(*filas[0]) if filas else None

    async def eliminar_franja(self, id_franja: UUID) -> None:
        await self._conexion.execute("delete from public.franja_sala where id = %s", (id_franja,))

    async def insertar_cierre(self, id_sala: UUID, tramo: Tramo, motivo: str) -> Cierre:
        filas = await self._filas(
            "insert into public.cierre_sala (id_sala, inicio, fin, motivo, id_autor) "
            "values (%s, %s, %s, %s, (select auth.uid())) "
            "returning id, id_sala, inicio, fin, motivo",
            (id_sala, tramo.inicio, tramo.fin, motivo),
        )
        return Cierre(*filas[0])

    async def obtener_cierre(self, id_cierre: UUID) -> Cierre | None:
        filas = await self._filas(
            "select id, id_sala, inicio, fin, motivo from public.cierre_sala where id = %s",
            (id_cierre,),
        )
        return Cierre(*filas[0]) if filas else None

    async def eliminar_cierre(self, id_cierre: UUID) -> None:
        await self._conexion.execute("delete from public.cierre_sala where id = %s", (id_cierre,))

    async def obtener_parametros(self) -> dict[str, int]:
        filas = await self._filas("select clave, valor from public.parametro")
        return {clave: int(valor) for clave, valor in filas}

    async def guardar_parametros(self, cambios: Mapping[str, int]) -> None:
        for clave, valor in cambios.items():
            if clave not in PARAMETROS:
                raise ValueError("Parametro desconocido.")
            await self._conexion.execute(
                "select public.actualizar_parametro(%s, %s)", (clave, valor)
            )

    async def plazos_pago(self) -> tuple[int, int]:
        dias, horas = (await self._filas("select * from public.plazos_pago()"))[0]
        return int(dias), int(horas)

    async def tiene_servicio_previo(self) -> bool:
        filas = await self._filas(
            "select exists (select 1 from public.reserva r "
            "join public.servicio s on s.id = r.id_servicio "
            "where r.id_cliente = (select auth.uid()) "
            "and r.estado in ('confirmada', 'en_curso', 'finalizada') and s.categoria <> 'ensayo')"
        )
        return bool(filas[0][0])

    async def insertar_reserva(self, nueva: NuevaReserva) -> UUID:
        try:
            filas = await self._filas(
                "insert into public.reserva (id_cliente, id_sala, id_servicio, id_franja, inicio, "
                "fin, precio, total, vence_pago, detalle, parametros_aplicados) "
                "values ((select auth.uid()), %s, %s, %s, %s, %s, %s, %s, %s, %s, %s) "
                "returning id",
                (
                    nueva.id_sala,
                    nueva.id_servicio,
                    nueva.id_franja,
                    nueva.inicio,
                    nueva.fin,
                    Jsonb(nueva.cotizacion.precio),
                    nueva.cotizacion.total,
                    nueva.vence_pago,
                    nueva.detalle,
                    Jsonb(nueva.cotizacion.parametros_aplicados),
                ),
            )
        except errors.ExclusionViolation:  # RN-01: la base es quien decide el solape
            raise TramoNoDisponible("Ese horario ya no está disponible.") from None
        id_reserva: UUID = filas[0][0]
        for e in nueva.cotizacion.especialistas:
            await self._conexion.execute(
                "insert into public.reserva_especialista "
                "(id_reserva, id_especialista, monto_fijo, monto_variable, unidad) "
                "values (%s, %s, %s, %s, %s)",
                (id_reserva, e.id, e.monto_fijo, e.monto_variable, e.unidad),
            )
        for hito, monto in nueva.cuotas:
            await self._conexion.execute(
                "insert into public.cuota (id_reserva, hito, monto) values (%s, %s, %s)",
                (id_reserva, hito, monto),
            )
        return id_reserva

    async def encolar_aviso_reserva(self, id_reserva: UUID) -> None:
        await self._conexion.execute("select public.encolar_aviso_reserva(%s)", (id_reserva,))

    async def requisitos_para_reservar(self) -> RequisitosReserva:
        pendientes = await self._filas(
            "select tipo, version, contexto, motivo from public.mis_pendientes()"
        )
        faltantes = (await self._filas("select public.campos_faltantes_para_reservar()"))[0][0]
        menor = await self._filas(
            "select es_menor from public.usuario where id = (select auth.uid())"
        )
        vigente = await self._filas(
            "select tipo, version, vigente_desde from public.textos_vigentes() "
            "where tipo = 'condiciones_contratacion'"
        )
        return RequisitosReserva(
            tuple(
                {"tipo": t, "version": v, "contexto": c, "motivo": m} for t, v, c, m in pendientes
            ),
            tuple(faltantes or ()),
            bool(menor and menor[0][0]),
            {
                "tipo": vigente[0][0],
                "version": vigente[0][1],
                "vigente_desde": vigente[0][2].isoformat(),
            }
            if vigente
            else None,
        )

    async def aceptar_condiciones(self, id_reserva: UUID, version: str) -> None:
        try:
            await self._conexion.execute(
                "select public.aceptar_condiciones('reserva', %s, %s)", (id_reserva, version)
            )
        except errors.RaiseException as error:
            if error.diag.message_primary == "texto_desactualizado":  # carrera con una publicacion
                raise TextoDesactualizado(
                    "Las condiciones dejaron de ser la version vigente."
                ) from None
            raise

    async def _reservas(self, condicion: str, parametros: Sequence[Any]) -> list[Reserva]:
        filas = await self._filas(
            f"{_RESERVA} where {condicion} order by r.inicio, r.folio", parametros
        )
        ids = [f[0] for f in filas]
        cuotas: dict[UUID, list[CuotaReserva]] = {}
        pagos: dict[UUID, list[PagoCuota]] = {}
        especialistas: dict[UUID, list[Referencia]] = {}
        if ids:
            for f in await self._filas(  # la RLS deja ver solo los pagos propios (o todos al admin)
                "select id_cuota, id, estado, metodo, monto, numero_operacion, motivo_rechazo, "
                "registrado_en from public.comprobante_pago "
                "where id_cuota in (select id from public.cuota where id_reserva = any(%s)) "
                "order by registrado_en, id",
                (ids,),
            ):
                pagos.setdefault(f[0], []).append(PagoCuota(*f[1:]))
            estados = {f[0]: f[2] for f in filas}
            for f in await self._filas(
                "select id, id_reserva, hito, monto, estado, pagado from public.cuota "
                "where id_reserva = any(%s) order by hito",
                (ids,),
            ):
                de_la_cuota = pagos.get(f[0], [])
                estado = estado_de_cuota(f[4], de_la_cuota)
                cuotas.setdefault(f[1], []).append(
                    CuotaReserva(
                        f[0],
                        f[2],
                        f[3],
                        estado,
                        cuota_pagable(estado, f[2], estados[f[1]]),
                        tuple(de_la_cuota),
                        f[5],
                    )
                )
            for f in await self._filas(
                "select re.id_reserva, e.id, e.nombre from public.reserva_especialista re "
                "join public.especialista e on e.id = re.id_especialista "
                "where re.id_reserva = any(%s) order by e.nombre",
                (ids,),
            ):
                especialistas.setdefault(f[0], []).append(Referencia(f[1], f[2]))
        nombres = await self._nombres_de_personas(filas)
        reprogramaciones = await self._reprogramaciones(ids)
        devoluciones = await self._devoluciones_del_estudio(ids)
        return [
            Reserva(
                id=f[0],
                folio=f[1],
                estado=f[2],
                motivo_cancelacion=f[3],
                inicio=f[4],
                fin=f[5],
                fin_buffer=f[6],
                precio=_con_impuesto(f[7], f[17]),
                vence_pago=f[8],
                id_cliente=f[9],
                sala=Referencia(f[10], f[11]),
                servicio=ServicioReservado(f[12], f[13], f[14]),
                nota_cancelacion=f[15],
                en_validacion=f[16],
                version_condiciones=f[18],
                especialistas=tuple(especialistas.get(f[0], [])),
                cuotas=tuple(cuotas.get(f[0], [])),
                pagado=sum((c.pagado for c in cuotas.get(f[0], [])), Decimal("0.00")),
                politica=Politica.desde_parametros(f[17]),
                cancelacion=_cancelacion(f, nombres),
                reprogramaciones=tuple(reprogramaciones.get(f[0], [])),
                eleccion_estudio=f[19],
                devolucion=devoluciones.get(f[0]),
            )
            for f in filas
        ]

    async def _nombres_de_personas(self, filas: Sequence[Any]) -> Mapping[UUID, str | None]:
        """Quien registro la cancelacion o la excepcion; solo personal y administrador los ven."""
        ids = list({i for f in filas for i in (f[26], f[28]) if i})
        return await self.nombres_de_clientes(ids)

    async def _reprogramaciones(self, ids: Sequence[UUID]) -> dict[UUID, list[Reprogramacion]]:
        resultado: dict[UUID, list[Reprogramacion]] = {}
        if not ids:
            return resultado
        filas = await self._filas(
            "select id_reserva, anterior_inicio, nuevo_inicio, nivel, penalizacion, "
            "total_anterior, total_nuevo, id_autor, en from public.reprogramacion "
            "where id_reserva = any(%s) "
            "order by en, id",
            (ids,),
        )
        nombres = await self.nombres_de_clientes([f[7] for f in filas if f[7]])
        for f in filas:
            por = Referencia(f[7], nombres[f[7]]) if f[7] in nombres else None
            resultado.setdefault(f[0], []).append(
                Reprogramacion(f[1], f[2], f[3], f[4], f[5], f[6], por, f[8])
            )
        return resultado

    async def _devoluciones_del_estudio(self, ids: Sequence[UUID]) -> dict[UUID, Any]:
        if not ids:
            return {}
        filas = await self._filas(
            f"{DEVOLUCION}where d.tipo = 'estudio' and d.id_reserva = any(%s)", (ids,)
        )
        return {f[2]: devolucion_desde_fila(f) for f in filas}

    async def obtener_reserva(self, id_reserva: UUID) -> Reserva | None:
        encontradas = await self._reservas("r.id = %s", (id_reserva,))
        return encontradas[0] if encontradas else None

    async def existe_reserva(self, id_reserva: UUID) -> bool:
        return bool((await self._filas("select public.existe_reserva(%s)", (id_reserva,)))[0][0])

    async def listar_mias(self) -> list[Reserva]:
        return await self._reservas("r.id_cliente = (select auth.uid())", ())

    async def listar_en_rango(self, desde: datetime, hasta: datetime) -> list[Reserva]:
        return await self._reservas("r.inicio < %s and r.fin_buffer > %s", (hasta, desde))

    async def cancelar_reserva(
        self,
        id_reserva: UUID,
        nota: str | None = None,
        nivel_esperado: int | None = None,
        por: str | None = None,
        aviso_en: datetime | None = None,
    ) -> None:
        try:
            await self._conexion.execute(
                "select public.cancelar_reserva(%s, %s, %s, %s, %s)",
                (id_reserva, nota, nivel_esperado, por, aviso_en),
            )
        except (errors.NoDataFound, errors.InsufficientPrivilege, errors.RaiseException) as e:
            raise _traducir(e) from None
        except errors.InvalidParameterValue as e:
            raise _traducir(e) from None

    async def vista_cancelacion(
        self, id_reserva: UUID, aviso_en: datetime | None = None
    ) -> VistaCancelacion:
        try:
            filas = await self._filas(
                "select * from public.vista_cancelacion(%s, %s)", (id_reserva, aviso_en)
            )
        except (errors.NoDataFound, errors.InsufficientPrivilege, errors.RaiseException) as e:
            raise _traducir(e) from None
        return _vista(filas[0])

    async def marcar_inasistencia(self, id_reserva: UUID) -> None:
        try:
            await self._conexion.execute("select public.marcar_inasistencia(%s)", (id_reserva,))
        except (errors.NoDataFound, errors.InsufficientPrivilege, errors.RaiseException) as e:
            raise _traducir(e) from None

    async def aplicar_excepcion(self, id_reserva: UUID, motivo: str) -> None:
        try:
            await self._conexion.execute(
                "select public.aplicar_excepcion(%s, %s)", (id_reserva, motivo)
            )
        except (
            errors.NoDataFound,
            errors.InsufficientPrivilege,
            errors.RaiseException,
            errors.InvalidParameterValue,
        ) as e:
            raise _traducir(e) from None

    async def ocupacion_excluyendo(
        self, id_sala: UUID, desde: datetime, hasta: datetime, excluir: UUID
    ) -> list[Tramo]:
        filas = await self._filas(
            "select inicio, fin_buffer from public.ocupacion_sala_excluyendo(%s, %s, %s, %s)",
            (id_sala, desde, hasta, excluir),
        )
        return [Tramo(*f) for f in filas]

    async def contexto_reprogramacion(self, id_reserva: UUID) -> ContextoReprogramacion:
        try:
            filas = await self._filas(
                "select id_sala, id_servicio, inicio, fin, estudio, precio, total, "
                "id_especialistas, parametros_aplicados "
                "from public.contexto_reprogramacion(%s)",
                (id_reserva,),
            )
        except (errors.NoDataFound, errors.InsufficientPrivilege, errors.RaiseException) as e:
            raise _traducir_reprogramacion(e) from None
        f = filas[0]
        return ContextoReprogramacion(
            f[0], f[1], f[2], f[3], f[4], _con_impuesto(f[5], f[8]), f[6], tuple(f[7])
        )

    async def vista_reprogramacion(
        self, id_reserva: UUID, inicio: datetime, total: Decimal, precio: dict[str, Any]
    ) -> VistaReprogramacion:
        try:
            filas = await self._filas(
                "select nivel, penalizacion, saldo, credito, reprogramaciones_restantes "
                "from public.vista_reprogramacion(%s, %s, %s)",
                (id_reserva, inicio, total),
            )
        except (
            errors.NoDataFound,
            errors.InsufficientPrivilege,
            errors.RaiseException,
            errors.InvalidParameterValue,
        ) as e:
            raise _traducir_reprogramacion(e) from None
        nivel, penalizacion, saldo, credito, restantes = filas[0]
        centimos = Decimal("0.01")  # la base devuelve `0` sin escala en los ceros
        return VistaReprogramacion(
            nivel,
            penalizacion.quantize(centimos),
            precio,
            saldo.quantize(centimos),
            credito.quantize(centimos),
            restantes,
        )

    async def reprogramar_reserva(  # noqa: PLR0913
        self,
        id_reserva: UUID,
        inicio: datetime,
        nivel_esperado: int | None,
        total_esperado: Decimal | None,
        id_franja: UUID,
        precio: dict[str, Any],
        total: Decimal,
        especialistas: Sequence[EspecialistaAplicado],
    ) -> None:
        aplicados = [
            {
                "id": str(e.id),
                "monto_fijo": str(e.monto_fijo),
                "monto_variable": str(e.monto_variable),
                "unidad": e.unidad,
            }
            for e in especialistas
        ]
        try:
            await self._conexion.execute(
                "select public.reprogramar_reserva(%s, %s, %s, %s, %s, %s, %s, %s)",
                (
                    id_reserva,
                    inicio,
                    nivel_esperado,
                    total_esperado,
                    id_franja,
                    Jsonb(precio),
                    total,
                    Jsonb(aplicados),
                ),
            )
        except (
            errors.NoDataFound,
            errors.InsufficientPrivilege,
            errors.RaiseException,
            errors.InvalidParameterValue,
            errors.ExclusionViolation,
        ) as e:
            raise _traducir_reprogramacion(e) from None

    async def elegir_estudio_devolucion(self, id_reserva: UUID) -> None:
        try:
            await self._conexion.execute(
                "select public.elegir_estudio_devolucion(%s)", (id_reserva,)
            )
        except (errors.NoDataFound, errors.InsufficientPrivilege, errors.RaiseException) as e:
            raise _traducir_reprogramacion(e) from None
