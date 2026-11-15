---
id: reglas-negocio
titulo: Reglas de negocio
estado: borrador
depende_de: []
---

# Reglas de negocio

| ID | Regla |
|---|---|
| RN-01 | Dos reservas de la misma sala no pueden solaparse. |
| RN-02 | Toda reserva genera un buffer técnico automático de 30 min posterior a su fin (desinfección y calibración). El buffer bloquea la sala. |
| RN-03 | Una reserva pasa a `Confirmada` solo tras validar el anticipo del 50%. |
| RN-04 | El anticipo se paga por pasarela digital o mediante comprobante bancario validado por el Administrador. |
| RN-05 | La liquidación (50% restante) se habilita tras la aprobación de la versión de mezcla o máster por el cliente. |
| RN-06 | La descarga del máster se habilita solo tras la liquidación. |
| RN-07 | El enlace de descarga es cifrado, autenticado y caduca a los 7 días calendario. |
| RN-08 | Nomenclatura de entregables incremental y automática: `PRJ<nn>_<Track>_v<mayor>.<menor>.wav` (ej. `PRJ01_Track_v1.0.wav`). |
| RN-09 | Solo se aceptan entregables WAV sin pérdida. |
| RN-10 | Cada proyecto tiene un límite de rondas de corrección pactadas; cada observación consume del saldo según la ronda vigente. |
| RN-11 | El personal técnico se asigna según la especialidad del proyecto, solo a sesiones `Confirmada`. |

Abiertas que afectan reglas: D-05 (límite por defecto de rondas), D-06 (caducidad de `Pre-reservada`), D-11 (cancelación y reembolso). Ver [decisiones](../00-proyecto/decisiones/README.md).
