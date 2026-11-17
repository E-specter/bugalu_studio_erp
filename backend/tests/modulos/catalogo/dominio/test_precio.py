from datetime import UTC, date, datetime, time, timedelta, timezone
from decimal import Decimal
from typing import Any
from uuid import uuid4

import pytest

from bugalu.compartido.errores import ServicioNoReservable, TramoInvalido
from bugalu.modulos.catalogo.dominio.precio import (
    ConfiguracionImpuestos,
    Especialista,
    Impuesto,
    Linea,
    Recargos,
    Servicio,
    Simulacion,
    Unidad,
    calcular_simulacion,
    desglosar_igv_incluido,
)

LIMA = timezone(timedelta(hours=-5))
D = Decimal
IGV_INCLUIDO = ConfiguracionImpuestos(D("18.00"), True)


def lima(dia: int, hora: int, minuto: int = 0) -> datetime:
    return datetime(2026, 11, dia, hora, minuto, tzinfo=LIMA)


# 2026-11-18 es miercoles, 19 jueves, 20 viernes, 21 sabado, 22 domingo.
RECARGOS = Recargos(
    noche=D(25), desde_noche=time(20, 0), hasta_noche=time(6, 0), fin_de_semana=D(20), feriado=D(30)
)


def servicio(tarifa: str = "80", fijo: str = "0", **extra: bool) -> Servicio:
    datos = {"ocupa_sala": True, "activo": True, **extra}
    return Servicio(
        id=uuid4(),
        nombre="Grabacion",
        categoria="grabacion",
        tarifa_hora=D(tarifa),
        monto_fijo=D(fijo),
        especialistas_por_defecto=(),
        **datos,
    )


def especialista(nombre: str, fijo: str, variable: str, unidad: Unidad) -> Especialista:
    return Especialista(uuid4(), nombre, D(fijo), D(variable), unidad, True)


INGENIERO = especialista("Ingeniero", "30", "25", Unidad.LAPSO_30)
EJECUTANTE = especialista("Ejecutante", "50", "40", Unidad.HORA)


def calcular(
    inicio: datetime,
    fin: datetime,
    *,
    svc: Servicio | None = None,
    defecto: tuple[Especialista, ...] = (),
    elegidos: tuple[Especialista, ...] = (),
    recargos: Recargos = RECARGOS,
    feriados: tuple[date, ...] = (),
    impuestos: ConfiguracionImpuestos = IGV_INCLUIDO,
    adelanto: int = 50,
) -> Simulacion:
    return calcular_simulacion(
        svc or servicio(),
        defecto,
        elegidos,
        inicio,
        fin,
        recargos,
        frozenset(feriados),
        impuestos,
        adelanto,
    )


def resumen(s: Simulacion) -> list[tuple[str, int, Decimal]]:
    return [(r.tipo, r.bloques, r.monto) for r in s.recargos]


def test_sin_recargos_solo_la_sala_por_horas() -> None:
    s = calcular(lima(18, 10), lima(18, 12))
    assert s.lineas == (Linea("Grabacion", D("2"), "hora", D("160.00")),)
    assert s.recargos == ()
    assert (s.total, s.anticipo) == (D("160.00"), D("80.00"))


def test_media_hora_son_0_5_horas() -> None:
    s = calcular(lima(18, 10), lima(18, 10, 30))
    assert s.lineas[0].cantidad == D("0.5") and s.lineas[0].monto == D("40.00")


def test_parte_fija_se_cobra_una_vez_y_sin_recargo() -> None:
    s = calcular(lima(18, 21), lima(18, 23), svc=servicio(fijo="15"))
    assert s.lineas[1] == Linea("Grabacion (monto fijo)", D("1"), "fijo", D("15.00"))
    assert s.recargos[0].monto == D("40.00")  # 4 bloques x 40 x 25 %, sin contar los 15 fijos


def test_especialista_por_lapso_de_30_min_y_su_parte_fija() -> None:
    s = calcular(lima(18, 10), lima(18, 12), defecto=(INGENIERO,))
    assert s.lineas[1] == Linea("Ingeniero", D("4"), "lapso_30", D("100.00"))
    assert s.lineas[2] == Linea("Ingeniero (monto fijo)", D("1"), "fijo", D("30.00"))
    assert (s.total, s.anticipo) == (D("290.00"), D("145.00"))


def test_especialista_por_hora() -> None:
    s = calcular(lima(18, 10), lima(18, 11, 30), elegidos=(EJECUTANTE,))
    assert s.lineas[1] == Linea("Ejecutante", D("1.5"), "hora", D("60.00"))
    assert s.total == D("120.00") + D("60.00") + D("50.00")


def test_el_especialista_por_defecto_y_el_adicional_repetido_cuentan_una_vez() -> None:
    s = calcular(lima(18, 10), lima(18, 11), defecto=(INGENIERO,), elegidos=(INGENIERO, EJECUTANTE))
    assert [linea.concepto for linea in s.lineas] == [
        "Grabacion",
        "Ingeniero",
        "Ingeniero (monto fijo)",
        "Ejecutante",
        "Ejecutante (monto fijo)",
    ]


def test_noche_que_cruza_la_medianoche() -> None:
    s = calcular(lima(18, 21), lima(19, 1))
    assert s.lineas[0].monto == D("320.00")
    assert resumen(s) == [("noche", 8, D("80.00"))]
    assert s.total == D("400.00")


@pytest.mark.parametrize(
    ("inicio", "fin", "bloques"),
    [
        (lima(18, 19), lima(18, 21), 2),  # el bloque de las 20:00 ya es noche
        (lima(19, 5), lima(19, 7), 2),  # el bloque de las 06:00 ya es dia
        (lima(18, 19, 30), lima(18, 20), 0),  # el bloque de las 19:30 no es noche
    ],
)
def test_los_limites_de_la_noche_se_miden_por_bloque_de_30_min(
    inicio: datetime, fin: datetime, bloques: int
) -> None:
    assert sum(r.bloques for r in calcular(inicio, fin).recargos) == bloques


def test_ventana_de_noche_que_no_cruza_la_medianoche() -> None:
    r = Recargos(D(50), time(1, 0), time(3, 0), D(0), D(0))
    s = calcular(lima(18, 0, 30), lima(18, 3, 30), recargos=r)
    assert [(x.tipo, x.bloques) for x in s.recargos] == [("noche", 4)]  # 01:00 a 02:30


def test_fin_de_semana_sabado_y_domingo() -> None:
    assert resumen(calcular(lima(21, 10), lima(21, 12))) == [("fin_de_semana", 4, D("32.00"))]
    assert calcular(lima(22, 10), lima(22, 11)).recargos[0].tipo == "fin_de_semana"
    assert calcular(lima(20, 10), lima(20, 11)).recargos == ()  # viernes de dia


def test_feriado_por_la_fecha_de_lima_de_cada_bloque() -> None:
    s = calcular(lima(18, 23), lima(19, 1), feriados=(date(2026, 11, 19),))
    assert resumen(s) == [("noche", 2, D("20.00")), ("feriado", 2, D("24.00"))]
    assert s.total == D("160.00") + D("44.00")


def test_coincidencias_aplican_solo_el_mayor_porcentaje() -> None:
    noche_y_feriado = calcular(lima(18, 21), lima(18, 22), feriados=(date(2026, 11, 18),))
    assert resumen(noche_y_feriado) == [("feriado", 2, D("24.00"))]
    r = Recargos(D(10), time(20, 0), time(6, 0), D(50), D(30))
    sabado = calcular(lima(21, 21), lima(21, 22), recargos=r, feriados=(date(2026, 11, 21),))
    assert resumen(sabado) == [("fin_de_semana", 2, D("40.00"))]


def test_empate_de_porcentajes_prefiere_feriado_luego_fin_de_semana() -> None:
    r = Recargos(D(20), time(20, 0), time(6, 0), D(20), D(20))
    con_feriado = calcular(lima(21, 21), lima(21, 22), recargos=r, feriados=(date(2026, 11, 21),))
    assert [x.tipo for x in con_feriado.recargos] == ["feriado"]
    assert [x.tipo for x in calcular(lima(21, 21), lima(21, 22), recargos=r).recargos] == [
        "fin_de_semana"
    ]


def test_el_recargo_cubre_la_parte_variable_de_todos_los_componentes() -> None:
    s = calcular(lima(18, 21), lima(18, 22), defecto=(INGENIERO,), elegidos=(EJECUTANTE,))
    # por bloque: 40 (sala) + 25 (lapso) + 20 (media hora de ejecutante) = 85; 2 x 85 x 25 %
    assert s.recargos[0].monto == D("42.50")


def test_recargo_en_cero_no_genera_partida() -> None:
    r = Recargos(D(0), time(20, 0), time(6, 0), D(0), D(0))
    assert calcular(lima(18, 21), lima(18, 22), recargos=r).recargos == ()


def test_redondeo_a_centimos_mitad_hacia_arriba_y_anticipo() -> None:
    s = calcular(lima(18, 20), lima(18, 20, 30), svc=servicio("33.33"))
    assert s.lineas[0].monto == D("16.67")  # 16,665
    assert s.recargos[0].monto == D("4.17")  # 4,16625
    assert (s.total, s.anticipo) == (D("20.84"), D("10.42"))
    solo_sala = calcular(lima(18, 10), lima(18, 10, 30), svc=servicio("33.33"))
    assert solo_sala.anticipo == D("8.34")  # 8,335


def test_los_montos_conservan_dos_decimales() -> None:
    s = calcular(lima(18, 10), lima(18, 11))
    assert (str(s.total), str(s.anticipo), str(s.lineas[0].monto)) == ("80.00", "40.00", "80.00")


@pytest.mark.parametrize(
    ("inicio", "fin"),
    [
        (lima(18, 10, 15), lima(18, 11)),
        (lima(18, 10), lima(18, 11, 10)),
        (lima(18, 11), lima(18, 10)),
        (lima(18, 10), lima(18, 10)),
        (lima(18, 10), lima(18, 18, 30)),  # mas de 8 horas
        (datetime(2026, 11, 18, 10), datetime(2026, 11, 18, 11)),  # sin zona horaria
    ],
)
def test_tramo_invalido(inicio: datetime, fin: datetime) -> None:
    with pytest.raises(TramoInvalido):
        calcular(inicio, fin)


def test_tramos_limite_validos() -> None:
    calcular(lima(18, 10), lima(18, 10, 30))
    calcular(lima(18, 10), lima(18, 18))  # 8 horas


@pytest.mark.parametrize("extra", [{"ocupa_sala": False}, {"activo": False}])
def test_un_servicio_que_no_ocupa_sala_o_inactivo_no_se_reserva(extra: dict[str, Any]) -> None:
    with pytest.raises(ServicioNoReservable):
        calcular(lima(18, 10), lima(18, 11), svc=servicio(**extra))


def test_el_tramo_se_interpreta_en_hora_de_lima_aunque_llegue_en_utc() -> None:
    utc = UTC
    s = calcular(datetime(2026, 11, 19, 2, 0, tzinfo=utc), datetime(2026, 11, 19, 3, 0, tzinfo=utc))
    assert s.recargos[0].tipo == "noche"  # 21:00 a 22:00 en Lima


# --- IGV (RF-20 CA-02) ---


def test_igv_incluido_150_al_18_es_base_127_12_e_igv_22_88() -> None:
    assert desglosar_igv_incluido(D("150.00"), D("18.00")) == (D("127.12"), D("22.88"))


def test_igv_incluido_75_al_18_es_base_63_56_e_igv_11_44() -> None:
    assert desglosar_igv_incluido(D("75.00"), D("18.00")) == (D("63.56"), D("11.44"))


def test_igv_incluido_redondea_la_base_mitad_hacia_arriba() -> None:
    # 0.01 / 2 = 0.005 exacto: sube a 0.01 y el IGV queda en 0.00
    assert desglosar_igv_incluido(D("0.01"), D("100")) == (D("0.01"), D("0.00"))


def test_igv_incluido_con_0_por_ciento_no_hay_igv() -> None:
    assert desglosar_igv_incluido(D("150.00"), D("0")) == (D("150.00"), D("0.00"))


def test_igv_incluido_base_mas_igv_siempre_es_el_total() -> None:
    for centimos in range(1, 3000, 7):
        total = D(centimos) / 100
        base, igv = desglosar_igv_incluido(total, D("18.00"))
        assert base + igv == total and igv >= 0


def test_simulacion_con_igv_incluido_no_cambia_lineas_ni_total() -> None:
    s = calcular(lima(18, 10), lima(18, 12))
    assert s.total == D("160.00") and s.lineas[0].monto == D("160.00")
    assert s.impuesto == Impuesto(D("18.00"), True, D("135.59"), D("24.41"))


def test_simulacion_sin_igv_incluido_suma_el_igv_a_las_lineas() -> None:
    s = calcular(lima(18, 10), lima(18, 12), impuestos=ConfiguracionImpuestos(D("18.00"), False))
    assert s.lineas[0].monto == D("160.00")
    assert s.impuesto == Impuesto(D("18.00"), False, D("160.00"), D("28.80"))
    assert (s.total, s.anticipo) == (D("188.80"), D("94.40"))


def test_simulacion_sin_igv_redondea_el_igv_mitad_hacia_arriba() -> None:
    # 0.25 x 18 % = 0.045 -> 0.05 (el servicio de 0.50 por hora cuesta 0.25 en 30 min)
    s = calcular(
        lima(18, 10),
        lima(18, 10, 30),
        svc=servicio("0.50"),
        impuestos=ConfiguracionImpuestos(D("18.00"), False),
    )
    assert (s.impuesto.base, s.impuesto.monto, s.total) == (D("0.25"), D("0.05"), D("0.30"))


def test_el_anticipo_sale_del_porcentaje_de_adelanto_sobre_el_total() -> None:
    s = calcular(lima(18, 10), lima(18, 12), adelanto=30)
    assert s.anticipo == D("48.00") and s.porcentaje_adelanto == D("30.00")
    con_igv_aparte = calcular(
        lima(18, 10),
        lima(18, 12),
        impuestos=ConfiguracionImpuestos(D("18.00"), False),
        adelanto=25,
    )
    assert con_igv_aparte.anticipo == D("47.20")  # 25 % del total con IGV (188.80)
