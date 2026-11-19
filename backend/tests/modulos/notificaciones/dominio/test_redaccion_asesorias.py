"""RF-15 B6 (CA-14): avisos de cancelacion y reprogramacion de una asesoria."""

from typing import Any

from bugalu.modulos.notificaciones.dominio.armado import TIPOS_CON_EVENTO
from bugalu.modulos.notificaciones.dominio.redaccion import redactar

BASE: dict[str, Any] = {
    "id_reserva": "x", "folio": "A-2027-00001", "inicio": "2027-03-10T15:00:00+00:00",
    "fin": "2027-03-10T15:30:00+00:00", "cliente": "Ana Torres", "profesional": "Pablo",
    "modalidad": "virtual", "lugar": None, "enlace": "https://meet.google.com/abc",
}  # fmt: skip


def test_cancelada_profesional_dice_quien_la_pidio_y_no_lleva_dinero() -> None:
    asunto, cuerpo = redactar("asesoria_cancelada_profesional", {**BASE, "por": "cliente"})
    assert asunto == "Asesoría A-2027-00001 cancelada"
    assert "Ana Torres" in cuerpo and "A pedido de: el cliente" in cuerpo
    assert "te avisaremos" not in cuerpo and "S/" not in cuerpo
    _, cuerpo = redactar("asesoria_cancelada_profesional", {**BASE, "por": "estudio"})
    assert "A pedido de: el estudio" in cuerpo and "Si Ana Torres elige reprogramar" in cuerpo


def test_reprogramada_profesional_muestra_antes_y_ahora_en_lima() -> None:
    datos = {**BASE, "anterior_inicio": "2027-03-09T15:00:00+00:00"}
    asunto, cuerpo = redactar("asesoria_reprogramada_profesional", datos)
    assert asunto == "Asesoría A-2027-00001 movida al miércoles 10 de marzo de 2027, 10:00"
    assert "Antes: martes 9 de marzo de 2027, 10:00" in cuerpo and "Enlace: https://meet" in cuerpo
    assert "S/" not in cuerpo


def test_los_avisos_de_reserva_hablan_de_asesoria_cuando_el_folio_es_de_asesoria() -> None:
    for tipo, extra in (
        ("reserva_cancelada_estudio", {"nota": "Sin sala"}),
        ("reserva_reprogramada", {"anterior_inicio": BASE["inicio"], "sin_costo": True}),
        (
            "reserva_cancelada_con_pagos",
            {"nivel": 1, "pagado": 50, "retenido": 0, "credito": 50, "credito_vence": None},
        ),
    ):
        asunto, cuerpo = redactar(tipo, {**BASE, **extra})
        texto = (asunto + cuerpo).lower()
        assert "asesoría" in texto and "reserva" not in texto
        assert "Profesional: Pablo" in cuerpo and "Enlace: https://meet" in cuerpo
    _, sala = redactar("reserva_cancelada_estudio", {**BASE, "folio": "R-2027-00001"})
    assert "tu reserva" in sala


def test_los_dos_avisos_nuevos_mueven_el_calendario() -> None:
    assert {"asesoria_cancelada_profesional", "asesoria_reprogramada_profesional"} <= (
        TIPOS_CON_EVENTO
    )
