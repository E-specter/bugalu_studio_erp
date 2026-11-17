"""CA-14: el Markdown de un texto legal sale como HTML sin script, HTML crudo ni enlaces malos."""

import pytest

from bugalu.modulos.identidad.infraestructura.salida.markdown_a_html import markdown_a_html


def test_convierte_titulos_listas_y_enfasis() -> None:
    html = markdown_a_html("# Titulo\n\n- uno\n- **dos**\n")
    assert "<h1>Titulo</h1>" in html
    assert "<li>uno</li>" in html
    assert "<strong>dos</strong>" in html


@pytest.mark.parametrize(
    "entrada",
    [
        "<script>alert(1)</script>",
        "hola <script>alert(1)</script>",
        '<img src=x onerror="alert(1)">',
        "<iframe src='https://x'></iframe>",
        "<div onclick='x()'>texto</div>",
    ],
)
def test_el_html_crudo_sale_escapado(entrada: str) -> None:
    html = markdown_a_html(entrada)
    assert "<script" not in html
    assert "<img" not in html
    assert "<iframe" not in html
    assert "<div" not in html
    assert "&lt;" in html


@pytest.mark.parametrize(
    "destino",
    [
        "javascript:alert(1)",
        "JaVaScRiPt:alert(1)",
        "java&#x09;script:alert(1)",
        "vbscript:x",
        "data:text/html;base64,PHNjcmlwdD4=",
        "file:///etc/passwd",
        "mailto:a@b.pe",
        "//evil.example/x",
    ],
)
def test_un_enlace_que_no_es_http_ni_relativo_pierde_su_destino(destino: str) -> None:
    html = markdown_a_html(f"[clic]({destino})")
    assert "href" not in html
    assert "clic" in html


def test_un_enlace_a_una_imagen_peligrosa_pierde_su_origen() -> None:
    html = markdown_a_html("![alt](javascript:alert(1)) ![d](data:image/svg+xml;base64,AAAA)")
    assert "src" not in html


@pytest.mark.parametrize(
    "destino",
    ["https://bugalu.pe/x", "http://bugalu.pe", "/legal/terminos", "otra.md#parte", "#ancla"],
)
def test_los_enlaces_http_https_y_relativos_se_conservan(destino: str) -> None:
    assert f'href="{destino}"' in markdown_a_html(f"[clic]({destino})")
