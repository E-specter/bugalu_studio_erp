from datetime import datetime, timedelta, timezone
from decimal import Decimal
from uuid import UUID, uuid4

import pytest

from bugalu.compartido.errores import (
    AlmacenamientoNoDisponible,
    ArchivoMuyGrande,
    ConfirmacionRequerida,
    DatosInvalidos,
    FormatoNoAdmitido,
    HorarioConAsesorias,
    HorarioSolapado,
    NoEncontrado,
    RangoInvalido,
    SinPermiso,
)
from bugalu.modulos.asesorias.aplicacion.disponibilidad.caso_de_uso import (
    ConsultarDisponibilidadProfesional,
)
from bugalu.modulos.asesorias.aplicacion.especialidades.caso_de_uso import (
    ActualizarEspecialidad,
    CrearEspecialidad,
    ListarEspecialidades,
)
from bugalu.modulos.asesorias.aplicacion.foto.caso_de_uso import QuitarFoto, ReemplazarFoto
from bugalu.modulos.asesorias.aplicacion.horarios.caso_de_uso import (
    PublicarHorarios,
    RetirarHorario,
    SugerirHorarios,
)
from bugalu.modulos.asesorias.aplicacion.perfiles.caso_de_uso import (
    ActualizarProfesional,
    ListarProfesionales,
    ObtenerProfesional,
)
from bugalu.modulos.asesorias.dominio.foto import LIMITE_BYTES
from bugalu.modulos.reservas.dominio.disponibilidad import Tramo
from tests.modulos.asesorias.aplicacion.falsos import (
    MEZCLA,
    PABLO,
    PAULA,
    AlmacenFalso,
    RepositorioFalso,
    perfil,
)

LIMA = timezone(timedelta(hours=-5))
AHORA = datetime(2026, 12, 1, 9, tzinfo=LIMA)
JPEG = b"\xff\xd8\xff\xe0" + b"0" * 100


def t(dia: int, hora: int) -> Tramo:
    return Tramo(
        datetime(2026, 12, dia, hora, tzinfo=LIMA), datetime(2026, 12, dia, hora + 1, tzinfo=LIMA)
    )


# --- especialidades (CA-02) ---


async def test_solo_el_administrador_ve_todas_las_especialidades() -> None:
    with pytest.raises(SinPermiso):
        await ListarEspecialidades(RepositorioFalso()).ejecutar(todas=True)
    assert await ListarEspecialidades(RepositorioFalso()).ejecutar(todas=False) == [MEZCLA]


async def test_crear_y_cambiar_especialidades_es_del_administrador() -> None:
    with pytest.raises(SinPermiso):
        await CrearEspecialidad(RepositorioFalso()).ejecutar("Coros")
    repo = RepositorioFalso(administrador=True)
    nueva = await CrearEspecialidad(repo).ejecutar("Coros")
    desactivada = await ActualizarEspecialidad(repo).ejecutar(nueva.id, {"activa": False})
    assert not desactivada.activa
    with pytest.raises(NoEncontrado):
        await ActualizarEspecialidad(repo).ejecutar(uuid4(), {"activa": False})


# --- perfiles (CA-03, CA-04) ---


async def test_el_visitante_ve_solo_publicados_y_el_administrador_todos() -> None:
    repo = RepositorioFalso()
    repo.perfiles[PAULA] = perfil(PAULA, publicado=False)
    visibles, ve_estado = await ListarProfesionales(repo).ejecutar(None, con_sesion=False)
    assert [p.id for p in visibles] == [PABLO] and not ve_estado
    repo.administrador = True
    todos, ve_estado = await ListarProfesionales(repo).ejecutar(None, con_sesion=True)
    assert len(todos) == 2 and ve_estado


async def test_el_estado_lo_ven_el_propio_y_el_administrador() -> None:
    repo = RepositorioFalso()
    assert (await ObtenerProfesional(repo).ejecutar(PABLO, None))[1] is False
    assert (await ObtenerProfesional(repo).ejecutar(PABLO, PAULA))[1] is False
    assert (await ObtenerProfesional(repo).ejecutar(PABLO, PABLO))[1] is True
    repo.administrador = True
    assert (await ObtenerProfesional(repo).ejecutar(PABLO, PAULA))[1] is True
    with pytest.raises(NoEncontrado):
        await ObtenerProfesional(repo).ejecutar(uuid4(), PABLO)


async def test_un_profesional_no_edita_el_perfil_de_otro_y_no_se_escribe_nada() -> None:
    repo = RepositorioFalso()
    with pytest.raises(SinPermiso):
        await ActualizarProfesional(repo).ejecutar(PAULA, PABLO, {"presentacion": "x"})
    assert repo.escrituras == []


async def test_el_profesional_no_toca_activo_ni_precios() -> None:
    repo = RepositorioFalso()
    for campo in ("activo", "precios"):
        with pytest.raises(SinPermiso):
            await ActualizarProfesional(repo).ejecutar(PABLO, PABLO, {campo: True})
    assert repo.escrituras == []


async def test_el_profesional_edita_lo_suyo() -> None:
    repo = RepositorioFalso()
    await ActualizarProfesional(repo).ejecutar(
        PABLO, PABLO, {"presentacion": "Hola", "especialidades": [MEZCLA.id]}
    )
    assert repo.escrituras == ["especialidades", "perfil"]


async def test_cambiar_un_precio_pide_confirmacion_y_no_escribe() -> None:
    repo = RepositorioFalso(administrador=True)
    with pytest.raises(ConfirmacionRequerida) as error:
        await ActualizarProfesional(repo).ejecutar(
            PAULA, PABLO, {"presentacion": "x", "precios": {30: Decimal("60.00")}}
        )
    assert error.value.detalles == {"campos": ["precio_30"]}
    assert repo.escrituras == []


async def test_un_precio_igual_no_pide_confirmacion_y_activar_es_del_administrador() -> None:
    repo = RepositorioFalso(administrador=True)
    await ActualizarProfesional(repo).ejecutar(
        PAULA, PABLO, {"precios": {30: Decimal("50")}, "activo": False}
    )
    assert repo.escrituras == ["estado"]


async def test_ofrecer_una_duracion_nueva_o_quitarla_es_sensible() -> None:
    repo = RepositorioFalso(administrador=True)
    for precios, campo in (({60: Decimal("90")}, "precio_60"), ({30: None}, "precio_30")):
        with pytest.raises(ConfirmacionRequerida) as error:
            await ActualizarProfesional(repo).ejecutar(PAULA, PABLO, {"precios": precios})
        assert error.value.detalles == {"campos": [campo]}


# --- foto (CA-03) ---


async def test_la_foto_se_sube_a_una_ruta_fija_por_perfil_y_se_guarda() -> None:
    repo, almacen = RepositorioFalso(), AlmacenFalso()
    reemplazo = await ReemplazarFoto(repo, almacen).ejecutar(PABLO, PABLO, JPEG)
    assert reemplazo.nueva == f"{PABLO}/foto-1" and reemplazo.anterior is None
    assert almacen.subidos == [(f"{PABLO}/foto-1", "image/jpeg")]
    assert repo.escrituras == [f"foto:{PABLO}/foto-1"]


async def test_reemplazar_lee_el_perfil_bloqueando_la_fila() -> None:
    repo, almacen = RepositorioFalso(), AlmacenFalso()
    await ReemplazarFoto(repo, almacen).ejecutar(PABLO, PABLO, JPEG)
    assert repo.bloqueos == [True]


async def test_reemplazar_alterna_la_ruta_y_no_borra_la_anterior_hasta_confirmar() -> None:
    repo, almacen = RepositorioFalso(), AlmacenFalso()
    repo.perfiles[PABLO] = perfil(PABLO, foto_ruta=f"{PABLO}/foto-1")
    caso = ReemplazarFoto(repo, almacen)
    reemplazo = await caso.ejecutar(PABLO, PABLO, JPEG)
    assert (reemplazo.nueva, reemplazo.anterior) == (f"{PABLO}/foto-2", f"{PABLO}/foto-1")
    assert almacen.borrados == []  # el commit aun no ocurrio
    await caso.confirmar(reemplazo)
    assert almacen.borrados == [f"{PABLO}/foto-1"]


async def test_si_la_base_falla_la_foto_nueva_se_borra_y_la_anterior_sigue() -> None:
    repo, almacen = RepositorioFalso(), AlmacenFalso()
    repo.perfiles[PABLO] = perfil(PABLO, foto_ruta=f"{PABLO}/foto-1")

    async def falla(id_profesional: UUID, ruta: str | None) -> None:
        raise RuntimeError("base caida")

    repo.fijar_foto = falla  # type: ignore[method-assign]
    with pytest.raises(RuntimeError):
        await ReemplazarFoto(repo, almacen).ejecutar(PABLO, PABLO, JPEG)
    assert almacen.borrados == [f"{PABLO}/foto-2"]


async def test_descartar_borra_la_nueva_si_el_commit_falla_despues() -> None:
    almacen = AlmacenFalso()
    caso = ReemplazarFoto(RepositorioFalso(), almacen)
    reemplazo = await caso.ejecutar(PABLO, PABLO, JPEG)
    await caso.descartar(reemplazo)
    assert almacen.borrados == [reemplazo.nueva]


async def test_una_foto_demasiado_grande_o_de_otro_formato_se_rechaza_sin_subir() -> None:
    repo, almacen = RepositorioFalso(), AlmacenFalso()
    with pytest.raises(ArchivoMuyGrande):
        await ReemplazarFoto(repo, almacen).ejecutar(PABLO, PABLO, JPEG + b"0" * LIMITE_BYTES)
    with pytest.raises(FormatoNoAdmitido):
        await ReemplazarFoto(repo, almacen).ejecutar(PABLO, PABLO, b"%PDF-1.7 000000")
    assert almacen.subidos == [] and repo.escrituras == []


async def test_la_foto_de_otro_no_se_sube() -> None:
    repo, almacen = RepositorioFalso(), AlmacenFalso()
    with pytest.raises(SinPermiso):
        await ReemplazarFoto(repo, almacen).ejecutar(PAULA, PABLO, JPEG)
    assert almacen.subidos == []


async def test_con_el_almacenamiento_caido_no_se_guarda_ruta() -> None:
    repo = RepositorioFalso()
    with pytest.raises(AlmacenamientoNoDisponible):
        await ReemplazarFoto(repo, AlmacenFalso(caido=True)).ejecutar(PABLO, PABLO, JPEG)
    assert repo.escrituras == []


async def test_quitar_la_foto_la_borra_del_almacen() -> None:
    repo, almacen = RepositorioFalso(), AlmacenFalso()
    repo.perfiles[PABLO] = perfil(PABLO, foto_ruta=f"{PABLO}/a.png")
    await QuitarFoto(repo, almacen).ejecutar(PABLO, PABLO)
    assert repo.escrituras == ["foto:None"] and almacen.borrados == [f"{PABLO}/a.png"]
    with pytest.raises(AlmacenamientoNoDisponible):  # estricto: el llamador revierte la base
        await QuitarFoto(repo, AlmacenFalso(caido=True)).ejecutar(PABLO, PABLO)


# --- horarios (CA-05) ---


async def test_publicar_horarios_valida_y_exige_ser_el_propio_o_administrador() -> None:
    repo = RepositorioFalso()
    publicados = await PublicarHorarios(repo).ejecutar(PABLO, PABLO, [t(7, 8), t(7, 9)], AHORA)
    assert len(publicados) == 2
    with pytest.raises(HorarioSolapado):
        await PublicarHorarios(repo).ejecutar(PABLO, PABLO, [t(7, 8)], AHORA)
    with pytest.raises(SinPermiso):
        await PublicarHorarios(repo).ejecutar(PAULA, PABLO, [t(8, 8)], AHORA)
    with pytest.raises(DatosInvalidos):
        await PublicarHorarios(repo).ejecutar(PABLO, PABLO, [t(1, 8)], AHORA)
    with pytest.raises(NoEncontrado):
        await PublicarHorarios(repo).ejecutar(PABLO, uuid4(), [t(8, 8)], AHORA)


async def test_la_sugerencia_copia_la_ultima_semana_publicada() -> None:
    repo = RepositorioFalso()
    await PublicarHorarios(repo).ejecutar(PABLO, PABLO, [t(7, 8)], AHORA)  # lunes 7 de dic
    sugeridos = await SugerirHorarios(repo).ejecutar(PABLO, PABLO, "2026-W51")  # lunes 14
    assert sugeridos == [t(14, 8)]
    with pytest.raises(DatosInvalidos):
        await SugerirHorarios(repo).ejecutar(PABLO, PABLO, "2026-W99")


async def test_retirar_un_bloque_propio_y_la_regla_de_asesorias_vivas() -> None:
    repo = RepositorioFalso()
    [horario] = await PublicarHorarios(repo).ejecutar(PABLO, PABLO, [t(7, 8)], AHORA)
    repo.vivas = [uuid4()]
    with pytest.raises(HorarioConAsesorias) as error:
        await RetirarHorario(repo).ejecutar(PABLO, PABLO, horario.id)
    assert error.value.detalles == {"asesorias": [str(repo.vivas[0])]}
    assert len(repo.horarios) == 1
    repo.vivas = []
    with pytest.raises(SinPermiso):
        await RetirarHorario(repo).ejecutar(PAULA, PABLO, horario.id)
    await RetirarHorario(repo).ejecutar(PABLO, PABLO, horario.id)
    assert repo.horarios == []
    with pytest.raises(NoEncontrado):
        await RetirarHorario(repo).ejecutar(PABLO, PABLO, horario.id)


# --- disponibilidad (CA-05) ---


async def test_la_disponibilidad_trae_limites_horarios_dias_y_duraciones() -> None:
    repo = RepositorioFalso()
    await PublicarHorarios(repo).ejecutar(PABLO, PABLO, [t(7, 8), t(7, 9)], AHORA)
    desde, hasta = datetime(2026, 12, 7, tzinfo=LIMA), datetime(2026, 12, 9, tzinfo=LIMA)
    d = await ConsultarDisponibilidadProfesional(repo).ejecutar(PABLO, desde, hasta, AHORA)
    assert (d.limites.desde, d.limites.hasta) == (
        AHORA + timedelta(hours=2),
        AHORA + timedelta(weeks=8),
    )
    assert len(d.horarios) == 2 and d.ocupados == []
    assert [(x.fecha.day, x.minutos) for x in d.dias] == [(7, 120), (8, 0)]
    assert [(x.minutos, x.precio, x.igv.monto) for x in d.duraciones] == [
        (30, Decimal("50.00"), Decimal("7.63"))
    ]


async def test_la_disponibilidad_respeta_la_anticipacion_de_la_sala() -> None:
    repo = RepositorioFalso()
    repo.minima = 24 * 7
    await PublicarHorarios(repo).ejecutar(PABLO, PABLO, [t(7, 8)], AHORA)
    d = await ConsultarDisponibilidadProfesional(repo).ejecutar(
        PABLO, datetime(2026, 12, 7, tzinfo=LIMA), datetime(2026, 12, 8, tzinfo=LIMA), AHORA
    )
    assert d.dias[0].minutos == 0


async def test_disponibilidad_rango_invalido_y_perfil_inexistente() -> None:
    repo = RepositorioFalso()
    d = datetime(2026, 12, 7, tzinfo=LIMA)
    with pytest.raises(RangoInvalido):
        await ConsultarDisponibilidadProfesional(repo).ejecutar(PABLO, d, d, AHORA)
    with pytest.raises(RangoInvalido):
        await ConsultarDisponibilidadProfesional(repo).ejecutar(
            PABLO, d, d + timedelta(days=43), AHORA
        )
    with pytest.raises(NoEncontrado):
        await ConsultarDisponibilidadProfesional(repo).ejecutar(
            uuid4(), d, d + timedelta(days=1), AHORA
        )
