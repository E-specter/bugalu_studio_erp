import pytest

from bugalu.compartido.errores import DatosInvalidos
from bugalu.modulos.pagos.dominio.instrucciones import MAX_CONTACTO, validar_contacto


def test_texto_demasiado_largo_dice_el_limite() -> None:
    with pytest.raises(DatosInvalidos) as e:
        validar_contacto("a" * (MAX_CONTACTO + 1))
    assert e.value.mensaje == f"El texto admite hasta {MAX_CONTACTO} caracteres."
    assert e.value.detalles == {"campo": "texto"}


@pytest.mark.parametrize("roto", ["\ud800", "a\x00b"])
def test_caracter_no_admitido_tiene_su_propio_mensaje(roto: str) -> None:
    with pytest.raises(DatosInvalidos) as e:
        validar_contacto(roto)
    assert e.value.mensaje == "El texto tiene un caracter no admitido."
    assert e.value.detalles == {"campo": "texto"}
