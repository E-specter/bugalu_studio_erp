"""Avisos de RF-18 (CA-14): cancelacion con pagos, inasistencia, credito y devoluciones."""

from collections.abc import Callable
from decimal import Decimal
from typing import Any

from bugalu.modulos.notificaciones.dominio.formato import _fecha, _horario, _lima, _soles


def _detalle_cancelacion(datos: dict[str, Any]) -> str:
    credito = Decimal(str(datos["credito"]))
    vence = (
        f"El crédito vence el {_fecha(_lima(datos['credito_vence']))} (hora de Lima).\n"
        if credito > 0 and datos.get("credito_vence")
        else "No queda crédito a tu favor.\n"
    )
    return (
        f"Nivel de cancelación: nivel {datos['nivel']}\n"
        f"Pagado: {_soles(datos['pagado'])}\n"
        f"Retenido: {_soles(datos['retenido'])}\n"
        f"Crédito a tu favor: {_soles(datos['credito'])}\n{vence}"
    )


def _reserva_cancelada_con_pagos(datos: dict[str, Any]) -> tuple[str, str]:
    return (
        f"Cancelamos tu reserva {datos['folio']}",
        f"Tu reserva {datos['folio']} ({_horario(datos)}, hora de Lima) quedó cancelada.\n\n"
        + _detalle_cancelacion(datos),
    )


def _inasistencia_marcada(datos: dict[str, Any]) -> tuple[str, str]:
    return (
        f"Marcamos tu inasistencia en la reserva {datos['folio']}",
        f"Registramos que no asististe a tu reserva {datos['folio']} "
        f"({_horario(datos)}, hora de Lima).\n\n"
        f"Retenemos lo pagado ({_soles(datos['retenido'])}); no hay crédito ni cobro adicional.\n",
    )


def _credito_por_vencer(datos: dict[str, Any]) -> tuple[str, str]:
    return (
        "Tu crédito vence pronto",
        f"Tienes un crédito de {_soles(datos['saldo'])} (origen: reserva {datos['folio_origen']}) "
        f"que vence el {_fecha(_lima(datos['vence']))} (hora de Lima).\n\n"
        "Puedes usarlo al pagar una cuota de cualquiera de tus reservas.\n",
    )


def _devolucion_solicitada(datos: dict[str, Any]) -> tuple[str, str]:
    return (
        "Devolución por decidir",
        f"{datos['cliente'] or 'Un cliente'} pidió la devolución de un crédito "
        f"de {_soles(datos['saldo'])} (origen: reserva {datos['folio_origen']}).\n\n"
        f"Motivo: {datos['motivo']}\n",
    )


def _devolucion_decidida(datos: dict[str, Any]) -> tuple[str, str]:
    motivo = f"\nMotivo: {datos['motivo']}\n" if datos.get("motivo") else ""
    if datos["decision"] == "rechazo":
        resultado = "Rechazamos tu solicitud de devolución."
    elif datos["decision"] == "total":
        resultado = f"Se aprobó la devolución de {_soles(datos['monto_aprobado'])}."
    else:
        resultado = (
            f"Se aprobó una devolución parcial de {_soles(datos['monto_aprobado'])}; "
            "el resto sigue como crédito."
        )
    return (
        "Respuesta a tu solicitud de devolución",
        f"{resultado} (crédito de la reserva {datos['folio_origen']})\n{motivo}",
    )


def _devolucion_realizada(datos: dict[str, Any]) -> tuple[str, str]:
    return (
        "Te devolvimos el dinero",
        f"Realizamos la devolución de {_soles(datos['monto_aprobado'])} "
        f"(crédito de la reserva {datos['folio_origen']}).\n\n{datos['nota']}\n",
    )


def _costo_reprogramacion(datos: dict[str, Any]) -> str:
    if datos.get("sin_costo"):
        return "La reprogramación es sin costo: el precio no cambia.\n"
    credito = Decimal(str(datos["credito"]))
    return (
        f"Nivel de reprogramación: nivel {datos['nivel']}\n"
        f"Penalización: {_soles(datos['penalizacion'])}\n"
        f"Saldo por pagar: {_soles(datos['saldo'])}\n"
        + (f"Crédito a tu favor: {_soles(credito)}\n" if credito > 0 else "")
    )


def _reserva_reprogramada(datos: dict[str, Any]) -> tuple[str, str]:
    return (
        f"Reprogramamos tu reserva {datos['folio']}",
        f"Tu reserva {datos['folio']} pasó del {_fecha(_lima(datos['anterior_inicio']))} "
        f"a {_horario(datos)} (hora de Lima).\n\n{_costo_reprogramacion(datos)}",
    )


def _eleccion_estudio_resuelta(datos: dict[str, Any]) -> tuple[str, str]:
    if datos["opcion"] == "devolucion":
        eleccion = (
            f"eligió la devolución íntegra de {_soles(datos['monto'])}; "
            f"el plazo es hasta el {_fecha(_lima(datos['limite']))} (hora de Lima)."
        )
    else:
        eleccion = f"eligió reprogramar sin costo a {_horario(datos)} (hora de Lima)."
    return (
        f"Respuesta a la cancelación del estudio: reserva {datos['folio']}",
        f"{datos['cliente'] or 'El cliente'} {eleccion}\n",
    )


REDACTORES_RF18: dict[str, Callable[[dict[str, Any]], tuple[str, str]]] = {
    "reserva_cancelada_con_pagos": _reserva_cancelada_con_pagos,
    "inasistencia_marcada": _inasistencia_marcada,
    "credito_por_vencer": _credito_por_vencer,
    "devolucion_solicitada": _devolucion_solicitada,
    "devolucion_decidida": _devolucion_decidida,
    "devolucion_realizada": _devolucion_realizada,
    "reserva_reprogramada": _reserva_reprogramada,
    "eleccion_estudio_resuelta": _eleccion_estudio_resuelta,
}
