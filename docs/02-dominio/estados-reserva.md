---
id: estados-reserva
titulo: Estados de reserva
estado: borrador
depende_de: [RN-03, D-06, D-11]
---

# Estados de reserva

```
Pre-reservada ──(anticipo validado)──► Confirmada ──► En curso ──► Finalizada
      │                                    │
      └────────────► Cancelada ◄───────────┘
```

| Desde | Hacia | Condición |
|---|---|---|
| Pre-reservada | Confirmada | Anticipo del 50% validado ([RN-03](reglas-negocio.md)) |
| Pre-reservada | Cancelada | Cancelación o caducidad sin pago (D-06) |
| Confirmada | En curso | Inicio de la sesión |
| Confirmada | Cancelada | Cancelación; reembolso según D-11 |
| En curso | Finalizada | Fin de la sesión |

Cada cambio de estado notifica por correo al artista y al personal asignado ([RF-06](../03-requerimientos/RF-06.md)).

> **Pendiente de validar:** las transiciones se infirieron del informe. Confirmar con el cliente antes de marcar este archivo como `aprobado`.
