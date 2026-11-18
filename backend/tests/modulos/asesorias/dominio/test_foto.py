import pytest

from bugalu.modulos.asesorias.dominio.foto import LIMITE_BYTES, detectar_tipo


@pytest.mark.parametrize(
    ("cabecera", "mime"),
    [
        (b"\xff\xd8\xff\xe0" + b"0" * 8, "image/jpeg"),
        (b"\x89PNG\r\n\x1a\n" + b"0" * 8, "image/png"),
        (b"RIFF\x10\x00\x00\x00WEBPVP8 ", "image/webp"),
    ],
)
def test_el_tipo_sale_de_los_bytes(cabecera: bytes, mime: str) -> None:
    tipo = detectar_tipo(cabecera)
    assert tipo is not None and tipo.mime == mime


@pytest.mark.parametrize(
    "cabecera",
    [b"%PDF-1.7 0000", b"GIF89a000000", b"RIFF\x10\x00\x00\x00WAVEfmt ", b"", b"<svg xmlns=...>"],
)
def test_otros_formatos_no_se_admiten(cabecera: bytes) -> None:
    assert detectar_tipo(cabecera) is None


def test_el_limite_es_de_2_mb() -> None:
    assert LIMITE_BYTES == 2 * 1024 * 1024
