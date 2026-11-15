---
id: flujo-registrar-reserva
titulo: CUS-04 Registrar reserva de sala
estado: borrador
depende_de: [RF-03, RF-04, RF-05, RN-01, RN-02, RN-03, RN-12, RN-13, RN-15]
---

# CUS-04 Registrar reserva de sala

Aplica a reservas de tipo `grabacion` y `ensayo`.

1. El visitante o cliente consulta las franjas publicadas de la semana ([RF-03](../../03-requerimientos/RF-03.md)) y elige sala, tipo y un tramo en múltiplos de 30 min ([RN-12](../reglas-negocio.md)).
2. Ve la simulación de precio ([RN-15](../reglas-negocio.md)) y deja el detalle de lo que necesita.
3. Si no tiene cuenta, la crea en este paso ([RF-01](../../03-requerimientos/RF-01.md)). Para un `ensayo`, el caso de uso exige un servicio previo `Confirmada` ([RN-13](../reglas-negocio.md)).
4. El caso de uso verifica que el tramo y su buffer de 30 min caben en la franja y no se solapan con otra reserva ([RN-01](../reglas-negocio.md), [RN-02](../reglas-negocio.md)).
5. Crea la reserva `Pre-reservada` con su folio y genera sus cuotas: 50% `al_reservar` y 50% `al_terminar` ([RN-13](../reglas-negocio.md)). Si la reserva cuelga de una cotización aceptada, no genera cuotas: manda el plan de la cotización ([RN-16](../reglas-negocio.md)).
6. El cliente registra el pago de la primera cuota con su captura ([RF-05](../../03-requerimientos/RF-05.md)).
7. El Administrador valida el comprobante; la reserva pasa a `Confirmada` ([RN-03](../reglas-negocio.md)). Si lo rechaza, el cliente sube otro.
8. Al terminar la sesión, la reserva pasa a `Finalizada` y el cliente paga la cuota `al_terminar` por el mismo mecanismo.

Estados: [estados-reserva](../estados-reserva.md). Requerimientos: [RF-04](../../03-requerimientos/RF-04.md), [RF-05](../../03-requerimientos/RF-05.md).
