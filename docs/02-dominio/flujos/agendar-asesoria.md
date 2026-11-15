---
id: flujo-agendar-asesoria
titulo: CUS-15 Agendar asesoría artística
estado: borrador
depende_de: [RF-15, RN-14, RN-16]
---

# CUS-15 Agendar asesoría artística

1. El visitante o cliente elige un profesional artístico y ve sus horarios publicados.
2. Elige un horario en múltiplos de 30 min y la modalidad: `presencial` (lugar acordado) o `virtual` (enlace de videollamada) ([RN-14](../reglas-negocio.md)).
3. Si no tiene cuenta, la crea en este paso ([RF-01](../../03-requerimientos/RF-01.md)).
4. El caso de uso verifica que el profesional no tenga otra asesoría solapada y crea la asesoría `Pendiente de pago` con su precio fijo y una cuota única `al_reservar`.
5. El cliente registra el pago con su captura ([RF-05](../../03-requerimientos/RF-05.md)); el Administrador lo valida y la asesoría pasa a `Confirmada`.
6. Se da la asesoría y el profesional la marca `Realizada`.
7. Si se acuerda un servicio, el estudio emite una cotización a medida con su plan de cuotas ([RF-02](../../03-requerimientos/RF-02.md), [RN-16](../reglas-negocio.md)). Al aceptarla, el cliente reserva sus sesiones contra esa cotización ([registrar-reserva](registrar-reserva.md)).

Estados: [estados-reserva](../estados-reserva.md#asesoría). Requerimiento: [RF-15](../../03-requerimientos/RF-15.md).
