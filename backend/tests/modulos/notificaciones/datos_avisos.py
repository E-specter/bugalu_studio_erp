"""Un ejemplo de datos por cada tipo de aviso (los que encola la base)."""

# ruff: noqa: E501 - datos de ejemplo y textos literales de la spec

from typing import Any

_R = {
    "id_reserva": "11111111-2222-3333-4444-555555555555",
    "folio": "R-2027-00042",
    "inicio": "2027-03-10T15:00:00+00:00",  # 10:00 en Lima
    "fin": "2027-03-10T17:00:00+00:00",
}

DATOS_AVISOS: dict[str, dict[str, Any]] = {
    "reserva_creada": {
        **_R, "servicio": "Grabación de voces", "total": 250, "vence_pago": "2027-03-08T20:30:00+00:00",
    },
    "reserva_caducada": dict(_R),
    "pago_registrado": {
        **_R, "id_pago": "pp-1", "cliente": "Ana Torres", "hito": "al_reservar", "monto": 25,
        "monto_cuota": 25, "metodo": "yape", "numero_operacion": "AB-1234",
    },
    "pago_aprobado": {**_R, "hito": "al_reservar", "monto": 125, "reserva_confirmada": True},
    "pago_rechazado": {**_R, "hito": "al_terminar", "monto": 25, "motivo": "Monto errado"},
    "reserva_finalizada_saldo": {**_R, "saldo": 125},
    "reserva_cancelada_estudio": {**_R, "nota": "Falla eléctrica"},
    "reserva_cancelada_cliente": {**_R, "cliente": "Ana Torres"},
    "reserva_cancelada_con_pagos": {
        **_R, "nivel": 2, "pagado": 100, "retenido": 50, "credito": 50,
        "credito_vence": "2027-04-10T04:59:59+00:00",
    },
    "reserva_reprogramada": {
        **_R, "anterior_inicio": "2027-03-01T15:00:00+00:00", "nivel": 2, "penalizacion": 50,
        "saldo": 190, "credito": 0, "sin_costo": False,
    },
    "inasistencia_marcada": {**_R, "retenido": 100},
    "eleccion_estudio_resuelta": {
        **_R, "cliente": "Ana Torres", "opcion": "devolucion", "monto": 100,
        "limite": "2027-03-17T04:59:59+00:00",
    },
    "credito_por_vencer": {"saldo": 60, "vence": "2027-04-10T04:59:59+00:00", "folio_origen": "R-1"},
    "devolucion_solicitada": {
        "id_devolucion": "dd-1", "cliente": "Ana Torres", "saldo": 100, "motivo": "Cambié de planes",
        "folio_origen": "R-1",
    },
    "devolucion_decidida": {
        "decision": "parcial", "monto_aprobado": 30, "motivo": "Política", "folio_origen": "R-1",
    },
    "devolucion_realizada": {"monto_aprobado": 30, "nota": "Yape, operación 998877", "folio_origen": "R-1"},
    "texto_legal_nuevo": {
        "tipo": "terminos_uso", "tipo_cambio": "mayor", "version": 3,
        "vigente_desde": "2027-03-10T15:00:00+00:00", "resumen_cambios": "Nuevos plazos <b>.",
    },
}  # fmt: skip
