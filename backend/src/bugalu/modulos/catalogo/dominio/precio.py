"""Motor de precio de una reserva (RN-15, ADR-009): funciones puras, sin I/O.

Cada componente (el servicio y cada especialista) tiene una parte variable por tiempo, con recargo
por horario sobre cada bloque de 30 min, y una parte fija que se cobra una vez por reserva.
"""

from collections.abc import Collection, Iterable, Sequence
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta, timezone
from decimal import ROUND_HALF_UP, Decimal
from enum import StrEnum
from uuid import UUID

from bugalu.compartido.errores import ServicioNoReservable, TramoInvalido

LIMA = timezone(timedelta(hours=-5))  # Lima no tiene horario de verano
BLOQUE = timedelta(minutes=30)
MAXIMO_BLOQUES = 16  # 8 horas
_CENTIMO = Decimal("0.01")


class Unidad(StrEnum):
    HORA = "hora"
    LAPSO_30 = "lapso_30"


class TipoRecargo(StrEnum):
    NOCHE = "noche"
    FIN_DE_SEMANA = "fin_de_semana"
    FERIADO = "feriado"


@dataclass(frozen=True)
class Servicio:
    id: UUID
    nombre: str
    categoria: str
    ocupa_sala: bool
    tarifa_hora: Decimal
    monto_fijo: Decimal
    especialistas_por_defecto: tuple[UUID, ...]
    activo: bool


@dataclass(frozen=True)
class Especialista:
    id: UUID
    nombre: str
    monto_fijo: Decimal
    monto_variable: Decimal
    unidad: Unidad
    activo: bool


@dataclass(frozen=True)
class Recargos:
    noche: Decimal
    desde_noche: time
    hasta_noche: time
    fin_de_semana: Decimal
    feriado: Decimal


@dataclass(frozen=True)
class Feriado:
    fecha: date
    nombre: str


@dataclass(frozen=True)
class Linea:
    concepto: str
    cantidad: Decimal
    unidad: str
    monto: Decimal


@dataclass(frozen=True)
class LineaRecargo:
    tipo: str
    bloques: int
    monto: Decimal


@dataclass(frozen=True)
class ConfiguracionImpuestos:
    porcentaje: Decimal
    incluido: bool  # los precios del catalogo ya traen el IGV (ADR-013)


@dataclass(frozen=True)
class Impuesto:
    porcentaje: Decimal
    incluido: bool
    base: Decimal
    monto: Decimal


@dataclass(frozen=True)
class Simulacion:
    lineas: tuple[Linea, ...]
    recargos: tuple[LineaRecargo, ...]
    total: Decimal
    anticipo: Decimal
    impuesto: Impuesto
    porcentaje_adelanto: Decimal  # el que dio el anticipo, con dos decimales


def _centimos(monto: Decimal) -> Decimal:
    return monto.quantize(_CENTIMO, rounding=ROUND_HALF_UP)


def desglosar_igv_incluido(total: Decimal, porcentaje: Decimal) -> tuple[Decimal, Decimal]:
    """(base, igv) de un total que ya incluye el IGV (RF-20 CA-02); base + igv = total."""
    base = _centimos(total / (1 + porcentaje / 100))
    return base, total - base


def impuesto_y_total(suma: Decimal, config: ConfiguracionImpuestos) -> tuple[Impuesto, Decimal]:
    if config.incluido:
        base, igv = desglosar_igv_incluido(suma, config.porcentaje)
        return Impuesto(config.porcentaje, True, base, igv), suma
    igv = _centimos(suma * config.porcentaje / 100)
    return Impuesto(config.porcentaje, False, suma, igv), suma + igv


def combinar_especialistas(
    por_defecto: Iterable[Especialista], elegidos: Iterable[Especialista]
) -> list[Especialista]:
    """Los por defecto siempre van; los elegidos se suman sin repetir."""
    unicos = {e.id: e for e in (*por_defecto, *elegidos)}
    return list(unicos.values())


def bloques_del_tramo(inicio: datetime, fin: datetime) -> list[datetime]:
    """Inicio de cada bloque de 30 min, en hora de Lima."""
    if inicio.tzinfo is None or fin.tzinfo is None:
        raise TramoInvalido("El inicio y el fin deben incluir la zona horaria.")
    desde = inicio.astimezone(LIMA)
    duracion = fin - inicio
    if desde.minute % 30 or desde.second or desde.microsecond or duracion % BLOQUE:
        raise TramoInvalido("El tramo debe empezar y terminar en múltiplos de 30 minutos.")
    cantidad = duracion // BLOQUE
    if not 1 <= cantidad <= MAXIMO_BLOQUES:
        raise TramoInvalido("El tramo dura de 30 minutos a 8 horas.")
    return [desde + BLOQUE * i for i in range(cantidad)]


def _es_noche(hora: time, r: Recargos) -> bool:
    if r.desde_noche > r.hasta_noche:  # cruza la medianoche
        return hora >= r.desde_noche or hora < r.hasta_noche
    return r.desde_noche <= hora < r.hasta_noche


def _recargo_del_bloque(
    bloque: datetime, r: Recargos, feriados: Collection[date]
) -> tuple[TipoRecargo, Decimal] | None:
    """Coincidencias: manda el mayor porcentaje; a igual, feriado y luego fin de semana."""
    candidatos: list[tuple[TipoRecargo, Decimal]] = []
    if bloque.date() in feriados:
        candidatos.append((TipoRecargo.FERIADO, r.feriado))
    if bloque.weekday() >= 5:
        candidatos.append((TipoRecargo.FIN_DE_SEMANA, r.fin_de_semana))
    if _es_noche(bloque.time(), r):
        candidatos.append((TipoRecargo.NOCHE, r.noche))
    return max(candidatos, key=lambda c: c[1], default=None)


def calcular_simulacion(
    servicio: Servicio,
    por_defecto: Sequence[Especialista],
    elegidos: Sequence[Especialista],
    inicio: datetime,
    fin: datetime,
    recargos: Recargos,
    feriados: Collection[date],
    impuestos: ConfiguracionImpuestos,
    porcentaje_adelanto: int,
) -> Simulacion:
    if not (servicio.ocupa_sala and servicio.activo):
        raise ServicioNoReservable("El servicio no se reserva en el calendario.")
    bloques = bloques_del_tramo(inicio, fin)

    # (nombre, parte fija, tarifa por unidad, unidad)
    componentes = [(servicio.nombre, servicio.monto_fijo, servicio.tarifa_hora, Unidad.HORA)] + [
        (e.nombre, e.monto_fijo, e.monto_variable, e.unidad)
        for e in combinar_especialistas(por_defecto, elegidos)
    ]
    n = len(bloques)
    lineas: list[Linea] = []
    variable_por_bloque = Decimal(0)
    for nombre, fijo, tarifa, unidad in componentes:
        por_bloque = tarifa / 2 if unidad is Unidad.HORA else tarifa
        variable_por_bloque += por_bloque
        cantidad = Decimal(n) / 2 if unidad is Unidad.HORA else Decimal(n)
        if tarifa:
            lineas.append(Linea(nombre, cantidad, unidad.value, _centimos(por_bloque * n)))
        if fijo:
            lineas.append(Linea(f"{nombre} (monto fijo)", Decimal(1), "fijo", _centimos(fijo)))

    acumulado: dict[TipoRecargo, tuple[int, Decimal]] = {}
    for bloque in bloques:
        if (aplicable := _recargo_del_bloque(bloque, recargos, feriados)) and aplicable[1]:
            tipo, porcentaje = aplicable
            cuenta, monto = acumulado.get(tipo, (0, Decimal(0)))
            acumulado[tipo] = (cuenta + 1, monto + variable_por_bloque * porcentaje / 100)
    lineas_recargo = tuple(
        LineaRecargo(tipo.value, acumulado[tipo][0], _centimos(acumulado[tipo][1]))
        for tipo in TipoRecargo
        if tipo in acumulado
    )

    montos = [*(x.monto for x in lineas), *(x.monto for x in lineas_recargo)]
    suma = sum(montos, Decimal(0)).quantize(_CENTIMO)
    impuesto, total = impuesto_y_total(suma, impuestos)
    anticipo = _centimos(total * porcentaje_adelanto / 100)
    adelanto = Decimal(porcentaje_adelanto).quantize(_CENTIMO)
    return Simulacion(tuple(lineas), lineas_recargo, total, anticipo, impuesto, adelanto)
