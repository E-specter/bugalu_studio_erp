"""Avisos de RF-15 etapa B: confirmación al profesional y cambio de lugar o enlace."""

from collections.abc import Callable
from typing import Any

from bugalu.modulos.notificaciones.dominio.formato import _horario


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


REDACTORES_RF15: dict[str, Callable[[dict[str, Any]], tuple[str, str]]] = {
    "asesoria_confirmada_profesional": _asesoria_confirmada_profesional,
    "asesoria_encuentro_cambiado": _asesoria_encuentro_cambiado,
}
