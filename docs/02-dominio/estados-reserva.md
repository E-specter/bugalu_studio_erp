---
id: estados-reserva
titulo: Estados de reserva, asesoría y pago
estado: borrador
depende_de: [RN-03, RN-04, D-06, D-11]
---

# Estados de reserva, asesoría y pago

Cada cambio de estado notifica por correo al cliente y al personal asignado ([RF-06](../03-requerimientos/RF-06.md)). Los saldos pendientes viven en las cuotas, no en el estado de la reserva.

## Reserva de sala (grabación o ensayo)

```
Pre-reservada ──(cuota al_reservar validada)──► Confirmada ──► En curso ──► Finalizada
      │                                             │
      └──────────────► Cancelada ◄──────────────────┘
```

| Desde | Hacia | Condición |
|---|---|---|
| Pre-reservada | Confirmada | El Administrador valida la cuota `al_reservar` ([RN-03](reglas-negocio.md)) |
| Pre-reservada | Cancelada | El cliente la cancela sin pagos (RN-20), el Administrador la cancela, o caduca sin pago registrado (RN-18) |
| Confirmada | En curso | Automático al llegar el inicio ([RN-23](reglas-negocio.md)) |
| Confirmada | Cancelada | Cancelación por el Administrador con nota del reembolso gestionado fuera del sistema (D-11, v1: [ADR-010](../00-proyecto/decisiones/ADR-010-pagos-estados-y-cancelacion.md)) |
| En curso | Finalizada | Automático al llegar el fin; si la cuota `al_terminar` sigue pendiente, se avisa del saldo ([RN-13](reglas-negocio.md), [RN-23](reglas-negocio.md)) |

## Asesoría

```
Pendiente de pago ──(cuota validada)──► Confirmada ──► Realizada
        │                                   │
        └──────────► Cancelada ◄────────────┘
```

| Desde | Hacia | Condición |
|---|---|---|
| Pendiente de pago | Confirmada | El Administrador valida su cuota única ([RN-14](reglas-negocio.md)) |
| Pendiente de pago | Cancelada | El Administrador la cancela; en v1 no caduca sola (D-06) |
| Confirmada | Realizada | El profesional la marca como dada |
| Confirmada | Cancelada | Cancelación; reembolso según D-11 |

## Comprobante de pago

```
Pendiente de validacion ──► Aprobado
            └─────────────► Rechazado (con motivo)
```

Al aprobarse, la cuota queda pagada y la aprobación no se deshace (v1). Un rechazo deja la cuota pendiente y el cliente puede subir otro comprobante; mientras un comprobante está pendiente, la cuota no admite otro ([RN-04](reglas-negocio.md)). Una `Pre-reservada` con comprobante pendiente no caduca ni avanza ([RN-18](reglas-negocio.md), [RN-23](reglas-negocio.md)).

> **Pendiente de validar:** las transiciones de reserva salieron del informe y se ajustaron al flujo real (2026-11-15). Confirmar con el cliente antes de marcar este archivo como `aprobado`.
