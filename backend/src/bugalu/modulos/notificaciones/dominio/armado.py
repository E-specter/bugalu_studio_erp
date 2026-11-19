"""Armado del correo de un aviso: redaccion, plantilla de marca y evento de calendario."""

from collections.abc import Sequence
from datetime import UTC, datetime

from bugalu.modulos.notificaciones.dominio.calendario import (
    DatosEvento,
    enlace_google,
    enlace_outlook,
    generar_ics,
    texto_evento,
)
from bugalu.modulos.notificaciones.dominio.correo import Correo, Evento
from bugalu.modulos.notificaciones.dominio.plantilla import BloqueEvento, componer
from bugalu.modulos.notificaciones.dominio.puertos import DatosReserva, Pendiente
from bugalu.modulos.notificaciones.dominio.redaccion import redactar

# Avisos que mueven el calendario del cliente: metodo del .ics (ADR-016).
_METODO = {
    "pago_aprobado": "REQUEST",
    "reserva_reprogramada": "REQUEST",
    "reserva_cancelada_estudio": "CANCEL",
    "reserva_cancelada_con_pagos": "CANCEL",
    "asesoria_confirmada_profesional": "REQUEST",
    "asesoria_encuentro_cambiado": "REQUEST",
    "asesoria_cancelada_profesional": "CANCEL",
    "asesoria_reprogramada_profesional": "REQUEST",
}
_REPROGRAMACIONES = frozenset({"reserva_reprogramada", "asesoria_reprogramada_profesional"})
_CONFIRMACIONES = frozenset({"pago_aprobado", "asesoria_confirmada_profesional"})
TIPOS_CON_EVENTO = frozenset(_METODO)
# SEQUENCE: segundos desde esta epoca propia (en Unix pasaria de 32 bits en 2038).
EPOCA_SECUENCIA = datetime(2026, 1, 1, tzinfo=UTC)


def _tiene_evento(p: Pendiente, reserva: DatosReserva | None) -> bool:
    if p.tipo not in _METODO:
        return False
    if p.tipo in _CONFIRMACIONES:  # es la confirmacion misma
        return bool(p.datos.get("reserva_confirmada"))
    return reserva is not None and reserva.tiene_evento


def _evento(
    p: Pendiente, reserva: DatosReserva | None, url: str, remitente: str, ahora: datetime
) -> tuple[Evento, BloqueEvento]:
    if reserva is None:
        raise ValueError("faltan los datos de la reserva para el evento")
    if p.creada_en is None:
        raise ValueError("falta creada_en para el SEQUENCE del evento")
    datos = p.datos
    e = DatosEvento(
        id_reserva=str(datos["id_reserva"]),
        folio=str(datos["folio"]),
        # El horario del aviso (reprogramacion, cancelacion) manda sobre el actual de la reserva.
        inicio=datetime.fromisoformat(datos["inicio"]) if "inicio" in datos else reserva.inicio,
        fin=datetime.fromisoformat(datos["fin"]) if "fin" in datos else reserva.fin,
        servicio=reserva.servicio,
        sala=reserva.sala,
        ubicacion_texto=reserva.ubicacion,
    )
    metodo = _METODO[p.tipo]
    ics = generar_ics(
        e,
        metodo,
        int((p.creada_en - EPOCA_SECUENCIA).total_seconds()),
        ahora,
        remitente,
        p.destinatario,
        url,
    )
    solicitud = metodo == "REQUEST"
    bloque = BloqueEvento(
        texto_evento(
            metodo,
            p.tipo in _REPROGRAMACIONES,
            e.folio,
            p.tipo == "asesoria_encuentro_cambiado",
        ),
        con_aviso=solicitud,
        url_google=enlace_google(e, url) if solicitud else None,
        url_outlook=enlace_outlook(e, url) if solicitud else None,
    )
    return Evento(metodo, f"bugalu-{e.folio}.ics", ics), bloque


def armar_correo(
    p: Pendiente,
    instrucciones: Sequence[tuple[str, str]],
    reserva: DatosReserva | None,
    url_publica: str,
    remitente: str,
    ahora: datetime,
) -> Correo:
    asunto, cuerpo = redactar(p.tipo, p.datos, instrucciones)
    url = url_publica.rstrip("/")
    evento: Evento | None = None
    bloque: BloqueEvento | None = None
    if _tiene_evento(p, reserva):
        evento, bloque = _evento(p, reserva, url, remitente, ahora)
    texto, html = componer(p.tipo, p.datos, asunto, cuerpo, url, bloque)
    return Correo(p.destinatario, asunto, texto, html, evento)
