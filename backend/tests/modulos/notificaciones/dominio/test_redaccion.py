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


REGISTRADO = {
    "folio": "BG-0042",
    "cliente": "Ana Torres",
    "hito": "al_reservar",
    "monto": 25,
    "monto_cuota": 25.0,
    "metodo": "yape",
    "numero_operacion": "AB-1234",
}


def test_pago_registrado_lleva_folio_cliente_cuota_monto_metodo_y_operacion() -> None:
    asunto, cuerpo = redactar("pago_registrado", REGISTRADO)
    assert "BG-0042" in asunto
    for esperado in ("BG-0042", "Ana Torres", "al reservar", "S/ 25,00", "yape", "AB-1234"):
        assert esperado in cuerpo
    assert "coincide con la cuota" in cuerpo


def test_pago_registrado_avisa_cuando_el_monto_no_coincide() -> None:
    _, cuerpo = redactar("pago_registrado", {**REGISTRADO, "monto": 30})
    assert "NO coincide" in cuerpo and "S/ 30,00" in cuerpo and "S/ 25,00" in cuerpo


def test_pago_aprobado_confirma_la_reserva_solo_si_corresponde() -> None:
    datos = {"folio": "BG-0042", "hito": "al_reservar", "monto": 1250, "reserva_confirmada": True}
    asunto, cuerpo = redactar("pago_aprobado", datos)
    assert "BG-0042" in asunto and formatear_soles(Decimal(1250)) in cuerpo
    assert "tu reserva está confirmada" in cuerpo
    _, sin = redactar("pago_aprobado", {**datos, "reserva_confirmada": False})
    assert "confirmada" not in sin


def test_pago_rechazado_trae_el_motivo_y_que_puede_registrar_otro_pago() -> None:
    datos = {"folio": "BG-0042", "hito": "al_terminar", "monto": 25, "motivo": "Monto errado"}
    asunto, cuerpo = redactar("pago_rechazado", datos)
    assert "BG-0042" in asunto and "Monto errado" in cuerpo
    assert "otro pago" in cuerpo


def test_reserva_creada_agrega_los_datos_para_pagar_de_los_metodos_activos() -> None:
    _, cuerpo = redactar("reserva_creada", CREADA, [("yape", "Yape al 999 111 222")])
    assert "Datos para pagar" in cuerpo and "Yape al 999 111 222" in cuerpo
    _, sin = redactar("reserva_creada", CREADA, [])
    assert "Datos para pagar" not in sin


MIL_DOSCIENTOS = formatear_soles(Decimal(1250))  # separador de miles propio del formato
FINALIZADA = {
    "folio": "BG-0042",
    "inicio": CREADA["inicio"],
    "fin": CREADA["fin"],
    "saldo": 1250,
}


def test_reserva_finalizada_trae_el_saldo_y_los_datos_para_pagar_activos() -> None:
    asunto, cuerpo = redactar(
        "reserva_finalizada_saldo", FINALIZADA, [("yape", "Yape al 999 111 222")]
    )
    assert "BG-0042" in asunto and "saldo" in asunto.lower()
    for esperado in ("BG-0042", MIL_DOSCIENTOS, "10:00", "Datos para pagar", "Yape al 999 111 222"):
        assert esperado in cuerpo
    _, sin = redactar("reserva_finalizada_saldo", FINALIZADA, [])
    assert MIL_DOSCIENTOS in sin and "Datos para pagar" not in sin


def test_reserva_cancelada_por_el_estudio_lleva_la_nota_solo_si_existe() -> None:
    datos = {"folio": "BG-0042", "inicio": CREADA["inicio"], "fin": CREADA["fin"]}
    asunto, cuerpo = redactar(
        "reserva_cancelada_estudio", {**datos, "nota": "Reembolso de S/ 25 por yape"}
    )
    assert "BG-0042" in asunto and "cancel" in cuerpo.lower()
    assert "Reembolso de S/ 25 por yape" in cuerpo and "10:00" in cuerpo
    _, sin = redactar("reserva_cancelada_estudio", {**datos, "nota": None})
    assert "Nota" not in sin


def test_reserva_cancelada_por_el_cliente_avisa_a_administradores_con_folio_cliente_e_inicio() -> (
    None
):
    datos = {
        "folio": "BG-0042",
        "cliente": "Ana Torres",
        "inicio": CREADA["inicio"],
        "fin": CREADA["fin"],
    }
    asunto, cuerpo = redactar("reserva_cancelada_cliente", datos)
    assert "BG-0042" in asunto
    for esperado in ("BG-0042", "Ana Torres", "miércoles 10 de marzo de 2027", "10:00"):
        assert esperado in cuerpo
    _, anonimo = redactar("reserva_cancelada_cliente", {**datos, "cliente": None})
    assert "sin nombre" in anonimo
