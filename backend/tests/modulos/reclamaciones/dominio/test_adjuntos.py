import pytest

from bugalu.compartido.errores import AdjuntoMuyGrande, AdjuntoNoPermitido, DemasiadosAdjuntos
from bugalu.modulos.reclamaciones.dominio.adjuntos import LIMITE_BYTES, validar_adjuntos

PNG = b"\x89PNG\r\n\x1a\n" + b"x" * 20
JPG = b"\xff\xd8\xff\xe0" + b"x" * 20
PDF = b"%PDF-1.7\n" + b"x" * 20


def test_el_tipo_sale_del_contenido_y_no_del_nombre() -> None:
    adjuntos = validar_adjuntos([("foto.pdf", PNG), ("a.png", JPG), ("b.jpg", PDF)])
    assert [(a.n, a.tipo, a.tamano) for a in adjuntos] == [
        (1, "image/png", len(PNG)),
        (2, "image/jpeg", len(JPG)),
        (3, "application/pdf", len(PDF)),
    ]
    assert adjuntos[0].contenido == PNG


def test_sin_adjuntos_es_una_lista_vacia() -> None:
    assert validar_adjuntos([]) == []


def test_mas_de_tres_es_demasiados_adjuntos() -> None:
    with pytest.raises(DemasiadosAdjuntos):
        validar_adjuntos([("a.png", PNG)] * 4)


@pytest.mark.parametrize("contenido", [b"MZ\x90\x00 programa", b"", b"GIF89a....", b"<html>"])
def test_un_contenido_que_no_es_pdf_jpg_ni_png_se_rechaza_con_su_posicion(
    contenido: bytes,
) -> None:
    with pytest.raises(AdjuntoNoPermitido) as e:
        validar_adjuntos([("a.png", PNG), ("b.png", contenido)])
    assert e.value.detalles == {"adjunto": 2}


def test_mas_de_5_mb_es_adjunto_muy_grande_con_su_posicion() -> None:
    with pytest.raises(AdjuntoMuyGrande) as e:
        validar_adjuntos([("a.pdf", PDF + b"0" * LIMITE_BYTES)])
    assert (e.value.estado_http, e.value.detalles) == (413, {"adjunto": 1})


def test_justo_5_mb_se_admite() -> None:
    assert validar_adjuntos([("a.pdf", PDF + b"0" * (LIMITE_BYTES - len(PDF)))])[0].tamano == (
        LIMITE_BYTES
    )


@pytest.mark.parametrize(
    ("nombre", "esperado"),
    [
        ("C:\fotos\ruta/mi foto.png", "mi foto.png"),
        ("../../etc/pas\x00swd.png", "passwd.png"),
        ("   ", "adjunto-1.png"),
        ("a" * 300 + ".png", "a" * 200),
    ],
)
def test_el_nombre_se_limpia_de_rutas_y_controles(nombre: str, esperado: str) -> None:
    assert validar_adjuntos([(nombre, PNG)])[0].nombre == esperado
