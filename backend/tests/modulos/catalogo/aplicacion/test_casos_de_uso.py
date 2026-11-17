from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal
from uuid import uuid4

import pytest

from bugalu.compartido.errores import (
    ConfirmacionRequerida,
    DatosInvalidos,
    FeriadoRepetido,
    NoEncontrado,
    ServicioNoReservable,
    SinPermiso,
    TramoInvalido,
)
from bugalu.modulos.catalogo.aplicacion.actualizar_especialista.caso_de_uso import (
    ActualizarEspecialista,
)
from bugalu.modulos.catalogo.aplicacion.actualizar_servicio.caso_de_uso import ActualizarServicio
from bugalu.modulos.catalogo.aplicacion.agregar_feriado.caso_de_uso import AgregarFeriado
from bugalu.modulos.catalogo.aplicacion.eliminar_feriado.caso_de_uso import EliminarFeriado
from bugalu.modulos.catalogo.aplicacion.reemplazar_recargos.caso_de_uso import ReemplazarRecargos
from bugalu.modulos.catalogo.aplicacion.simular_precio.caso_de_uso import SimularPrecio
from bugalu.modulos.catalogo.dominio.precio import Feriado, Recargos
from tests.modulos.catalogo.aplicacion.falsos import (
    EJECUTANTE,
    INGENIERO,
    MEZCLA,
    SALA,
    SERVICIO,
    CatalogoFalso,
)

LIMA = timezone(timedelta(hours=-5))
D = Decimal


def tramo(dia: int, desde: int, hasta: int) -> tuple[datetime, datetime]:
    return datetime(2026, 11, dia, desde, tzinfo=LIMA), datetime(2026, 11, dia, hasta, tzinfo=LIMA)


async def test_la_simulacion_incluye_el_especialista_por_defecto_y_los_elegidos() -> None:
    inicio, fin = tramo(18, 10, 11)
    s = await SimularPrecio(CatalogoFalso()).ejecutar(
        SALA, SERVICIO.id, inicio, fin, [EJECUTANTE.id, INGENIERO.id, EJECUTANTE.id]
    )
    assert [x.concepto for x in s.lineas] == [
        "Grabacion",
        "Ingeniero",
        "Ingeniero (monto fijo)",
        "Ejecutante",
        "Ejecutante (monto fijo)",
    ]
    assert s.total == D("80") + D("50") + D("30") + D("40") + D("50")


async def test_la_simulacion_usa_los_feriados_de_la_base() -> None:
    catalogo = CatalogoFalso()
    catalogo.feriados[date(2026, 11, 18)] = Feriado(date(2026, 11, 18), "Prueba")
    inicio, fin = tramo(18, 10, 11)
    s = await SimularPrecio(catalogo).ejecutar(SALA, SERVICIO.id, inicio, fin, [])
    assert [r.tipo for r in s.recargos] == ["feriado"]


async def test_un_servicio_de_posproduccion_no_es_reservable() -> None:
    inicio, fin = tramo(18, 10, 11)
    with pytest.raises(ServicioNoReservable):
        await SimularPrecio(CatalogoFalso()).ejecutar(SALA, MEZCLA.id, inicio, fin, [])


async def test_tramo_que_no_es_multiplo_de_30_min_es_tramo_invalido() -> None:
    inicio = datetime(2026, 11, 18, 10, 10, tzinfo=LIMA)
    with pytest.raises(TramoInvalido):
        await SimularPrecio(CatalogoFalso()).ejecutar(
            SALA, SERVICIO.id, inicio, inicio + timedelta(hours=1), []
        )


@pytest.mark.parametrize("quien", ["sala", "servicio", "especialista", "inactivo"])
async def test_referencias_inexistentes_o_inactivas_son_datos_invalidos(quien: str) -> None:
    catalogo = CatalogoFalso()
    ids = {"sala": SALA, "servicio": SERVICIO.id, "especialista": EJECUTANTE.id}
    ids[quien] = uuid4()
    if quien == "inactivo":
        await catalogo.actualizar_especialista(EJECUTANTE.id, {"activo": False})
    inicio, fin = tramo(18, 10, 11)
    esp = [ids["especialista"]] if quien != "inactivo" else [EJECUTANTE.id]
    with pytest.raises(DatosInvalidos):
        await SimularPrecio(catalogo).ejecutar(ids["sala"], ids["servicio"], inicio, fin, esp)


async def test_un_especialista_por_defecto_inactivo_no_se_cobra() -> None:
    catalogo = CatalogoFalso()
    await catalogo.actualizar_especialista(INGENIERO.id, {"activo": False})
    inicio, fin = tramo(18, 10, 11)
    s = await SimularPrecio(catalogo).ejecutar(SALA, SERVICIO.id, inicio, fin, [])
    assert [x.concepto for x in s.lineas] == ["Grabacion"]


async def test_solo_el_administrador_escribe_y_el_catalogo_queda_intacto() -> None:
    c = CatalogoFalso(administrador=False)
    for llamada in (
        ActualizarServicio(c).ejecutar(SERVICIO.id, {"tarifa_hora": D("1")}),
        ActualizarEspecialista(c).ejecutar(EJECUTANTE.id, {"activo": False}),
        ReemplazarRecargos(c).ejecutar(Recargos(D(1), time(1), time(2), D(1), D(1))),
        AgregarFeriado(c).ejecutar(Feriado(date(2026, 12, 25), "Navidad")),
        EliminarFeriado(c).ejecutar(date(2026, 12, 25)),
    ):
        with pytest.raises(SinPermiso):
            await llamada
    assert c.escrituras == 0


async def test_actualizar_servicio_cambia_campos_y_reemplaza_los_especialistas_por_defecto() -> (
    None
):
    c = CatalogoFalso()
    nuevo = await ActualizarServicio(c).ejecutar(
        SERVICIO.id,
        {"activo": False, "especialistas_por_defecto": [EJECUTANTE.id, EJECUTANTE.id]},
    )
    assert nuevo.activo is False and nuevo.tarifa_hora == D("80")
    assert nuevo.especialistas_por_defecto == (EJECUTANTE.id,)


async def test_cambiar_un_sensible_exige_confirmacion_y_no_escribe_nada() -> None:
    c = CatalogoFalso()
    cambios = {"monto_fijo": D("12.50"), "activo": False}
    with pytest.raises(ConfirmacionRequerida) as error:
        await ActualizarServicio(c).ejecutar(SERVICIO.id, cambios)
    assert error.value.detalles == {"campos": ["monto_fijo"]}
    assert c.escrituras == 0
    await ActualizarServicio(c).ejecutar(SERVICIO.id, {"tarifa_hora": D("80.00")})  # mismo valor


async def test_actualizar_servicio_con_especialista_inexistente_no_cambia_nada() -> None:
    c = CatalogoFalso()
    with pytest.raises(DatosInvalidos):
        await ActualizarServicio(c).ejecutar(
            SERVICIO.id, {"activo": False, "especialistas_por_defecto": [uuid4()]}
        )
    assert c.escrituras == 0


async def test_actualizar_inexistentes_es_404() -> None:
    with pytest.raises(NoEncontrado):
        await ActualizarServicio(CatalogoFalso()).ejecutar(uuid4(), {"activo": False})
    with pytest.raises(NoEncontrado):
        await ActualizarEspecialista(CatalogoFalso()).ejecutar(uuid4(), {"activo": False})
    with pytest.raises(NoEncontrado):
        await EliminarFeriado(CatalogoFalso()).ejecutar(date(2026, 12, 25))


async def test_feriado_repetido_es_conflicto() -> None:
    c = CatalogoFalso()
    await AgregarFeriado(c).ejecutar(Feriado(date(2026, 12, 25), "Navidad"))
    with pytest.raises(FeriadoRepetido):
        await AgregarFeriado(c).ejecutar(Feriado(date(2026, 12, 25), "Otra vez"))
