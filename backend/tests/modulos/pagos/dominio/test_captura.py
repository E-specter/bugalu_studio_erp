import pytest

from bugalu.modulos.pagos.dominio.captura import detectar_tipo

PNG = b"\x89PNG\r\n\x1a\n" + b"\0" * 8
JPEG = b"\xff\xd8\xff\xe0" + b"\0" * 8
PDF = b"%PDF-1.7\n"


@pytest.mark.parametrize(
    ("cabecera", "mime", "extension", "clase"),
    [
        (JPEG, "image/jpeg", "jpg", "imagen"),
        (PNG, "image/png", "png", "imagen"),
        (PDF, "application/pdf", "pdf", "pdf"),
    ],
)
def test_detecta_el_tipo_por_la_firma(
    cabecera: bytes, mime: str, extension: str, clase: str
) -> None:
    tipo = detectar_tipo(cabecera)
    assert tipo is not None
    assert (tipo.mime, tipo.extension, tipo.clase) == (mime, extension, clase)


@pytest.mark.parametrize(
    "cabecera",
    [b"MZ\x90\x00", b"", b"\xff\xd8", b"\x89PNG\r\n\x1a", b"GIF89a", b"  %PDF-1.7", b"<html>"],
)
def test_lo_que_no_tiene_firma_valida_no_se_admite(cabecera: bytes) -> None:
    assert detectar_tipo(cabecera) is None
