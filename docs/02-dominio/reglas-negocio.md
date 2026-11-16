---
id: reglas-negocio
titulo: Reglas de negocio
estado: borrador
depende_de: [ADR-004]
---

# Reglas de negocio

Moneda: soles (PEN). Las reglas de reservas, asesorías y pagos salen del flujo real del estudio ([spec 2026-11-15](../superpowers/specs/2026-11-15-contratacion-y-decisiones-design.md)).

## Disponibilidad y reservas

| ID | Regla |
|---|---|
| RN-01 | Dos reservas de la misma sala no pueden solaparse, incluido su buffer. |
| RN-02 | Toda reserva de sala genera un buffer técnico automático de 30 min posterior a su fin (desinfección y calibración). El buffer bloquea la sala. No aplica a asesorías. |
| RN-12 | El Administrador publica a mano las franjas de disponibilidad por sala (el sistema sugiere una plantilla editable) y registra excepciones: cerrar un día u horas, o abrir horas extra. El cliente reserva un tramo dentro de una franja para un servicio, en múltiplos de 30 min, de 30 min a 8 horas; el resto de la franja sigue disponible. El tramo más su buffer debe caber en la franja ([ADR-009](../00-proyecto/decisiones/ADR-009-reservas-tarifas-y-caducidad.md)). |
| RN-13 | Una reserva de sala es para un servicio que ocupa sala: grabación (voces, instrumentos, banda en vivo), ensayo o live session. Sin cotización, genera dos cuotas: 50% `al_reservar` y 50% `al_terminar` la sesión. El ensayo solo lo reserva un cliente con al menos un servicio previo en estado `Confirmada` o posterior: reserva de grabación `Confirmada`, `En curso` o `Finalizada`, o asesoría `Confirmada` o `Realizada`. |
| RN-14 | La asesoría se agenda con un profesional concreto dentro de sus horarios publicados, en múltiplos de 30 min (mínimo 30 min); modalidad `presencial` (lugar acordado) o `virtual` (enlace de videollamada). Tiene precio fijo y genera una única cuota `al_reservar`. Un profesional no tiene dos asesorías solapadas. |
| RN-15 | El precio de una reserva lo calcula el sistema sumando cada componente (el servicio y cada especialista, con el ingeniero de sonido por defecto): parte variable por tiempo según su unidad (hora o lapso de 30 min) más el recargo de cada bloque en horario de noche, fin de semana o feriado, y parte fija que se cobra siempre (0 si no tiene). La simulación pública usa el mismo cálculo y no tiene valor de cotización ([ADR-009](../00-proyecto/decisiones/ADR-009-reservas-tarifas-y-caducidad.md)). |
| RN-16 | Tras una asesoría, el estudio puede emitir una cotización formal con precio y plan de cuotas (monto con fecha o hito) que reemplaza el 50/50. Las reservas y la posproducción que cuelgan de una cotización aceptada no generan cuotas propias. El costo de la asesoría no se descuenta salvo que la cotización lo indique. |
| RN-17 | Una reserva se hace con al menos 2 horas y como mucho 8 semanas de anticipación (ajustables por el Administrador) ([ADR-009](../00-proyecto/decisiones/ADR-009-reservas-tarifas-y-caducidad.md)). |
| RN-18 | Una reserva `Pre-reservada` sin ningún pago registrado caduca 3 días antes de su inicio, o 1 hora después de solicitarla si faltaban menos de 3 días; en todo caso, el cliente tiene al menos esa hora (vence lo más tarde entre ambos momentos) y el plazo nunca pasa del inicio. Registrar un pago con captura detiene el plazo; si el Administrador lo rechaza, el cliente tiene 1 hora más. Al caducar pasa a `Cancelada` (caducada) y el tramo se libera. Los plazos son ajustables ([ADR-009](../00-proyecto/decisiones/ADR-009-reservas-tarifas-y-caducidad.md)). |
| RN-19 | Visitante y cliente ven solo libre u ocupado; el cliente ve sus reservas; personal y Administrador ven todas con el cliente y el servicio. |
| RN-20 | El cliente cancela sin costo su reserva mientras no haya registrado ningún pago; el tramo se libera al momento. Con pagos registrados aplica D-11. |
| RN-21 | Se avisa por correo al reservar (con la fecha límite de pago) y al caducar una reserva. |

## Pagos

| ID | Regla |
|---|---|
| RN-03 | Una reserva de sala pasa a `Confirmada` cuando el Administrador valida su cuota `al_reservar` (o la que fije su cotización). Una asesoría, cuando valida su cuota única. |
| RN-04 | Todo pago se registra contra una cuota con método (`transferencia`, `yape`, `plin`, `tarjeta`), monto en PEN, número de operación y captura. Queda `Pendiente de validacion` hasta que el Administrador lo aprueba o lo rechaza con motivo ([ADR-004](../00-proyecto/decisiones/ADR-004-pagos-validacion-manual.md)). |
| RN-05 | La posproducción (mezcla/máster) tiene precio propio: 50% `al_encargar` y 50% `al_aprobar_version` por el cliente, salvo cotización a medida. |
| RN-06 | La descarga del máster se habilita solo tras validar la cuota `al_aprobar_version` (o la última cuota del plan de la cotización). |

## Entregables y personal

| ID | Regla |
|---|---|
| RN-07 | El enlace de descarga es cifrado, autenticado y caduca a los 7 días calendario. |
| RN-08 | Nomenclatura de entregables incremental y automática: `PRJ<nn>_<Track>_v<mayor>.<menor>.wav` (ej. `PRJ01_Track_v1.0.wav`). |
| RN-09 | Solo se aceptan entregables WAV sin pérdida. |
| RN-10 | Cada proyecto tiene un límite de rondas de corrección pactadas; cada observación consume del saldo según la ronda vigente. |
| RN-11 | El personal técnico se asigna según la especialidad del proyecto, solo a sesiones `Confirmada`. |

## Abiertas

- D-05: límite por defecto de rondas.
- D-06: cerrada para reservas de sala (RN-18, [ADR-009](../00-proyecto/decisiones/ADR-009-reservas-tarifas-y-caducidad.md)); la caducidad de la asesoría `Pendiente de pago` se decide con RF-15.
- D-11: cancelación y reembolso.

Ver [decisiones](../00-proyecto/decisiones/README.md).
