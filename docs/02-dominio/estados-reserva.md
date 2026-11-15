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
| Pre-reservada | Cancelada | El cliente o el Administrador la cancela; en v1 no caduca sola (D-06) |
| Confirmada | En curso | Inicio de la sesión |
| Confirmada | Cancelada | Cancelación; reembolso según D-11 |
| En curso | Finalizada | Fin de la sesión; se habilita la cuota `al_terminar` ([RN-13](reglas-negocio.md)) |

## Asesoría

```
Pendiente de pago ──(cuota validada)──► Confirmada ──► Realizada
        │                                   │
        └──────────► Cancelada ◄────────────┘
```

| Desde | Hacia | Condición |
|---|---|---|
| Pendiente de pago | Confirmada | El Administrador valida su cuota única ([RN-14](reglas-negocio.md)) |
| Pendiente de pago | Cancelada | El cliente o el Administrador la cancela; en v1 no caduca sola (D-06) |
| Confirmada | Realizada | El profesional la marca como dada |
| Confirmada | Cancelada | Cancelación; reembolso según D-11 |

## Comprobante de pago

```
Pendiente de validacion ──► Aprobado
            └─────────────► Rechazado (con motivo)
```

Al aprobarse, la cuota queda pagada. Un rechazo deja la cuota pendiente y el cliente puede subir otro comprobante ([RN-04](reglas-negocio.md)).

> **Pendiente de validar:** las transiciones de reserva salieron del informe y se ajustaron al flujo real (2026-11-15). Confirmar con el cliente antes de marcar este archivo como `aprobado`.
