"""Redaccion pura de los correos: texto plano en espanol, hora de Lima, montos `S/ 1.234,50`."""

from collections.abc import Callable, Sequence
from decimal import Decimal
from typing import Any

from bugalu.modulos.notificaciones.dominio.formato import (
    _fecha,
    _horario,
    _lima,
    _soles,
    formatear_soles,
)
from bugalu.modulos.notificaciones.dominio.redaccion_rf18 import REDACTORES_RF18

Instrucciones = Sequence[tuple[str, str]]  # (metodo, texto) de los metodos activos
_HITOS = {"al_reservar": "al reservar", "al_terminar": "al terminar"}


def _datos_para_pagar(instrucciones: Instrucciones) -> str:
    if not instrucciones:
        return ""
    return "\nDatos para pagar:\n" + "".join(f"- {m.capitalize()}: {t}\n" for m, t in instrucciones)


def _reserva_creada(datos: dict[str, Any], instrucciones: Instrucciones = ()) -> tuple[str, str]:
    limite = _lima(datos["vence_pago"])
    return (
        f"Reserva {datos['folio']} registrada",
        "Tu reserva en Bugalú Studio quedó registrada.\n\n"
        f"Folio: {datos['folio']}\n"
        f"Servicio: {datos['servicio']}\n"
        f"Fecha y hora: {_horario(datos)} (hora de Lima)\n"
        f"Total: {formatear_soles(Decimal(str(datos['total'])))}\n\n"
        f"Fecha límite de pago: {_fecha(limite)}, {limite:%H:%M} (hora de Lima).\n"
        "Si no registras el pago antes de esa fecha, la reserva caducará y el horario "
        "se liberará.\n" + _datos_para_pagar(instrucciones),
    )


def _reserva_caducada(datos: dict[str, Any]) -> tuple[str, str]:
    return (
        f"Reserva {datos['folio']} caducada",
        f"Tu reserva {datos['folio']} caducó porque no se registró el pago a tiempo.\n\n"
        f"El horario ({_horario(datos)}, hora de Lima) se liberó. "
        "Puedes hacer una nueva reserva cuando quieras.\n",
    )


def _pago_registrado(datos: dict[str, Any]) -> tuple[str, str]:
    coincide = Decimal(str(datos["monto"])) == Decimal(str(datos["monto_cuota"]))
    verificacion = (
        "El monto coincide con la cuota."
        if coincide
        else f"El monto NO coincide con la cuota ({_soles(datos['monto_cuota'])})."
    )
    return (
        f"Pago por validar de la reserva {datos['folio']}",
        "Se registró un pago por validar.\n\n"
        f"Reserva: {datos['folio']}\n"
        f"Cliente: {datos['cliente'] or 'sin nombre'}\n"
        f"Cuota: {_HITOS[datos['hito']]}\n"
        f"Monto: {_soles(datos['monto'])}\n"
        f"Método: {datos['metodo']}\n"
        f"Número de operación: {datos['numero_operacion']}\n"
        f"{verificacion}\n",
    )


def _pago_aprobado(datos: dict[str, Any]) -> tuple[str, str]:
    confirmada = (
        "\nCon este pago, tu reserva está confirmada.\n" if datos.get("reserva_confirmada") else ""
    )
    return (
        f"Pago aprobado de la reserva {datos['folio']}",
        f"Aprobamos tu pago de {_soles(datos['monto'])} ({_HITOS[datos['hito']]}) "
        f"de la reserva {datos['folio']}.\n{confirmada}",
    )


def _pago_rechazado(datos: dict[str, Any]) -> tuple[str, str]:
    return (
        f"Pago rechazado de la reserva {datos['folio']}",
        f"No pudimos aprobar tu pago de {_soles(datos['monto'])} ({_HITOS[datos['hito']]}) "
        f"de la reserva {datos['folio']}.\n\nMotivo: {datos['motivo']}\n\n"
        "Puedes registrar otro pago desde el detalle de tu reserva.\n",
    )


def _reserva_finalizada_saldo(
    datos: dict[str, Any], instrucciones: Instrucciones = ()
) -> tuple[str, str]:
    return (
        f"Saldo pendiente de la reserva {datos['folio']}",
        f"Tu sesión de la reserva {datos['folio']} ({_horario(datos)}, hora de Lima) terminó.\n\n"
        f"Queda un saldo pendiente de {_soles(datos['saldo'])}. "
        "Puedes pagarlo y registrar tu pago desde el detalle de tu reserva.\n"
        + _datos_para_pagar(instrucciones),
    )


def _reserva_cancelada_estudio(datos: dict[str, Any]) -> tuple[str, str]:
    nota = f"\nNota del estudio: {datos['nota']}\n" if datos.get("nota") else ""
    return (
        f"Reserva {datos['folio']} cancelada por el estudio",
        f"El estudio canceló tu reserva {datos['folio']} "
        f"({_horario(datos)}, hora de Lima).\n{nota}\n"
        "Si tu reserva tenía pagos, entra a su detalle y elige: reprogramarla sin costo "
        "a un horario libre, o la devolución íntegra de lo pagado.\n",
    )


def _reserva_cancelada_cliente(datos: dict[str, Any]) -> tuple[str, str]:
    cliente = datos["cliente"] or "sin nombre"
    return (
        f"Reserva {datos['folio']} cancelada por el cliente",
        f"El cliente canceló la reserva {datos['folio']}.\n\n"
        f"Cliente: {cliente}\n"
        f"Fecha y hora: {_horario(datos)} (hora de Lima)\n"
        "El horario quedó libre.\n",
    )


_TEXTOS = {
    "terminos_uso": "Términos de uso",
    "politica_privacidad": "Política de privacidad",
    "condiciones_contratacion": "Condiciones de contratación",
    "declaracion_agrupacion": "Declaración de agrupación",
}


def _texto_legal_nuevo(datos: dict[str, Any]) -> tuple[str, str]:
    nombre = _TEXTOS.get(datos["tipo"], datos["tipo"])
    cambios = f"Qué cambia: {datos['resumen_cambios']}\n" if datos.get("resumen_cambios") else ""
    nueva_aceptacion = (
        "Tendrás que volver a aceptarlo en tu siguiente ingreso.\n"
        if datos["tipo_cambio"] == "mayor"
        else ""
    )
    return (
        f"Actualizamos: {nombre}",
        f"Publicamos la versión {datos['version']} de «{nombre}».\n\n"
        f"Rige desde el {_fecha(_lima(datos['vigente_desde']))} (hora de Lima).\n"
        f"{cambios}{nueva_aceptacion}"
        "Puedes leerla completa en la plataforma, en la sección de textos legales.\n",
    )


_REDACTORES: dict[str, Callable[[dict[str, Any]], tuple[str, str]]] = {
    "reserva_caducada": _reserva_caducada,
    "pago_registrado": _pago_registrado,
    "pago_aprobado": _pago_aprobado,
    "pago_rechazado": _pago_rechazado,
    "reserva_cancelada_estudio": _reserva_cancelada_estudio,
    "reserva_cancelada_cliente": _reserva_cancelada_cliente,
    "texto_legal_nuevo": _texto_legal_nuevo,
}


def redactar(
    tipo: str, datos: dict[str, Any], instrucciones: Instrucciones = ()
) -> tuple[str, str]:
    """Devuelve (asunto, cuerpo) del tipo de notificacion."""
    if tipo == "reserva_creada":
        return _reserva_creada(datos, instrucciones)
    if tipo == "reserva_finalizada_saldo":
        return _reserva_finalizada_saldo(datos, instrucciones)
    if tipo in REDACTORES_RF18:
        return REDACTORES_RF18[tipo](datos)
    if tipo not in _REDACTORES:
        raise ValueError(f"tipo de notificacion desconocido: {tipo}")
    return _REDACTORES[tipo](datos)
