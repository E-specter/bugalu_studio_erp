"""RF-15 B1: correos de asesoria con `.ics` (confirmacion y cambio de lugar o enlace)."""

from datetime import UTC, datetime
from uuid import uuid4

from bugalu.modulos.notificaciones.dominio.armado import TIPOS_CON_EVENTO, armar_correo
from bugalu.modulos.notificaciones.dominio.puertos import DatosReserva, Pendiente

URL = "https://erp.bugalu.pe"
AHORA = datetime(2027, 3, 1, 12, 0, tzinfo=UTC)
CREADA = datetime(2027, 3, 1, 11, 0, tzinfo=UTC)
ID = "0b6f6f3e-1c2d-4e5f-8a9b-0c1d2e3f4a5b"
BASE = {
    "id_reserva": ID, "folio": "A-2027-00001", "inicio": "2027-03-10T15:00:00+00:00",
    "fin": "2027-03-10T15:30:00+00:00", "cliente": "Ana Torres", "profesional": "Pablo",
}  # fmt: skip


def reserva(ubicacion: str | None, tiene_evento: bool = True) -> DatosReserva:
    return DatosReserva(
        datetime(2027, 3, 10, 15, 0, tzinfo=UTC),
        datetime(2027, 3, 10, 15, 30, tzinfo=UTC),
        "Asesoría artística con Pablo",
        "Videollamada",
        tiene_evento,
        ubicacion,
    )


def armar(tipo: str, datos: dict, r: DatosReserva | None):  # type: ignore[no-untyped-def,type-arg]
    p = Pendiente(uuid4(), tipo, "x@y.pe", datos, 0, CREADA)
    return armar_correo(p, (), r, URL, "no-responder@bugalu.pe", AHORA)


def test_los_dos_tipos_nuevos_mueven_el_calendario() -> None:
    assert {"asesoria_confirmada_profesional", "asesoria_encuentro_cambiado"} <= TIPOS_CON_EVENTO


def test_confirmacion_al_profesional_lleva_ics_con_el_enlace_y_remite_a_mis_asesorias() -> None:
    enlace = "https://meet.google.com/abc-defg-hij"
    c = armar(
        "asesoria_confirmada_profesional", {**BASE, "reserva_confirmada": True}, reserva(enlace)
    )
    assert c.evento is not None and c.evento.metodo == "REQUEST"
    ics = c.evento.ics.replace("\r\n ", "")
    assert f"LOCATION:{enlace}" in ics and f"UID:reserva-{ID}@bugalu" in ics and "SEQUENCE:" in ics
    assert "Mis asesorías" in ics and "Mis reservas" not in ics
    assert f"/app/asesorias/detalle?id={ID}" in c.cuerpo + c.html and "Ana Torres" in c.cuerpo


def test_cambio_de_encuentro_lleva_ics_si_ya_estaba_en_el_calendario_y_texto_si_no() -> None:
    datos = {**BASE, "modalidad": "presencial", "lugar": "Av. Lima 123", "enlace": None}
    c = armar("asesoria_encuentro_cambiado", datos, reserva("Av. Lima 123"))
    assert c.evento is not None and "LOCATION:Av. Lima 123" in c.evento.ics
    assert "Av. Lima 123" in c.cuerpo
    sin = armar("asesoria_encuentro_cambiado", datos, reserva("Av. Lima 123", tiene_evento=False))
    assert sin.evento is None and "Av. Lima 123" in sin.cuerpo


def test_sin_lugar_ni_enlace_dice_por_confirmar() -> None:
    datos = {**BASE, "modalidad": "virtual", "lugar": None, "enlace": None}
    c = armar("asesoria_encuentro_cambiado", datos, reserva("Por confirmar"))
    assert "Por confirmar" in c.cuerpo and c.evento is not None
    assert "LOCATION:Por confirmar" in c.evento.ics


def test_cancelacion_al_profesional_lleva_cancel_y_remite_a_su_agenda() -> None:
    datos = {**BASE, "por": "estudio", "modalidad": "virtual"}
    c = armar("asesoria_cancelada_profesional", datos, reserva("Por confirmar"))
    assert c.evento is not None and c.evento.metodo == "CANCEL"
    assert "METHOD:CANCEL" in c.evento.ics and f"UID:reserva-{ID}@bugalu" in c.evento.ics
    assert f"{URL}/app/asesorias/agenda" in c.cuerpo and "Ver mis asesorías" in c.cuerpo
    assert armar("asesoria_cancelada_profesional", datos, reserva(None, False)).evento is None


def test_reprogramacion_al_profesional_lleva_request_con_el_horario_nuevo() -> None:
    datos = {**BASE, "anterior_inicio": "2027-03-09T15:00:00+00:00", "modalidad": "virtual"}
    c = armar("asesoria_reprogramada_profesional", datos, reserva("Por confirmar"))
    assert c.evento is not None and c.evento.metodo == "REQUEST"
    assert f"/app/asesorias/detalle?id={ID}" in c.cuerpo
    assert "Adjuntamos el evento con el nuevo horario" in c.cuerpo


def test_pago_aprobado_de_una_asesoria_lleva_request_y_remite_a_su_detalle() -> None:
    datos = {**BASE, "monto": 118, "hito": "al_reservar", "reserva_confirmada": True}
    c = armar("pago_aprobado", datos, reserva("Por confirmar"))
    assert c.evento is not None and c.evento.metodo == "REQUEST"
    assert c.asunto == "Asesoría A-2027-00001 confirmada"
    assert f"Ver mi asesoría: {URL}/app/asesorias/detalle?id={ID}" in c.cuerpo
