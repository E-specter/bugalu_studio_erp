"""RF-20 CA-05: ejemplos de impacto con el mismo motor de precio."""

from dataclasses import replace
from datetime import UTC, datetime, time
from decimal import Decimal
from uuid import uuid4

from bugalu.modulos.catalogo.dominio import impacto
from bugalu.modulos.catalogo.dominio.precio import (
    ConfiguracionImpuestos,
    Especialista,
    Recargos,
    Servicio,
    Unidad,
)

D = Decimal

SERVICIO = Servicio(uuid4(), "Voces", "grabacion", False, D("80"), D("0"), (), True)
IGV = ConfiguracionImpuestos(D("18"), True)
AHORA = datetime(2026, 12, 1, 15, tzinfo=UTC)


def test_servicio_2_horas_en_horario_normal_aunque_no_ocupe_sala() -> None:
    [e] = impacto.ejemplos_servicio(SERVICIO, replace(SERVICIO, tarifa_hora=D("100")), IGV)
    assert (e.tipo, e.antes, e.despues) == ("importe", "160.00", "200.00")
    assert "2 h" in e.concepto and "Voces" in e.concepto


def test_especialista_se_suma_a_cada_servicio_que_lo_trae() -> None:
    esp = Especialista(uuid4(), "Ing", D(0), D("20"), Unidad.HORA, True)
    [e] = impacto.ejemplos_especialista(
        [(SERVICIO, [])], esp, replace(esp, monto_variable=D("30")), IGV
    )
    assert (e.antes, e.despues) == ("200.00", "220.00")


def test_recargo_de_fin_de_semana_se_ve_en_un_sabado() -> None:
    antes = Recargos(D(0), time(22), time(6), D(20), D(0))
    despues = replace(antes, fin_de_semana=D(50))
    [e] = impacto.ejemplos_recargos(SERVICIO, antes, despues, IGV, ["fin_de_semana.porcentaje"])
    assert (e.antes, e.despues) == ("192.00", "240.00")


def test_impuestos_desglosa_100() -> None:
    primero, segundo = impacto.ejemplos_impuestos(IGV, ConfiguracionImpuestos(D("10"), False))
    assert (primero.antes, primero.despues) == ("15.25", "10.00")
    assert (segundo.antes, segundo.despues) == ("100.00", "110.00")


def test_parametros_plazos_adelanto_y_nivel() -> None:
    antes = {"dias_limite_pago": 5, "horas_limite_pago": 1, "porcentaje_adelanto": 50,
             "horas_nivel_1": 48, "horas_nivel_2": 24, "porcentaje_penalizacion_nivel_2": 25,
             "dias_vigencia_credito": 30}  # fmt: skip
    despues = {**antes, "horas_limite_pago": 3, "porcentaje_adelanto": 40, "horas_nivel_1": 20,
               "horas_nivel_2": 10, "dias_vigencia_credito": 45}  # fmt: skip
    cambiados = {"horas_limite_pago", "porcentaje_adelanto", "horas_nivel_1", "horas_nivel_2",
                 "dias_vigencia_credito"}  # fmt: skip
    ejemplos = {
        e.concepto: e for e in impacto.ejemplos_parametros(antes, despues, cambiados, AHORA)
    }
    tipos = {e.tipo for e in ejemplos.values()}
    assert tipos == {"fecha_hora", "importe", "texto"}
    adelanto = next(e for e in ejemplos.values() if "adelanto" in e.concepto.lower())
    assert (adelanto.antes, adelanto.despues) == ("100.00", "80.00")


def test_parametros_de_danos_se_muestran_como_importe_y_texto() -> None:
    antes = {"tarifa_hora_gestion": D("0.00"), "tope_horas_sesiones_perdidas": 8}
    despues = {"tarifa_hora_gestion": D("25.50"), "tope_horas_sesiones_perdidas": 12}
    ejemplos = {
        e.concepto: e for e in impacto.ejemplos_parametros(antes, despues, set(antes), AHORA)
    }
    tarifa = ejemplos["Tarifa por hora de gestión"]
    assert (tarifa.antes, tarifa.despues, tarifa.tipo) == ("0.00", "25.50", "importe")
    tope = ejemplos["Tope por sesiones perdidas"]
    assert (tope.antes, tope.despues, tope.tipo) == ("8", "12", "texto")
