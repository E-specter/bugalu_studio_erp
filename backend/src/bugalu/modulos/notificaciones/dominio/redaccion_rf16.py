"""Avisos del Libro de Reclamaciones (RF-16, docs/07-diseno/pantallas/RF-16-correos.md)."""

# ruff: noqa: E501 - SQL y textos literales largos

from collections.abc import Callable
from datetime import datetime
from decimal import Decimal
from typing import Any

from bugalu.modulos.notificaciones.dominio.formato import _lima, formatear_soles

_MESES = ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"]
_DOCUMENTO = {"dni": "DNI", "ce": "CE", "pasaporte": "Pasaporte"}
_MEDIO = {"correo": "Correo electrónico", "carta": "Carta al domicilio"}
_RECLAMO = "Reclamo"

_DEFINICIONES = (
    "RECLAMO: Disconformidad relacionada a los productos o servicios.\n"
    "QUEJA: Disconformidad no relacionada a los productos o servicios; o, malestar o descontento "
    "respecto a la atención al público."
)
_VIAS = (
    "La formulación del reclamo no impide acudir a otras vías de solución de controversias ni es "
    "requisito previo para interponer una denuncia ante el INDECOPI."
)
_PLAZO = (
    "El proveedor deberá dar respuesta al reclamo o queja en un plazo no mayor a quince (15) días "
    "hábiles improrrogables."
)


def _dia(f: datetime) -> str:
    return f"{f.day} {_MESES[f.month - 1]} {f.year}"


def _fecha(iso: str) -> str:
    return _dia(_lima(iso))


def _fecha_hora(iso: str) -> str:
    f = _lima(iso)
    return f"{_dia(f)}, {f:%H:%M}"


def _linea(valor: Any) -> str:
    """Un valor de una linea `Clave: valor`: los saltos del consumidor pasan a espacios."""
    return " ".join(str(valor).split())


def _opcional(valor: Any, vacio: str = "—") -> str:
    return _linea(valor) if valor not in (None, "") else vacio


def _tipo(datos: dict[str, Any]) -> str:
    return {"reclamo": "reclamo", "queja": "queja"}.get(datos.get("tipo") or "", "hoja")


def _etiqueta_tipo(datos: dict[str, Any]) -> str:
    return {"reclamo": "Reclamo", "queja": "Queja"}.get(datos.get("tipo") or "", "Sin marcar")


def _no_guardados_consumidor(n: int) -> str:
    return f"No pudimos guardar {n} de los adjuntos que enviaste.\n" if n else ""


def _no_guardados_admin(n: int) -> str:
    if not n:
        return ""
    return (
        "No se guardó 1 adjunto: pide al consumidor que lo reenvíe.\n"
        if n == 1
        else f"No se guardaron {n} adjuntos: pide al consumidor que los reenvíe.\n"
    )


def _registrada(d: dict[str, Any]) -> tuple[str, str]:
    medio = "correo electrónico" if d["medio_respuesta"] == "correo" else "carta a tu domicilio"
    monto = d.get("monto")
    adjuntos = ", ".join(_linea(a) for a in d["adjuntos"]) or "Ninguno"
    menor = ""
    if d["es_menor"] and d.get("representante"):
        r = d["representante"]
        menor = (
            "Madre, padre o tutor\n\n"
            f"Nombre: {_linea(r['nombre'])}\nDomicilio: {_linea(r['domicilio'])}\n"
            f"Teléfono: {_opcional(r.get('telefono'))}\nCorreo: {_linea(r['correo'])}\n\n"
        )
    cuerpo = (
        f"Registramos tu {_tipo(d)} en el Libro de Reclamaciones de Bugalú Studio. Esta es la "
        f"copia de tu hoja. Te responderemos por {medio} a más tardar el "
        f"{_fecha(d['vence_respuesta'])}.\n\n"
        f"Hoja N.º: {d['numero']}\n"
        f"Fecha y hora: {_fecha_hora(d['creada_en'])}\n"
        "Proveedor: Aural Perú E.I.R.L.\n"
        "RUC: 20615656128\n"
        "Domicilio del proveedor: Av. Javier Prado Este 5920, La Molina, Lima\n\n"
        "1. Identificación del consumidor reclamante\n\n"
        f"Nombre: {_linea(d['nombre'])}\n"
        f"Documento: {_DOCUMENTO[d['tipo_documento']]} {_linea(d['documento'])}\n"
        f"Domicilio: {_linea(d['domicilio'])}\n"
        f"Teléfono: {_opcional(d.get('telefono'))}\n"
        f"Correo: {_linea(d['correo'])}\n"
        f"Menor de edad: {'Sí' if d['es_menor'] else 'No'}\n\n"
        f"{menor}"
        "2. Identificación del bien contratado\n\n"
        f"Producto o servicio: {d['bien_tipo'].capitalize()}\n"
        f"Monto reclamado: {formatear_soles(Decimal(str(monto))) if monto is not None else 'No indicado'}\n"
        f"Descripción: {_opcional(d.get('descripcion'))}\n\n"
        "3. Detalle de la reclamación y pedido del consumidor\n\n"
        f"Tipo: {_etiqueta_tipo(d)}\n"
        f"Medio para la respuesta: {_MEDIO[d['medio_respuesta']]}\n"
        f"Adjuntos: {adjuntos}\n"
        f"{_no_guardados_consumidor(d.get('adjuntos_no_guardados', 0))}\n"
        f"Detalle:\n{d['detalle']}\n\n"
        f"Pedido:\n{d['pedido']}\n\n"
        f"{_DEFINICIONES}\n\n{_VIAS}\n{_PLAZO}\n"
    )
    return f"Hoja de reclamación N.º {d['numero']}", cuerpo


def _recibida(d: dict[str, Any]) -> tuple[str, str]:
    return (
        f"Nueva hoja de reclamación N.º {d['numero']}",
        "Llegó una hoja al Libro de Reclamaciones. Respóndela a más tardar el "
        f"{_fecha(d['vence_respuesta'])}: el plazo de 15 días hábiles no se prorroga.\n\n"
        f"Hoja N.º: {d['numero']}\n"
        f"Tipo: {_etiqueta_tipo(d)}\n"
        f"Consumidor: {_linea(d['nombre'])}\n"
        f"Presentada: {_fecha_hora(d['creada_en'])}\n"
        f"Medio para la respuesta: {_MEDIO[d['medio_respuesta']]}\n"
        f"Adjuntos: {d['adjuntos'] or 'Ninguno'}\n"
        f"{_no_guardados_admin(d.get('adjuntos_no_guardados', 0))}",
    )


def _respondida(d: dict[str, Any]) -> tuple[str, str]:
    return (
        f"Respuesta a tu hoja de reclamación N.º {d['numero']}",
        f"Respondimos tu {_tipo(d)} N.º {d['numero']}, presentado el {_fecha(d['creada_en'])}.\n\n"
        f"Nuestra respuesta:\n{d['texto']}\n\n"
        f"Hoja N.º: {d['numero']}\n"
        f"Fecha de la respuesta: {_fecha_hora(d['enviada_en'])}\n\n"
        f"{_VIAS}\n",
    )


def _por_vencer(d: dict[str, Any]) -> tuple[str, str]:
    hojas = d["hojas"]
    asunto = (
        "1 hoja de reclamación por responder"
        if len(hojas) == 1
        else f"{len(hojas)} hojas de reclamación por responder"
    )
    lineas = []
    for h in hojas:
        dias = h["dias"]
        if dias < 0:
            plazo = f"fuera de plazo desde el {_fecha(h['vence_respuesta'])}"
        elif dias == 0:
            plazo = "vence hoy"
        else:
            plazo = f"vence el {_fecha(h['vence_respuesta'])} (en {dias} días hábiles)"
        lineas.append(f"- N.º {h['numero']} · {_etiqueta_tipo(h)} · {plazo}\n")
    return (
        asunto,
        "Estas hojas vencen en 5 días hábiles o menos, o ya vencieron. Respóndelas en la "
        "plataforma.\n\n" + "".join(lineas),
    )


REDACTORES_RF16: dict[str, Callable[[dict[str, Any]], tuple[str, str]]] = {
    "reclamacion_registrada": _registrada,
    "reclamacion_recibida": _recibida,
    "reclamacion_respondida": _respondida,
    "reclamaciones_por_vencer": _por_vencer,
}
