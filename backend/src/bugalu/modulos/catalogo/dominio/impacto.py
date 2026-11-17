"""Ejemplos de impacto de un cambio sensible (RF-20 CA-05), con el mismo motor de precio (RN-15).

Los tramos de referencia son fijos (un miercoles, un sabado, una noche) para que el antes y el
despues se comparen sobre lo mismo; no dependen de la agenda ni de los feriados reales.
"""

from collections.abc import Collection, Iterable, Mapping, Sequence
from collections.abc import Set as Conjunto
from dataclasses import dataclass, replace
from datetime import date, datetime, time, timedelta
from decimal import Decimal

from bugalu.modulos.catalogo.dominio.precio import (
    LIMA,
    ConfiguracionImpuestos,
    Especialista,
    Recargos,
    Servicio,
    calcular_simulacion,
    impuesto_y_total,
)
from bugalu.modulos.reservas.dominio.reserva import calcular_vence_pago

IMPORTE, FECHA_HORA, TEXTO = "importe", "fecha_hora", "texto"
_MIERCOLES, _SABADO = date(2030, 1, 9), date(2030, 1, 12)
_NORMAL = (datetime(2030, 1, 9, 10, tzinfo=LIMA), datetime(2030, 1, 9, 12, tzinfo=LIMA))
_NOCHE = (datetime(2030, 1, 9, 22, tzinfo=LIMA), datetime(2030, 1, 10, 0, tzinfo=LIMA))
_FINDE = (datetime(2030, 1, 12, 10, tzinfo=LIMA), datetime(2030, 1, 12, 12, tzinfo=LIMA))
_SIN_RECARGOS = Recargos(Decimal(0), time(0), time(1), Decimal(0), Decimal(0))
_ADELANTO_DE_REFERENCIA = 50  # el adelanto no entra en el total que se compara


@dataclass(frozen=True)
class Ejemplo:
    concepto: str
    antes: str
    despues: str
    tipo: str


def _total(
    servicio: Servicio,
    por_defecto: Sequence[Especialista],
    elegidos: Sequence[Especialista],
    tramo: tuple[datetime, datetime],
    recargos: Recargos,
    impuestos: ConfiguracionImpuestos,
    feriados: Collection[date] = (),
) -> str:
    # Un servicio que no ocupa sala o esta inactivo tambien se ejemplifica: se muestra su tarifa.
    reservable = replace(servicio, ocupa_sala=True, activo=True)
    simulacion = calcular_simulacion(
        reservable, por_defecto, elegidos, *tramo, recargos, feriados, impuestos,
        _ADELANTO_DE_REFERENCIA,
    )  # fmt: skip
    return str(simulacion.total)


def ejemplos_servicio(
    antes: Servicio, despues: Servicio, impuestos: ConfiguracionImpuestos
) -> list[Ejemplo]:
    return [
        Ejemplo(
            f"2 h de {antes.nombre} en horario normal",
            _total(antes, [], [], _NORMAL, _SIN_RECARGOS, impuestos),
            _total(despues, [], [], _NORMAL, _SIN_RECARGOS, impuestos),
            IMPORTE,
        )
    ]


def ejemplos_especialista(
    usos: Iterable[tuple[Servicio, Sequence[Especialista]]],
    antes: Especialista,
    despues: Especialista,
    impuestos: ConfiguracionImpuestos,
) -> list[Ejemplo]:
    """`usos`: cada servicio con los demas especialistas que trae por defecto (sin este)."""
    return [
        Ejemplo(
            f"2 h de {servicio.nombre} con {antes.nombre}",
            _total(servicio, otros, [antes], _NORMAL, _SIN_RECARGOS, impuestos),
            _total(servicio, otros, [despues], _NORMAL, _SIN_RECARGOS, impuestos),
            IMPORTE,
        )
        for servicio, otros in usos
    ]


def ejemplos_recargos(
    servicio: Servicio,
    antes: Recargos,
    despues: Recargos,
    impuestos: ConfiguracionImpuestos,
    campos: Iterable[str],
) -> list[Ejemplo]:
    grupos = {c.split(".")[0] for c in campos}
    casos = [
        ("noche", "de 22:00 a 00:00", _NOCHE, ()),
        ("fin_de_semana", "un sábado en la mañana", _FINDE, ()),
        ("feriado", "un día feriado en la mañana", _NORMAL, (_MIERCOLES,)),
    ]
    return [
        Ejemplo(
            f"2 h de {servicio.nombre} {cuando}",
            _total(servicio, [], [], tramo, antes, impuestos, feriados),
            _total(servicio, [], [], tramo, despues, impuestos, feriados),
            IMPORTE,
        )
        for grupo, cuando, tramo, feriados in casos
        if grupo in grupos
    ]


def ejemplos_impuestos(
    antes: ConfiguracionImpuestos, despues: ConfiguracionImpuestos
) -> list[Ejemplo]:
    cien = Decimal("100.00")
    (igv_antes, total_antes), (igv_despues, total_despues) = (
        impuesto_y_total(cien, c) for c in (antes, despues)
    )
    return [
        Ejemplo(
            "IGV de una tarifa de 100.00", str(igv_antes.monto), str(igv_despues.monto), IMPORTE
        ),
        Ejemplo("Total de una tarifa de 100.00", str(total_antes), str(total_despues), IMPORTE),
    ]


def _nivel(horas_de_aviso: int, p: Mapping[str, int]) -> str:
    if horas_de_aviso > p["horas_nivel_1"]:
        return "Nivel 1: sin cargo"
    if horas_de_aviso >= p["horas_nivel_2"]:
        return f"Nivel 2: penalización del {p['porcentaje_penalizacion_nivel_2']} %"
    return "Nivel 3: se retiene lo pagado"


def _importe(porcentaje: int, base: str) -> str:
    return str((Decimal(base) * porcentaje / 100).quantize(Decimal("0.01")))


def ejemplos_parametros(
    antes: Mapping[str, int],
    despues: Mapping[str, int],
    cambiados: Conjunto[str],
    ahora: datetime,
) -> list[Ejemplo]:
    ejemplos: list[Ejemplo] = []
    cubiertos: set[str] = set()
    if cambiados & {"dias_limite_pago", "horas_limite_pago"}:
        cubiertos |= {"dias_limite_pago", "horas_limite_pago"}
        for texto_inicio, horas in (("5 días", 5 * 24), ("36 h", 36)):
            inicio = ahora + timedelta(hours=horas)
            vence = [
                calcular_vence_pago(ahora, inicio, p["dias_limite_pago"], p["horas_limite_pago"])
                .astimezone(LIMA)
                .isoformat()
                for p in (antes, despues)
            ]
            ejemplos.append(
                Ejemplo(
                    f"Vencimiento del pago de una reserva a {texto_inicio}",
                    vence[0],
                    vence[1],
                    FECHA_HORA,
                )
            )
    if "porcentaje_adelanto" in cambiados:
        cubiertos.add("porcentaje_adelanto")
        ejemplos.append(
            Ejemplo(
                "Adelanto de una reserva de 200.00",
                _importe(antes["porcentaje_adelanto"], "200.00"),
                _importe(despues["porcentaje_adelanto"], "200.00"),
                IMPORTE,
            )
        )
    if "porcentaje_penalizacion_nivel_2" in cambiados:
        cubiertos.add("porcentaje_penalizacion_nivel_2")
        ejemplos.append(
            Ejemplo(
                "Monto retenido en el nivel 2 de una reserva de 200.00",
                _importe(antes["porcentaje_penalizacion_nivel_2"], "200.00"),
                _importe(despues["porcentaje_penalizacion_nivel_2"], "200.00"),
                IMPORTE,
            )
        )
    if cambiados & {"horas_nivel_1", "horas_nivel_2", "porcentaje_penalizacion_nivel_2"}:
        cubiertos |= {"horas_nivel_1", "horas_nivel_2"}
        ejemplos.append(
            Ejemplo("Cancelar con 30 h de aviso", _nivel(30, antes), _nivel(30, despues), TEXTO)
        )
    ejemplos += [
        Ejemplo(c.replace("_", " ").capitalize(), str(antes[c]), str(despues[c]), TEXTO)
        for c in sorted(cambiados - cubiertos)
    ]
    return ejemplos
