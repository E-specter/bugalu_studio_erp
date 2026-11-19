"""Avisos de RF-15 etapa B: confirmación, cambio de lugar o enlace, cancelación y reprogramación."""

from collections.abc import Callable
from typing import Any

from bugalu.modulos.notificaciones.dominio.formato import _fecha, _horario, _lima
from bugalu.modulos.notificaciones.dominio.redaccion_rf18 import (
    _costo_reprogramacion,
    _detalle_cancelacion,
)


def _encuentro(datos: dict[str, Any]) -> str:
    if datos.get("modalidad") == "virtual":
        return f"Enlace: {datos.get('enlace') or 'Por confirmar'}\n"
    return f"Lugar: {datos.get('lugar') or 'Por confirmar'}\n"


def _modalidad(datos: dict[str, Any]) -> str:
    return "Virtual" if datos.get("modalidad") == "virtual" else "Presencial"


def _asesoria_confirmada_profesional(datos: dict[str, Any]) -> tuple[str, str]:
    return (
        f"Asesoría {datos['folio']} confirmada",
        "Se confirmó el pago de una asesoría contigo.\n\n"
        f"Folio: {datos['folio']}\n"
        f"Cliente: {datos.get('cliente') or 'sin nombre'}\n"
        f"Fecha y hora: {_horario(datos)} (hora de Lima)\n"
        f"Modalidad: {_modalidad(datos)}\n" + _encuentro(datos),
    )


def _asesoria_encuentro_cambiado(datos: dict[str, Any]) -> tuple[str, str]:
    return (
        f"Cambió el lugar o enlace de la asesoría {datos['folio']}",
        "Actualizamos el lugar o el enlace de la asesoría.\n\n"
        f"Folio: {datos['folio']}\n"
        f"Profesional: {datos.get('profesional') or 'sin nombre'}\n"
        f"Cliente: {datos.get('cliente') or 'sin nombre'}\n"
        f"Fecha y hora: {_horario(datos)} (hora de Lima)\n"
        f"Modalidad: {_modalidad(datos)}\n" + _encuentro(datos),
    )


def _cuando(iso: str) -> str:
    f = _lima(iso)
    return f"{_fecha(f)}, {f:%H:%M}"


def _tabla(datos: dict[str, Any]) -> str:
    return (
        f"Folio: {datos['folio']}\n"
        f"Profesional: {datos.get('profesional') or 'sin nombre'}\n"
        f"Modalidad: {_modalidad(datos)}\n" + _encuentro(datos)
    )


def _asesoria_cancelada_profesional(datos: dict[str, Any]) -> tuple[str, str]:
    cliente = datos.get("cliente") or "El cliente"
    estudio = datos.get("por") == "estudio"
    return (
        f"Asesoría {datos['folio']} cancelada",
        f"Se canceló tu asesoría con {cliente}. El horario quedó libre en tu agenda.\n\n"
        f"Folio: {datos['folio']}\nFecha y hora: {_horario(datos)} (hora de Lima)\n\n"
        f"A pedido de: {'el estudio' if estudio else 'el cliente'}\n"
        + (f"\nSi {cliente} elige reprogramar contigo, te avisaremos.\n" if estudio else ""),
    )


def _asesoria_reprogramada_profesional(datos: dict[str, Any]) -> tuple[str, str]:
    ahora = _cuando(datos["inicio"])
    return (
        f"Asesoría {datos['folio']} movida al {ahora}",
        f"{datos.get('cliente') or 'El cliente'} movió su asesoría contigo.\n\n"
        f"Folio: {datos['folio']}\nAntes: {_cuando(datos['anterior_inicio'])}\nAhora: {ahora}\n"
        f"Modalidad: {_modalidad(datos)}\n" + _encuentro(datos),
    )


# Avisos de reserva ya existentes, con texto de asesoría (folio `A-`): sin tipos duplicados.
def _cancelada_estudio(datos: dict[str, Any]) -> tuple[str, str]:
    nota = f"\nNota del estudio: {datos['nota']}\n" if datos.get("nota") else ""
    return (
        f"Asesoría {datos['folio']} cancelada por el estudio",
        f"El estudio canceló tu asesoría con {datos.get('profesional') or 'tu profesional'} "
        f"({_horario(datos)}, hora de Lima).\n{nota}\n"
        "Si tu asesoría tenía pagos, entra a Mis asesorías y elige: reprogramarla sin costo con "
        "el mismo profesional, o la devolución íntegra de lo pagado.\n\n" + _tabla(datos),
    )


def _cancelada_con_pagos(datos: dict[str, Any]) -> tuple[str, str]:
    return (
        f"Cancelamos tu asesoría {datos['folio']}",
        f"Tu asesoría con {datos.get('profesional') or 'tu profesional'} "
        f"({_horario(datos)}, hora de Lima) quedó cancelada.\n\n"
        + _detalle_cancelacion(datos)
        + "\n"
        + _tabla(datos),
    )


def _reprogramada(datos: dict[str, Any]) -> tuple[str, str]:
    return (
        f"Asesoría {datos['folio']}: nuevo horario",
        f"Tu asesoría con {datos.get('profesional') or 'tu profesional'} pasó del "
        f"{_fecha(_lima(datos['anterior_inicio']))} a {_horario(datos)} (hora de Lima).\n\n"
        + _costo_reprogramacion(datos)
        + "\n"
        + _tabla(datos),
    )


ASESORIA_DE_RESERVA: dict[str, Callable[[dict[str, Any]], tuple[str, str]]] = {
    "reserva_cancelada_estudio": _cancelada_estudio,
    "reserva_cancelada_con_pagos": _cancelada_con_pagos,
    "reserva_reprogramada": _reprogramada,
}

REDACTORES_RF15: dict[str, Callable[[dict[str, Any]], tuple[str, str]]] = {
    "asesoria_confirmada_profesional": _asesoria_confirmada_profesional,
    "asesoria_encuentro_cambiado": _asesoria_encuentro_cambiado,
    "asesoria_cancelada_profesional": _asesoria_cancelada_profesional,
    "asesoria_reprogramada_profesional": _asesoria_reprogramada_profesional,
}
