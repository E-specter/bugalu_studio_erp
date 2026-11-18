from dataclasses import replace
from datetime import date
from uuid import uuid4

import pytest

from bugalu.compartido.errores import (
    AdjuntoNoPermitido,
    AlmacenamientoNoDisponible,
    ConfirmacionDeHojaRequerida,
    DatosInvalidos,
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
    adjunto,
    contenido,
    hoja,
)

PNG = b"\x89PNG\r\n\x1a\n" + b"x" * 10


async def test_registrar_sin_confirmar_no_toca_la_base() -> None:
    repo = HojasFalso()
    with pytest.raises(ConfirmacionDeHojaRequerida):
        await RegistrarHoja(repo, AlmacenFalso()).ejecutar(contenido(), False, False, [], "1.2.3.4")
    assert repo.eventos == []


async def test_registrar_un_adjunto_invalido_no_registra_nada() -> None:
    repo = HojasFalso()
    with pytest.raises(AdjuntoNoPermitido):
        await RegistrarHoja(repo, AlmacenFalso()).ejecutar(
            contenido(), True, False, [("a.png", b"no es nada")], None
        )
    assert repo.eventos == []


async def test_registrar_inserta_primero_y_sube_cada_adjunto_a_su_ruta() -> None:
    repo, almacen = HojasFalso(), AlmacenFalso()
    resultado, creada = await RegistrarHoja(repo, almacen).ejecutar(
        contenido(), True, True, [("a.png", PNG), ("b.png", PNG)], "1.2.3.4"
    )
    assert repo.ultima_alta is not None
    id_, nueva, ip = repo.ultima_alta
    assert ip == "1.2.3.4"
    assert nueva.revisar_spam is True
    assert almacen.subidos == [
        (f"{id_}/1.png", len(PNG), "image/png"),
        (f"{id_}/2.png", len(PNG), "image/png"),
    ]
    assert (resultado.id, resultado.numero, resultado.estado) == (
        id_,
        "000000007-2026",
        "pendiente",
    )
    assert creada is True
    assert [a.n for a in resultado.adjuntos] == [1, 2]
    assert resultado.origen == "web"
    assert resultado.revisar_spam is None  # el consumidor no ve la marca
    assert resultado.dias_habiles_restantes == 15


async def test_si_falla_la_subida_el_error_sale_para_que_la_transaccion_deshaga_la_hoja() -> None:
    with pytest.raises(AlmacenamientoNoDisponible):
        await RegistrarHoja(HojasFalso(), AlmacenFalso(falla_en=2)).ejecutar(
            contenido(), True, False, [("a.png", PNG), ("b.png", PNG)], None
        )


async def test_transcribir_exige_ser_administrador() -> None:
    repo = HojasFalso(administrador=False)
    with pytest.raises(SinPermiso):
        await TranscribirHoja(repo, AlmacenFalso()).ejecutar(
            contenido(tipo=None), True, [], AHORA, "F-1"
        )
    assert repo.eventos == []


async def test_transcribir_registra_con_fecha_original_y_numero_fisico() -> None:
    repo = HojasFalso(administrador=True)
    resultado = await TranscribirHoja(repo, AlmacenFalso()).ejecutar(
        contenido(tipo=None), True, [("a.png", PNG)], AHORA, "FIS-1"
    )
    assert repo.ultima_alta is not None
    nueva = repo.ultima_alta[1]
    assert (nueva.fecha_original, nueva.numero_hoja_fisica) == (AHORA, "FIS-1")
    assert (resultado.origen, resultado.numero, resultado.revisar_spam) == (
        "libro_fisico",
        "000000008-2026",
        False,
    )
    assert resultado.contenido.tipo is None


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
    clave = uuid4()
    resultado, creada = await RegistrarHoja(repo, almacen).ejecutar(
        contenido(), True, False, [("a.png", PNG)], "1.2.3.4", clave
    )
    assert (resultado, creada) == (previa, False)
    assert almacen.subidos == []
    assert repo.ultima_alta is not None and repo.ultima_alta[1].clave_envio == clave
