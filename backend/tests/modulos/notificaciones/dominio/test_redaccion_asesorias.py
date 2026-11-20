"""RF-15 B6 y C1 (CA-13, CA-14): avisos de una asesoria, recordatorios y constancia."""

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


def test_reserva_caducada_de_una_asesoria_habla_de_asesoria() -> None:
    asunto, cuerpo = redactar("reserva_caducada", {**BASE})
    assert asunto == "Asesoría A-2027-00001 caducada"
    assert "asesoría A-2027-00001 caducó" in cuerpo and "reserva" not in (asunto + cuerpo).lower()
    asunto, _ = redactar("reserva_caducada", {**BASE, "folio": "R-2027-00001"})
    assert asunto == "Reserva R-2027-00001 caducada"


RECORDATORIO = {**BASE, "duracion": 30, "tolerancia": 15, "para": "cliente"}


def test_recordatorio_de_asesoria_al_cliente_con_enlace_y_tolerancia() -> None:
    asunto, cuerpo = redactar("recordatorio_asesoria", RECORDATORIO)
    assert asunto == "Recordatorio: asesoría del 10 mar a las 10:00"
    assert "asesoría con Pablo" in cuerpo and "Duración: 30 min" in cuerpo
    assert "Enlace: https://meet.google.com/abc" in cuerpo
    assert "Entra al enlace a la hora. Si no te conectas en los primeros 15 minutos" in cuerpo
    _, cuerpo = redactar("recordatorio_asesoria", {**RECORDATORIO, "modalidad": "presencial"})
    assert "Lugar: Por confirmar" in cuerpo and "Llega unos minutos antes" in cuerpo


def test_recordatorio_de_asesoria_al_profesional_sin_inasistencia_ni_dinero() -> None:
    datos = {**RECORDATORIO, "para": "profesional", "enlace": None}
    _, cuerpo = redactar("recordatorio_asesoria", datos)
    assert (
        "asesoría con Ana Torres" in cuerpo and "inasistencia" not in cuerpo and "S/" not in cuerpo
    )
    assert (
        "Enlace: Por confirmar" in cuerpo
        and "Aún falta registrar el enlace de Google Meet." in cuerpo
    )
    _, cuerpo = redactar("recordatorio_asesoria", {**datos, "modalidad": "presencial"})
    assert "Aún falta registrar el lugar." in cuerpo


def test_recordatorio_de_sala_con_y_sin_saldo() -> None:
    datos = {
        **BASE, "folio": "R-2027-00009", "servicio": "Ensayo", "sala": "Sala A", "tolerancia": 15,
    }  # fmt: skip
    asunto, cuerpo = redactar("recordatorio_reserva", datos)
    assert asunto == "Recordatorio: tu sesión del 10 mar a las 10:00"
    assert "Servicio: Ensayo" in cuerpo and "Sala: Sala A" in cuerpo and "15 minutos" in cuerpo
    assert "se paga al terminar" not in cuerpo
    _, cuerpo = redactar("recordatorio_reserva", {**datos, "saldo": 125})
    assert "El resto (S/ 125,00) se paga al terminar la sesión." in cuerpo


def test_la_constancia_va_por_correo_sin_adjunto_ni_notas() -> None:
    datos = {**BASE, "duracion": 30}
    asunto, cuerpo = redactar("asesoria_realizada", datos)
    assert asunto == "Tu constancia de asistencia · A-2027-00001"
    assert "Gracias por tu asesoría con Pablo" in cuerpo and "Duración: 30 min" in cuerpo
    assert "notas" not in cuerpo.lower()
    assert (
        "asesoria_realizada" not in TIPOS_CON_EVENTO
        and "recordatorio_asesoria" not in TIPOS_CON_EVENTO
    )
