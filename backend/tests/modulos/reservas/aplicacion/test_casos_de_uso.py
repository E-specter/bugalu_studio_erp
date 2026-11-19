from decimal import Decimal
from uuid import UUID, uuid4

import pytest

from bugalu.compartido.errores import (
    CierreConReservas,
    ConfirmacionRequerida,
    DatosInvalidos,
    FranjaConReservas,
    FranjaSolapada,
    NoEncontrado,
    RangoInvalido,
    SinPermiso,
)
from bugalu.modulos.reservas.aplicacion.actualizar_parametros.caso_de_uso import (
    ActualizarParametros,
)
from bugalu.modulos.reservas.aplicacion.consultar_disponibilidad.caso_de_uso import (
    ConsultarDisponibilidad,
)
from bugalu.modulos.reservas.aplicacion.obtener_parametros_danos.caso_de_uso import (
    ObtenerParametrosDanos,
)
from bugalu.modulos.reservas.aplicacion.publicar_franjas.caso_de_uso import PublicarFranjas
from bugalu.modulos.reservas.aplicacion.quitar_cierre.caso_de_uso import QuitarCierre
from bugalu.modulos.reservas.aplicacion.registrar_cierre.caso_de_uso import RegistrarCierre
from bugalu.modulos.reservas.aplicacion.retirar_franja.caso_de_uso import RetirarFranja
from bugalu.modulos.reservas.aplicacion.sugerir_franjas.caso_de_uso import SugerirFranjas
from bugalu.modulos.reservas.dominio.disponibilidad import Tramo
from bugalu.modulos.reservas.dominio.modelos import ReservaVisible
from tests.modulos.reservas.aplicacion.falsos import SALA, ReservasFalso, t

AHORA = t(1, 0)


def tr(dia: int, h1: int, h2: int) -> Tramo:
    return Tramo(t(dia, h1), t(dia, h2))


def reserva(cliente: UUID, dia: int = 7, h1: int = 9, h2: int = 11) -> ReservaVisible:
    return ReservaVisible(
        uuid4(), "R-2026-00001", cliente, "Ensayo", "confirmada", t(dia, h1), t(dia, h2)
    )


async def test_publicar_franjas_exige_administrador_y_no_escribe() -> None:
    falso = ReservasFalso(administrador=False)
    with pytest.raises(SinPermiso):
        await PublicarFranjas(falso).ejecutar(SALA.id, [tr(7, 8, 12)])
    assert not falso.franjas


async def test_publicar_franjas_en_sala_inexistente_es_404() -> None:
    with pytest.raises(NoEncontrado):
        await PublicarFranjas(ReservasFalso()).ejecutar(uuid4(), [tr(7, 8, 12)])


async def test_publicar_franjas_solapadas_deja_el_409_de_la_base() -> None:
    falso = ReservasFalso()
    await PublicarFranjas(falso).ejecutar(SALA.id, [tr(7, 8, 12)])
    with pytest.raises(FranjaSolapada):
        await PublicarFranjas(falso).ejecutar(SALA.id, [tr(7, 11, 14)])


async def test_retirar_franja_con_reservas_vigentes_es_409_y_la_conserva() -> None:
    falso = ReservasFalso()
    [franja] = await PublicarFranjas(falso).ejecutar(SALA.id, [tr(7, 8, 12)])
    falso.ocupados = [tr(7, 9, 11)]
    with pytest.raises(FranjaConReservas):
        await RetirarFranja(falso).ejecutar(franja.id)
    assert franja.id in falso.franjas
    falso.ocupados = []
    await RetirarFranja(falso).ejecutar(franja.id)
    assert not falso.franjas
    with pytest.raises(NoEncontrado):
        await RetirarFranja(falso).ejecutar(franja.id)


async def test_cierre_con_reservas_lista_folio_cliente_e_inicio() -> None:
    falso = ReservasFalso()
    cliente = uuid4()
    falso.ocupados = [tr(7, 9, 11)]
    falso.visibles = [reserva(cliente)]
    falso.nombres = {cliente: "Ana"}
    with pytest.raises(CierreConReservas) as e:
        await RegistrarCierre(falso).ejecutar(SALA.id, tr(7, 8, 12), "Mantenimiento")
    assert e.value.detalles is not None
    [r] = e.value.detalles["reservas"]
    assert (r["folio"], r["cliente"], r["inicio"]) == ("R-2026-00001", "Ana", t(7, 9).isoformat())
    assert UUID(r["id"]) and not falso.cierres


async def test_cierre_sin_reservas_se_registra_y_se_quita() -> None:
    falso = ReservasFalso()
    cierre = await RegistrarCierre(falso).ejecutar(SALA.id, tr(7, 8, 12), "Feriado")
    assert falso.cierres[cierre.id].motivo == "Feriado"
    await QuitarCierre(falso).ejecutar(cierre.id)
    with pytest.raises(NoEncontrado):
        await QuitarCierre(falso).ejecutar(cierre.id)


async def test_cierre_exige_administrador() -> None:
    sin_permiso = ReservasFalso(administrador=False)
    with pytest.raises(SinPermiso):
        await RegistrarCierre(sin_permiso).ejecutar(SALA.id, tr(7, 8, 12), "X")
    with pytest.raises(SinPermiso):
        await QuitarCierre(sin_permiso).ejecutar(uuid4())


async def test_sugerencia_desplaza_la_ultima_semana_y_exige_administrador() -> None:
    falso = ReservasFalso()
    await PublicarFranjas(falso).ejecutar(SALA.id, [tr(7, 8, 12)])
    r = await SugerirFranjas(falso).ejecutar(SALA.id, "2026-W51")  # lunes 14 de diciembre
    assert r == [tr(14, 8, 12)]
    with pytest.raises(SinPermiso):
        await SugerirFranjas(ReservasFalso(administrador=False)).ejecutar(SALA.id, "2026-W51")


async def test_sugerencia_con_semana_inexistente_es_422_con_su_campo() -> None:
    with pytest.raises(DatosInvalidos) as e:
        await SugerirFranjas(ReservasFalso()).ejecutar(SALA.id, "2027-W53")
    assert e.value.detalles == {"campo": "semana"}


async def test_parametros_actualizan_solo_los_enviados_y_exigen_administrador() -> None:
    falso = ReservasFalso()
    r = await ActualizarParametros(falso).ejecutar({"anticipacion_minima_horas": 4})
    assert r["anticipacion_minima_horas"] == 4 and r["dias_limite_pago"] == 3
    with pytest.raises(SinPermiso):
        await ActualizarParametros(ReservasFalso(administrador=False)).ejecutar(
            {"dias_limite_pago": 9}
        )
    # RF-20: un sensible con otro valor pide confirmacion y no cambia nada; el mismo valor pasa.
    with pytest.raises(ConfirmacionRequerida):
        await ActualizarParametros(falso).ejecutar({"horas_limite_pago": 4})
    assert falso.parametros["horas_limite_pago"] == 1
    await ActualizarParametros(falso).ejecutar({"horas_limite_pago": 1})


async def test_los_parametros_de_danos_son_sensibles_y_el_mismo_valor_no_se_guarda() -> None:
    falso = ReservasFalso()
    for cambios in ({"tarifa_hora_gestion": Decimal("25.00")}, {"tope_horas_sesiones_perdidas": 9}):
        with pytest.raises(ConfirmacionRequerida) as error:
            await ActualizarParametros(falso).ejecutar({**cambios, "anticipacion_minima_horas": 5})
        assert error.value.detalles == {"campos": list(cambios)}
    assert falso.guardados == [] and falso.parametros["anticipacion_minima_horas"] == 2
    r = await ActualizarParametros(falso).ejecutar(
        {"tarifa_hora_gestion": Decimal("0.0"), "tope_horas_sesiones_perdidas": 8}
    )
    assert r["tarifa_hora_gestion"] == Decimal("0.00") and r["tope_horas_sesiones_perdidas"] == 8
    assert falso.guardados == []  # nada cambio: no se escribe


async def test_parametros_de_danos_los_lee_cualquiera_sin_ser_administrador() -> None:
    falso = ReservasFalso(administrador=False, personal=False)
    r = await ObtenerParametrosDanos(falso).ejecutar()
    assert (r.tarifa_hora_gestion, r.tope_horas_sesiones_perdidas) == (Decimal("0.00"), 8)


async def test_disponibilidad_fuera_de_1_a_42_dias_es_rango_invalido() -> None:
    c = ConsultarDisponibilidad(ReservasFalso())
    for desde, hasta in (
        (t(7, 0), t(7, 0)),
        (t(8, 0), t(7, 0)),
        (t(1, 0), t(1, 0).replace(month=1, day=13, year=2027)),
    ):
        with pytest.raises(RangoInvalido):
            await c.ejecutar(SALA.id, desde, hasta, AHORA, None)
    await c.ejecutar(SALA.id, t(1, 0), t(1, 0).replace(month=1, day=12, year=2027), AHORA, None)


async def test_disponibilidad_de_sala_inexistente_es_404() -> None:
    with pytest.raises(NoEncontrado):
        await ConsultarDisponibilidad(ReservasFalso()).ejecutar(
            uuid4(), t(7, 0), t(14, 0), AHORA, None
        )


async def test_visitante_no_ve_datos_de_nadie_y_el_cliente_ve_solo_su_propia() -> None:
    falso = ReservasFalso(personal=False)
    yo, otro = uuid4(), uuid4()
    falso.ocupados = [tr(7, 9, 11), tr(7, 12, 14)]
    falso.visibles = [reserva(yo)]
    c = ConsultarDisponibilidad(falso)
    publico = await c.ejecutar(SALA.id, t(7, 0), t(8, 0), AHORA, None)
    assert [(o.propia, o.reserva, o.cliente) for o in publico.ocupados] == [(False, None, None)] * 2
    cliente = await c.ejecutar(SALA.id, t(7, 0), t(8, 0), AHORA, yo)
    assert [(o.propia, o.reserva, o.cliente) for o in cliente.ocupados] == [
        (True, None, None),
        (False, None, None),
    ]
    ajeno = await c.ejecutar(SALA.id, t(7, 0), t(8, 0), AHORA, otro)
    assert [o.propia for o in ajeno.ocupados] == [False, False]


async def test_personal_ve_el_detalle_con_el_nombre_del_cliente() -> None:
    falso = ReservasFalso(personal=True)
    cliente = uuid4()
    falso.ocupados = [tr(7, 9, 11)]
    falso.visibles = [reserva(cliente)]
    falso.nombres = {cliente: "Ana"}
    r = await ConsultarDisponibilidad(falso).ejecutar(SALA.id, t(7, 0), t(8, 0), AHORA, uuid4())
    [o] = r.ocupados
    assert o.reserva is not None and o.reserva.servicio == "Ensayo" and o.cliente == "Ana"
    assert o.propia is False
