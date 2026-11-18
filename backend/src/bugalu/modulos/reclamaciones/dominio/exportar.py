"""Exportacion CSV para Indecopi (CA-11): todas las columnas, con las celdas neutralizadas."""

import csv
import io
from collections.abc import Mapping, Sequence
from datetime import datetime, timedelta, timezone

from bugalu.modulos.reclamaciones.dominio.modelos import Hoja

COLUMNAS = (
    "numero", "creada_en", "origen", "fecha_original", "numero_hoja_fisica", "vence_respuesta",
    "estado", "tipo", "nombre", "tipo_documento", "documento", "domicilio", "telefono", "correo",
    "es_menor", "representante_nombre", "representante_domicilio", "representante_telefono",
    "representante_correo", "bien_tipo", "monto", "descripcion", "detalle", "pedido",
    "medio_respuesta", "adjuntos", "revisar_spam", "respuesta_texto", "respuesta_enviada_en",
    "respuesta_referencia_carta", "respondida_en", "respondida_por",
)  # fmt: skip
_PELIGROSAS = ("=", "+", "-", "@", "\t", "\r")


def neutralizar(celda: str) -> str:
    """Una celda que empieza por `= + - @` (o tabulador) la ejecutaria Excel como formula."""
    return "'" + celda if celda.startswith(_PELIGROSAS) else celda


def a_csv(filas: Sequence[Mapping[str, str]]) -> str:
    salida = io.StringIO()
    escritor = csv.writer(salida, lineterminator="\r\n")
    escritor.writerow(COLUMNAS)
    for fila in filas:
        escritor.writerow(neutralizar(fila[c]) for c in COLUMNAS)
    return "\ufeff" + salida.getvalue()  # BOM: Excel abre UTF-8 con tildes


_LIMA = timezone(timedelta(hours=-5))  # Lima no tiene horario de verano


def _f(valor: datetime | None) -> str:
    return valor.astimezone(_LIMA).isoformat() if valor else ""


def fila_csv(h: Hoja) -> dict[str, str]:
    c, r = h.contenido, h.respuesta
    rep = c.representante
    return {
        "numero": h.numero,
        "creada_en": _f(h.creada_en),
        "origen": h.origen,
        "fecha_original": _f(h.fecha_original),
        "numero_hoja_fisica": h.numero_hoja_fisica or "",
        "vence_respuesta": _f(h.vence_respuesta),
        "estado": h.estado,
        "tipo": c.tipo or "",
        "nombre": c.consumidor.nombre,
        "tipo_documento": c.consumidor.tipo_documento,
        "documento": c.consumidor.documento,
        "domicilio": c.consumidor.domicilio,
        "telefono": c.consumidor.telefono or "",
        "correo": c.consumidor.correo,
        "es_menor": "si" if c.es_menor else "no",
        "representante_nombre": rep.nombre if rep else "",
        "representante_domicilio": rep.domicilio if rep else "",
        "representante_telefono": (rep.telefono or "") if rep else "",
        "representante_correo": rep.correo if rep else "",
        "bien_tipo": c.bien.tipo,
        "monto": str(c.bien.monto) if c.bien.monto is not None else "",
        "descripcion": c.bien.descripcion or "",
        "detalle": c.detalle,
        "pedido": c.pedido,
        "medio_respuesta": c.medio_respuesta,
        "adjuntos": str(len(h.adjuntos)),
        "revisar_spam": "si" if h.revisar_spam else "no",
        "respuesta_texto": r.texto if r else "",
        "respuesta_enviada_en": _f(r.enviada_en) if r else "",
        "respuesta_referencia_carta": (r.referencia_carta or "") if r else "",
        "respondida_en": _f(r.respondida_en) if r else "",
        "respondida_por": (r.respondida_por.nombre or str(r.respondida_por.id))
        if r and r.respondida_por
        else "",
    }
