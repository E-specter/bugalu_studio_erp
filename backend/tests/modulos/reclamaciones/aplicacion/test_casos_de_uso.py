from dataclasses import replace
from datetime import UTC, date, datetime, timedelta
from uuid import uuid4

import pytest

from bugalu.compartido.errores import (
    AdjuntoNoPermitido,
    ConfirmacionDeHojaRequerida,
    DatosInvalidos,
    FechaOriginalInvalida,
    NoEncontrado,
    RangoInvalido,
    SinPermiso,
    YaRespondida,
)
from bugalu.modulos.reclamaciones.aplicacion.consultar.caso_de_uso import (
    ExportarHojas,
    ListarHojas,
    ListarMisHojas,
    ObtenerHoja,
    UrlAdjunto,
)
from bugalu.modulos.reclamaciones.aplicacion.limpiar.caso_de_uso import LimpiarAdjuntosHuerfanos
from bugalu.modulos.reclamaciones.aplicacion.registrar.caso_de_uso import (
    RegistrarHoja,
    TranscribirHoja,
)
from bugalu.modulos.reclamaciones.aplicacion.responder.caso_de_uso import ResponderHoja
from bugalu.modulos.reclamaciones.dominio.modelos import Autor, Respuesta
from tests.modulos.reclamaciones.aplicacion.falsos import (
    AHORA,
    AlmacenFalso,
    HojasFalso,
    abridor,
    adjunto,
    contenido,
    hoja,
)

PNG = b"\x89PNG\r\n\x1a\n" + b"x" * 10


def registrar(repo: HojasFalso, almacen: AlmacenFalso) -> RegistrarHoja:
    return RegistrarHoja(abridor(repo), abridor(repo), almacen)


def transcribir(repo: HojasFalso, almacen: AlmacenFalso) -> TranscribirHoja:
    return TranscribirHoja(abridor(repo), abridor(repo), almacen, lambda: AHORA)


async def test_registrar_sin_confirmar_no_toca_la_base() -> None:
    repo = HojasFalso()
    with pytest.raises(ConfirmacionDeHojaRequerida):
        await registrar(repo, AlmacenFalso()).ejecutar(contenido(), False, False, [], "1.2.3.4")
    assert repo.eventos == []


async def test_registrar_un_adjunto_invalido_no_registra_nada() -> None:
    repo = HojasFalso()
    with pytest.raises(AdjuntoNoPermitido):
        await registrar(repo, AlmacenFalso()).ejecutar(
            contenido(), True, False, [("a.png", b"no es nada")], None
        )
    assert repo.eventos == []


async def test_registrar_confirma_la_hoja_antes_de_subir_y_confirma_cada_adjunto_tras_subirlo() -> (
    None
):
    repo = HojasFalso()
    almacen = AlmacenFalso(eventos=repo.eventos)
    registro = await registrar(repo, almacen).ejecutar(
        contenido(), True, True, [("a.png", PNG), ("b.png", PNG)], "1.2.3.4"
    )
    assert repo.ultima_alta is not None
    id_, nueva, ip = repo.ultima_alta
    assert ip == "1.2.3.4"
    assert nueva.revisar_spam is True
    rutas = [r for r, _, _ in almacen.subidos]
    assert all(r.startswith(f"{id_}/") and r.endswith(".png") for r in rutas)
    assert len(set(rutas)) == 2
    assert repo.eventos == [
        "abre", "registrar", "cierra",  # la hoja se confirma antes de que Storage vea las subidas
        f"subir:{rutas[0]}", "abre", f"confirmar:{rutas[0]}", "cierra",
        f"subir:{rutas[1]}", "abre", f"confirmar:{rutas[1]}", "cierra",
        "abre", f"avisar:{id_}", "cierra",  # los avisos salen cuando termina la subida
    ]  # fmt: skip
    hoja_creada = registro.hoja
    assert (hoja_creada.id, hoja_creada.numero, hoja_creada.estado) == (
        id_,
        "000000007-2026",
        "pendiente",
    )
    assert (registro.creada, registro.no_guardados) == (True, [])
    assert [(a.n, a.ruta) for a in hoja_creada.adjuntos] == [(1, rutas[0]), (2, rutas[1])]
    assert hoja_creada.origen == "web"
    assert hoja_creada.revisar_spam is None  # el consumidor no ve la marca
    assert hoja_creada.dias_habiles_restantes == 15


async def test_si_falla_la_subida_la_hoja_se_conserva_se_registra_y_se_indica(
    caplog: pytest.LogCaptureFixture,
) -> None:
    repo = HojasFalso()
    with caplog.at_level("ERROR"):
        registro = await registrar(repo, AlmacenFalso(falla_en=2)).ejecutar(
            contenido(), True, False, [("a.png", PNG), ("b.png", PNG)], None
        )
    assert registro.no_guardados == [2]
    assert [a.n for a in registro.hoja.adjuntos] == [1]
    assert registro.creada is True
    assert repo.confirmaciones == 1  # el 2 no llega a confirmarse
    assert str(registro.hoja.id) in caplog.text and "2" in caplog.text


async def test_una_confirmacion_fallida_se_reintenta_una_vez() -> None:
    repo = HojasFalso()
    repo.falla_confirmar_en = 1  # solo la primera llamada falla
    registro = await registrar(repo, AlmacenFalso()).ejecutar(
        contenido(), True, False, [("a.png", PNG)], None
    )
    assert (registro.no_guardados, [a.n for a in registro.hoja.adjuntos]) == ([], [1])
    assert repo.confirmaciones == 2


async def test_sin_adjuntos_no_hay_que_cerrar_la_hoja() -> None:
    repo = HojasFalso()
    await registrar(repo, AlmacenFalso()).ejecutar(contenido(), True, False, [], None)
    assert not any(e.startswith("avisar") for e in repo.eventos)


async def test_si_falla_la_confirmacion_el_adjunto_tampoco_cuenta_como_guardado() -> None:
    repo = HojasFalso()
    repo.falla_confirmar_en = 1
    repo.fallas_confirmar = 2  # el reintento tambien falla
    registro = await registrar(repo, AlmacenFalso()).ejecutar(
        contenido(), True, False, [("a.png", PNG), ("b.png", PNG)], None
    )
    assert registro.no_guardados == [1]
    assert [a.n for a in registro.hoja.adjuntos] == [2]


async def test_transcribir_exige_ser_administrador() -> None:
    repo = HojasFalso(administrador=False)
    with pytest.raises(SinPermiso):
        await transcribir(repo, AlmacenFalso()).ejecutar(
            contenido(tipo=None), True, [], AHORA, "F-1"
        )
    assert "registrar" not in repo.eventos and "transcribir" not in repo.eventos


async def test_transcribir_registra_con_fecha_original_y_numero_fisico() -> None:
    repo = HojasFalso(administrador=True)
    registro = await transcribir(repo, AlmacenFalso()).ejecutar(
        contenido(tipo=None), True, [("a.png", PNG)], AHORA, "FIS-1"
    )
    assert repo.ultima_alta is not None
    nueva = repo.ultima_alta[1]
    assert (nueva.fecha_original, nueva.numero_hoja_fisica) == (AHORA, "FIS-1")
    resultado = registro.hoja
    assert (resultado.origen, resultado.numero, resultado.revisar_spam) == (
        "libro_fisico",
        "000000008-2026",
        False,
    )
    assert resultado.contenido.tipo is None
    assert [a.n for a in resultado.adjuntos] == [1]


@pytest.mark.parametrize(
    "fecha",
    [
        AHORA + timedelta(minutes=1),
        AHORA - timedelta(days=90, seconds=1),
        datetime(26, 3, 1, 10, 0, tzinfo=UTC),
    ],
)
async def test_transcribir_rechaza_una_fecha_futura_o_de_hace_mas_de_90_dias(
    fecha: datetime,
) -> None:
    repo = HojasFalso(administrador=True)
    with pytest.raises(FechaOriginalInvalida) as error:
        await transcribir(repo, AlmacenFalso()).ejecutar(
            contenido(tipo=None), True, [], fecha, "F-1"
        )
    assert error.value.detalles == {"campo": "fecha_original"}
    assert "transcribir" not in repo.eventos


async def test_transcribir_admite_la_fecha_de_hace_90_dias_y_la_de_ahora() -> None:
    for fecha in (AHORA - timedelta(days=90), AHORA):
        repo = HojasFalso(administrador=True)
        await transcribir(repo, AlmacenFalso()).ejecutar(
            contenido(tipo=None), True, [], fecha, "F-1"
        )
        assert "transcribir" in repo.eventos


async def test_obtener_oculta_al_cliente_la_marca_de_spam_y_al_autor() -> None:
    respondida = replace(
        hoja(revisar_spam=True),
        respuesta=Respuesta("Texto", "correo", None, AHORA, Autor(uuid4(), "Admin")),
    )
    for administrador, spam, autor in ((False, None, None), (True, True, "Admin")):
        repo = HojasFalso(administrador=administrador)
        repo.hojas[respondida.id] = respondida
        h = await ObtenerHoja(repo).ejecutar(respondida.id)
        assert h.respuesta is not None
        visto = h.respuesta.respondida_por
        assert (h.revisar_spam, visto and visto.nombre) == (spam, autor)


async def test_obtener_una_hoja_que_la_rls_oculta_es_no_encontrado() -> None:
    repo = HojasFalso()
    h = hoja()
    repo.hojas[h.id] = h
    repo.ocultas.add(h.id)
    with pytest.raises(NoEncontrado):
        await ObtenerHoja(repo).ejecutar(h.id)


async def test_mis_hojas_no_muestra_la_marca_de_spam() -> None:
    repo = HojasFalso()
    h = hoja(revisar_spam=True)
    repo.hojas[h.id] = h
    assert [r.revisar_spam for r in await ListarMisHojas(repo).ejecutar()] == [None]


async def test_la_bandeja_es_del_administrador_y_valida_el_rango() -> None:
    with pytest.raises(SinPermiso):
        await ListarHojas(HojasFalso()).ejecutar(None, None, None)
    repo = HojasFalso(administrador=True)
    with pytest.raises(RangoInvalido):
        await ListarHojas(repo).ejecutar(None, date(2026, 2, 1), date(2026, 1, 1))
    await ListarHojas(repo).ejecutar("pendiente", date(2026, 1, 1), date(2026, 2, 1))
    assert repo.consultas == [("pendiente", date(2026, 1, 1), date(2026, 2, 1))]


async def test_responder_exige_administrador_y_hoja_existente() -> None:
    with pytest.raises(SinPermiso):
        await ResponderHoja(HojasFalso()).ejecutar(uuid4(), "Respuesta larga", None, None)
    with pytest.raises(NoEncontrado):
        await ResponderHoja(HojasFalso(administrador=True)).ejecutar(
            uuid4(), "Respuesta larga", None, None
        )


async def test_responder_dos_veces_es_ya_respondida() -> None:
    repo = HojasFalso(administrador=True)
    h = hoja()
    repo.hojas[h.id] = h
    uc = ResponderHoja(repo)
    respondida = await uc.ejecutar(h.id, "Respuesta larga", None, None)
    assert respondida.estado == "respondida"
    with pytest.raises(YaRespondida):
        await uc.ejecutar(h.id, "Otra respuesta", None, None)
    assert repo.eventos == ["responder"]


async def test_con_carta_la_referencia_y_la_fecha_son_obligatorias() -> None:
    repo = HojasFalso(administrador=True)
    h = hoja(medio="carta")
    repo.hojas[h.id] = h
    uc = ResponderHoja(repo)
    for referencia, enviada in ((None, AHORA), ("C-1", None), ("  ", AHORA)):
        with pytest.raises(DatosInvalidos):
            await uc.ejecutar(h.id, "Respuesta larga", referencia, enviada)
    assert repo.eventos == []
    assert (await uc.ejecutar(h.id, "Respuesta larga", "C-1", AHORA)).respuesta is not None


async def test_url_de_adjunto_es_del_administrador_y_exige_que_exista() -> None:
    h = hoja(adjuntos=[adjunto(1)])
    with pytest.raises(SinPermiso):
        await UrlAdjunto(HojasFalso(), AlmacenFalso()).ejecutar(h.id, 1, AHORA)
    repo = HojasFalso(administrador=True)
    repo.hojas[h.id] = h
    uc = UrlAdjunto(repo, AlmacenFalso())
    with pytest.raises(NoEncontrado):
        await uc.ejecutar(h.id, 2, AHORA)
    url, expira = await uc.ejecutar(h.id, 1, AHORA)
    assert url == "http://firmada/x/1.png?s=300"
    assert (expira - AHORA).total_seconds() == 300


async def test_exportar_valida_el_rango_y_es_del_administrador() -> None:
    with pytest.raises(SinPermiso):
        await ExportarHojas(HojasFalso()).ejecutar(date(2026, 1, 1), date(2026, 2, 1))
    repo = HojasFalso(administrador=True)
    with pytest.raises(RangoInvalido):
        await ExportarHojas(repo).ejecutar(date(2026, 2, 1), date(2026, 1, 1))
    h = hoja()
    repo.hojas[h.id] = h
    texto = await ExportarHojas(repo).ejecutar(date(2026, 1, 1), date(2026, 2, 1))
    assert "000000001-2026" in texto


async def test_un_reintento_con_la_misma_clave_devuelve_la_hoja_sin_subir_nada() -> None:
    repo, almacen = HojasFalso(), AlmacenFalso()
    previa = hoja()
    repo.existente = previa
    repo.no_guardados_previos = [2]  # el primer envio perdio el adjunto 2
    clave = uuid4()
    registro = await registrar(repo, almacen).ejecutar(
        contenido(), True, False, [("a.png", PNG)], "1.2.3.4", clave
    )
    assert (registro.hoja, registro.creada, registro.no_guardados) == (previa, False, [2])
    assert almacen.subidos == [] and repo.confirmaciones == 0
    assert not any(e.startswith("avisar") for e in repo.eventos)
    assert repo.ultima_alta is not None and repo.ultima_alta[1].clave_envio == clave


async def test_la_limpieza_borra_de_storage_las_rutas_huerfanas_y_sigue_si_una_falla() -> None:
    repo, almacen = HojasFalso(), AlmacenFalso()
    repo.huerfanas = ["a/1.pdf", "b/2.pdf", "c/3.pdf"]
    almacen.falla_borrar = {"b/2.pdf"}
    assert await LimpiarAdjuntosHuerfanos(abridor(repo), almacen).ejecutar() == 2
    assert almacen.borrados == ["a/1.pdf", "c/3.pdf"]
