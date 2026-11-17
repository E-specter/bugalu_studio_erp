"""Armado del correo de un aviso: redaccion, plantilla de marca y evento de calendario."""

import re
from collections.abc import Sequence
from datetime import datetime

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
}
TIPOS_CON_EVENTO = frozenset(_METODO)


def _tiene_evento(p: Pendiente, reserva: DatosReserva | None) -> bool:
    if p.tipo not in _METODO:
        return False
    if p.tipo == "pago_aprobado":  # es la confirmacion misma
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
    )
    metodo = _METODO[p.tipo]
    ics = generar_ics(
        e, metodo, int(p.creada_en.timestamp()), ahora, remitente, p.destinatario, url
    )
    folio_seguro = re.sub(r"[^A-Za-z0-9._-]+", "_", e.folio)
    solicitud = metodo == "REQUEST"
    bloque = BloqueEvento(
        texto_evento(metodo, p.tipo == "reserva_reprogramada", folio_seguro),
        con_aviso=solicitud,
        url_google=enlace_google(e, url) if solicitud else None,
        url_outlook=enlace_outlook(e, url) if solicitud else None,
    )
    return Evento(metodo, f"bugalu-{folio_seguro}.ics", ics), bloque


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
