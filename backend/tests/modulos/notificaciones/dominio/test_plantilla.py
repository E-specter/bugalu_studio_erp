"""Plantilla de marca (ADR-016): HTML con estilos en linea y su version de texto plano."""

# ruff: noqa: E501 - datos de ejemplo y textos literales de la spec

import re
from html.parser import HTMLParser

import pytest

from bugalu.modulos.notificaciones.dominio.plantilla import (
    AVISOS,
    BloqueEvento,
    bloques_del_cuerpo,
    componer,
)
from bugalu.modulos.notificaciones.dominio.redaccion import redactar
from bugalu.modulos.notificaciones.dominio.redaccion_rf15 import REDACTORES_RF15
from bugalu.modulos.notificaciones.dominio.redaccion_rf16 import REDACTORES_RF16
from bugalu.modulos.notificaciones.dominio.redaccion_rf18 import REDACTORES_RF18

URL = "https://erp.bugalu.pe"
EVENTO = BloqueEvento(
    "Adjuntamos el evento.", True, "https://g.example/a?b=1&c=2", "https://o.example"
)


def test_bloques_separa_parrafos_tabla_lista_y_une_lineas_con_br() -> None:
    cuerpo = (
        "Hola mundo.\n\nFolio: R-1\nServicio: Grabación\nTotal: S/ 10,00\n\n"
        "Motivo: uno solo\n\nDatos para pagar:\n- Yape: 999\n- Plin: 888\n\n"
        "Primera línea\nSegunda línea\n"
    )
    assert bloques_del_cuerpo(cuerpo) == [
        ("p", ["Hola mundo."]),
        ("tabla", [("Folio", "R-1"), ("Servicio", "Grabación"), ("Total", "S/ 10,00")]),
        ("p", ["Motivo: uno solo"]),
        ("p", ["Datos para pagar:"]),
        ("lista", ["Yape: 999", "Plin: 888"]),
        ("p", ["Primera línea", "Segunda línea"]),
    ]


def test_clave_en_minuscula_o_larga_no_es_tabla() -> None:
    assert bloques_del_cuerpo("abc: uno\ndef: dos") == [("p", ["abc: uno", "def: dos"])]
    larga = "A" * 41
    assert bloques_del_cuerpo(f"{larga}: x\nB: y")[0][0] == "p"


class Extractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.etiquetas: list[tuple[str, dict[str, str | None]]] = []
        self.texto: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.etiquetas.append((tag, dict(attrs)))

    def handle_data(self, data: str) -> None:
        self.texto.append(data)


def analizar(html: str) -> Extractor:
    p = Extractor()
    p.feed(html)
    return p


DATOS_CREADA = {"id_reserva": "abc-123", "folio": "R-1"}
CUERPO = "Tu reserva quedó registrada.\n\nFolio: R-1\nServicio: Grabación\n\n- Yape: 999\n"


def armar(tipo: str = "reserva_creada", cuerpo: str = CUERPO, evento: BloqueEvento | None = None):
    return componer(tipo, DATOS_CREADA, "Reserva R-1 registrada", cuerpo, URL, evento)


def test_html_trae_los_bloques_de_la_spec_en_orden() -> None:
    _, html = armar()
    assert html.startswith("<!doctype html>") and '<html lang="es">' in html
    orden = [
        "display:none",  # previsualizacion
        'src="cid:logo-bugalu"',  # cabecera
        "// RESERVA",  # etiqueta
        "<h1",  # titulo
        "Hola:",  # saludo
        '<th scope="row"',  # tabla de datos
        "<ul",  # lista
        f'href="{URL}/app/reservas/detalle?id=abc-123"',  # boton
        "Mis reservas",  # pie
        "Aural Perú E.I.R.L. · RUC 20615656128",
    ]
    posiciones = [html.index(x) for x in orden]
    assert posiciones == sorted(posiciones)
    assert "Ver mi reserva" in html and "<title>Reserva R-1 registrada</title>" in html
    assert 'role="article"' in html and 'aria-label="Reserva R-1 registrada"' in html
    assert len(html.encode()) < 100_000
    assert "http://" not in html.replace("http://www.w3.org", "")  # ninguna imagen remota
    img = [a for t, a in analizar(html).etiquetas if t == "img"]
    assert len(img) == 1 and img[0]["src"] == "cid:logo-bugalu" and img[0]["alt"] == "Bugalú Studio"


def test_el_contenido_del_aviso_se_escapa_y_un_script_no_llega_a_ser_etiqueta() -> None:
    malo = "<script>alert(1)</script>"
    cuerpo = f"Hola {malo}\n\nCliente: {malo}\nServicio: a&b\n"
    texto, html = componer("reserva_creada", {"id_reserva": "x"}, malo, cuerpo, URL, None)
    assert "<script" not in html and "&lt;script&gt;" in html and "a&amp;b" in html
    assert "script" not in [t for t, _ in analizar(html).etiquetas]
    assert malo in texto  # el texto plano va tal cual


def test_el_id_de_la_url_del_boton_se_codifica_y_escapa() -> None:
    _, html = componer("reserva_creada", {"id_reserva": 'a"><b>&'}, "A", "x", URL, None)
    assert "<b>" not in html and 'a"><b>' not in html
    assert "id=a%22%3E%3Cb%3E%26" in html


def test_texto_plano_conserva_el_cuerpo_y_la_informacion_del_html() -> None:
    texto, html = armar()
    assert texto.startswith("BUGALÚ STUDIO\n// RESERVA\n\nReserva R-1 registrada\n\nHola:\n\n")
    assert CUERPO.rstrip("\n") in texto
    assert f"Ver mi reserva: {URL}/app/reservas/detalle?id=abc-123" in texto
    assert "\n--\nBugalú Studio · Converge y crea.\n" in texto
    for dato in (
        f"{URL}/legal/terminos-de-uso/",
        f"{URL}/libro-de-reclamaciones/",
        "RUC 20615656128",
    ):
        assert dato in texto and dato in html
    assert "+51 925 530 800" in texto and "+51 925 530 800" in html
    assert "tienes una cuenta" in texto and "tienes una cuenta" in html


def test_variante_administracion_no_tiene_ayuda_ni_redes_y_enlaza_al_panel() -> None:
    texto, html = componer(
        "pago_registrado", {"id_pago": "p-1"}, "Pago", "Se registró.\n", URL + "/", None
    )
    for salida in (texto, html):
        assert "eres Administrador" in salida and f"{URL}/app" in salida
        assert "WhatsApp" not in salida and "Instagram" not in salida
        assert "tienes una cuenta" not in salida
    assert f"{URL}//" not in texto.replace("https://", "")  # barra final de la URL recortada
    assert f"{URL}/app/pagos/revisar?id=p-1" in html and "Panel de Bugalú" in html


def test_bloque_de_calendario_con_aviso_y_enlaces_en_html_y_texto() -> None:
    texto, html = armar(evento=EVENTO)
    assert "<h2" in html and "Evento de calendario" in html and "Adjuntamos el evento." in html
    assert "Mis reservas." in html and "Añadir a Google Calendar" in html
    assert 'href="https://g.example/a?b=1&amp;c=2"' in html  # atributo escapado
    assert "Añadir a Outlook" in html
    assert "EVENTO DE CALENDARIO\nAdjuntamos el evento.\n" in texto
    assert "Añadir a Google Calendar: https://g.example/a?b=1&c=2\n" in texto
    assert "Añadir a Outlook: https://o.example\n" in texto


def test_cancelacion_sin_aviso_ni_enlaces() -> None:
    cancel = BloqueEvento("Adjuntamos la cancelación.", False, None, None)
    texto, html = armar(evento=cancel)
    assert "Adjuntamos la cancelación." in html and "Añadir a" not in html
    assert "Añadir a" not in texto and "no se sincroniza" not in texto


def test_sin_evento_no_hay_bloque_de_calendario() -> None:
    texto, html = armar()
    assert "Evento de calendario" not in html and "EVENTO DE CALENDARIO" not in texto


def test_previsualizacion_corta_a_110_caracteres_por_palabra() -> None:
    _, html = armar(cuerpo=("palabra " * 40) + "\n")
    oculto = re.search(r"mso-hide:all;\">(.*?)</div>", html)
    assert oculto is not None
    previa = oculto.group(1)
    assert previa.endswith("…") and len(previa) <= 111 and not previa.endswith(" …")


def test_cada_tipo_redactable_tiene_fila_en_la_tabla_de_avisos() -> None:
    tipos = {
        "reserva_creada", "reserva_caducada", "pago_registrado", "pago_aprobado",
        "pago_rechazado", "reserva_finalizada_saldo", "reserva_cancelada_estudio",
        "reserva_cancelada_cliente", "texto_legal_nuevo", *REDACTORES_RF18, *REDACTORES_RF16, *REDACTORES_RF15,
    }  # fmt: skip
    assert tipos == set(AVISOS)
    with pytest.raises(ValueError):
        redactar("inventado", {})


@pytest.mark.parametrize(
    ("tipo", "datos", "ruta", "etiqueta"),
    [
        ("texto_legal_nuevo", {"tipo": "politica_privacidad"}, "/legal/privacidad/", "TEXTOS LEGALES"),
        ("texto_legal_nuevo", {"tipo": "terminos_uso"}, "/legal/terminos-de-uso/", "TEXTOS LEGALES"),
        ("credito_por_vencer", {}, "/app/reservas/creditos", "CRÉDITO"),
        ("devolucion_solicitada", {"id_devolucion": "d-1"}, "/app/pagos/devoluciones/revisar?id=d-1", "DEVOLUCIÓN"),
        ("reserva_caducada", {}, "/reservar/", "RESERVA"),
    ],
)  # fmt: skip
def test_destino_y_etiqueta_del_boton_por_tipo(
    tipo: str, datos: dict[str, str], ruta: str, etiqueta: str
) -> None:
    texto, html = componer(tipo, datos, "A", "x", URL, None)
    assert f"{URL}{ruta}" in texto and f"{URL}{ruta}" in html and f"// {etiqueta}" in texto
