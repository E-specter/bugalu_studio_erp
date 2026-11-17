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
| RN-18 | Una reserva `Pre-reservada` sin ningún pago registrado caduca 3 días antes de su inicio, o 1 hora después de solicitarla si faltaban menos de 3 días; en todo caso, el cliente tiene al menos esa hora (vence lo más tarde entre ambos momentos) y el plazo nunca pasa del inicio. Registrar un pago con captura detiene el plazo; si el Administrador lo rechaza y no queda otro pago en validación, el plazo pasa a lo más tarde entre el actual y 1 hora después del rechazo, sin pasar del inicio. Una reserva con un pago en validación no caduca. Al caducar pasa a `Cancelada` (caducada) y el tramo se libera. Los plazos son ajustables ([ADR-009](../00-proyecto/decisiones/ADR-009-reservas-tarifas-y-caducidad.md)). |
| RN-19 | Visitante y cliente ven solo libre u ocupado; el cliente ve sus reservas; personal y Administrador ven todas con el cliente y el servicio. |
| RN-20 | Cancelar con pagos depende de la anticipación ([RF-18](../03-requerimientos/RF-18.md), [ADR-015](../00-proyecto/decisiones/ADR-015-cancelacion-conservacion-y-correcciones.md)). Sin pagos registrados, el cliente cancela sin costo y el tramo se libera al momento. Con pagos, los niveles usan los plazos guardados en la reserva: nivel 1 (más de 48 h antes) pasa lo pagado a crédito de 30 días, y el Administrador puede devolverlo; nivel 2 (más de 24 h y hasta 48 h) retiene la penalización del 25 % del total, como máximo lo pagado, y el resto va a crédito; nivel 3 (24 h o menos) retiene lo pagado. La inasistencia se marca desde 15 min después del inicio y retiene lo pagado. El Administrador puede tratar una cancelación de nivel 2 o 3, o una inasistencia, como nivel 1, con motivo. El cliente reprograma sin costo en nivel 1 y con penalización en nivel 2, con un máximo de 2 reprogramaciones (1 en nivel 2); en nivel 3 no reprograma. Si el estudio cancela con pagos, el cliente elige reprogramar sin costo o la devolución íntegra. Los plazos y porcentajes son ajustables. Sustituye la v1 de [ADR-010](../00-proyecto/decisiones/ADR-010-pagos-estados-y-cancelacion.md). |
| RN-21 | Se avisa por correo al reservar (con la fecha límite de pago y los datos para pagar) y al caducar una reserva; al cliente, cuando su pago se aprueba (con la reserva confirmada) o se rechaza (con el motivo), al finalizar con saldo pendiente, cuando el estudio cancela su reserva (con las dos opciones si hay pagos), al cancelar con pagos (nivel, lo retenido y el crédito con su vencimiento), al reprogramar (con el nuevo horario), al marcar inasistencia, 7 días antes de que venza un crédito y al decidir o marcar realizada una devolución; a los administradores, cuando llega un pago por validar, cuando un cliente cancela, pide una devolución o elige tras una cancelación del estudio. |
| RN-23 | Una reserva `Confirmada` pasa sola a `En curso` al llegar su inicio y a `Finalizada` al llegar su fin. Una `Pre-reservada` con pago en validación no avanza ni caduca; si llega a su fin sin confirmarse, pasa a `No asistió` (RN-20). La agenda la marca "pago por validar" ([ADR-010](../00-proyecto/decisiones/ADR-010-pagos-estados-y-cancelacion.md)). Una reserva en `No asistió` retiene lo pagado. |
| RN-25 | Antes de su primera reserva o asesoría, el cliente tiene nombre, documento de identidad (DNI, CE o pasaporte), teléfono y correo, y aceptada la versión mayor vigente de los términos de uso; cada reserva y asesoría registra la aceptación de la versión vigente de las condiciones de contratación, que la rige aunque cambien después. Las casillas nunca vienen marcadas y las promociones tienen un consentimiento aparte y revocable ([RF-17](../03-requerimientos/RF-17.md), [ADR-012](../00-proyecto/decisiones/ADR-012-textos-legales-y-consentimientos.md)). |
| RN-26 | Un menor de 18 años reserva solo con la autorización de su madre, padre o tutor (datos, documento, aceptación en la app y documento firmado); su reserva no se confirma hasta que el estudio valida ese documento, y sin el adulto responsable en el recinto la sesión no empieza ([RF-17](../03-requerimientos/RF-17.md), [ADR-015](../00-proyecto/decisiones/ADR-015-cancelacion-conservacion-y-correcciones.md)). |

## Pagos

| ID | Regla |
|---|---|
| RN-03 | Una reserva de sala pasa a `Confirmada` cuando el Administrador valida su cuota `al_reservar` (o la que fije su cotización). Una asesoría, cuando valida su cuota única. |
| RN-04 | Todo pago se registra contra una cuota con método (`transferencia`, `yape`, `plin`, `tarjeta`), el monto en PEN que el cliente realmente pagó, número de operación y una captura (JPG, PNG o PDF de hasta 5 MB). Queda `Pendiente de validacion` hasta que el Administrador lo aprueba (la cuota queda pagada aunque el monto difiera, a su criterio) o lo rechaza con motivo; la aprobación no se deshace. Una cuota no admite otro pago mientras tenga uno en validación; el número de operación no se repite con el mismo método salvo en pagos rechazados. La cuota `al_terminar` se puede pagar desde que la reserva está `Confirmada` ([ADR-004](../00-proyecto/decisiones/ADR-004-pagos-validacion-manual.md), [ADR-010](../00-proyecto/decisiones/ADR-010-pagos-estados-y-cancelacion.md)). |
| RN-05 | La posproducción (mezcla/máster) tiene precio propio: 50% `al_encargar` y 50% `al_aprobar_version` por el cliente, salvo cotización a medida. |
| RN-06 | La descarga del máster se habilita solo tras validar la cuota `al_aprobar_version` (o la última cuota del plan de la cotización). |
| RN-22 | El Administrador mantiene un texto de datos para pagar por método (banco, cuenta, CCI, número de Yape o Plin, titular) y si el método está activo; el cliente los ve al registrar el pago y en el correo de la reserva, y solo paga con métodos activos ([ADR-010](../00-proyecto/decisiones/ADR-010-pagos-estados-y-cancelacion.md)). |
| RN-24 | Los precios incluyen IGV (18 %); el desglose es informativo: base = total / (1 + tasa) redondeada al céntimo e IGV = total − base. El porcentaje de IGV, "precios incluyen IGV", las tarifas, los recargos, los plazos de pago y de cancelación y el porcentaje de adelanto solo los cambia el Administrador con vista previa del impacto, confirmación escrita y registro de quién, cuándo, valor anterior y nuevo; el cambio rige solo para operaciones nuevas ([RF-20](../03-requerimientos/RF-20.md), [ADR-013](../00-proyecto/decisiones/ADR-013-impuestos-y-parametros-sensibles.md)). |

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
