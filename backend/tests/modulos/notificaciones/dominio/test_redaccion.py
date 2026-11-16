"""Redaccion de los correos: texto plano en espanol, hora de Lima, montos S/ 1 234,50."""

from decimal import Decimal

import pytest

from bugalu.modulos.notificaciones.dominio.correo import Correo
from bugalu.modulos.notificaciones.dominio.redaccion import formatear_soles, redactar

CREADA = {
    "folio": "BG-0042",
    "servicio": "Grabación de voces",
    "inicio": "2027-03-10T15:00:00+00:00",  # 10:00 en Lima
    "fin": "2027-03-10T17:00:00+00:00",
    "total": 1234.5,
    "vence_pago": "2027-03-08T20:30:00+00:00",  # 15:30 en Lima
}


@pytest.mark.parametrize(
    ("monto", "texto"),
    [
        (Decimal("1234.5"), "S/ 1 234,50"),
        (Decimal("50"), "S/ 50,00"),
        (Decimal("1234567.891"), "S/ 1 234 567,89"),
    ],
)
def test_formatea_soles_como_el_frontend(monto: Decimal, texto: str) -> None:
    assert formatear_soles(monto) == texto


def test_reserva_creada_lleva_folio_servicio_horario_total_y_fecha_limite() -> None:
    asunto, cuerpo = redactar("reserva_creada", CREADA)
    assert "BG-0042" in asunto
    for esperado in (
        "BG-0042",
        "Grabación de voces",
        "miércoles 10 de marzo de 2027",
        "10:00",
        "12:00",
        "S/ 1 234,50",
        "lunes 8 de marzo de 2027, 15:30",
    ):
        assert esperado in cuerpo
    assert "caducará" in cuerpo


def test_reserva_caducada_lleva_folio_y_avisa_que_el_horario_se_libero() -> None:
    asunto, cuerpo = redactar(
        "reserva_caducada",
        {"folio": "BG-0042", "inicio": CREADA["inicio"], "fin": CREADA["fin"]},
    )
    assert "BG-0042" in asunto
    assert "BG-0042" in cuerpo
    assert "liberó" in cuerpo
    assert "10:00" in cuerpo


def test_tipo_desconocido_falla() -> None:
    with pytest.raises(ValueError, match="tipo"):
        redactar("otro", {})


@pytest.mark.parametrize("campo", ["destinatario", "asunto"])
def test_correo_rechaza_saltos_de_linea_en_cabeceras(campo: str) -> None:
    valores = {"destinatario": "a@b.pe", "asunto": "Hola", "cuerpo": "texto"}
    valores[campo] = "x\r\nBcc: otro@b.pe"
    with pytest.raises(ValueError, match="salto de linea"):
        Correo(**valores)
