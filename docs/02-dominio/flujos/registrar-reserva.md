---
id: flujo-registrar-reserva
titulo: CUS-04 Registrar reserva
estado: borrador
depende_de: [RF-03, RF-04, RF-05, RN-01, RN-02, RN-03]
---

# CUS-04 Registrar reserva

1. El cliente selecciona sala, fecha y horario en el calendario.
2. El caso de uso verifica la operatividad de la sala y que no haya solapamientos ([RN-01](../reglas-negocio.md)).
3. Crea la reserva `Pre-reservada` con buffer de 30 min ([RN-02](../reglas-negocio.md)) y calcula el anticipo del 50%.
4. El cliente confirma; el módulo `pagos` procesa el cobro con la pasarela.
5. Con la autorización (`codigo_autorizacion`), registra `comprobante_pago` y cambia la reserva a `Confirmada` ([RN-03](../reglas-negocio.md)).
6. Devuelve el folio de reserva al cliente.

Requerimientos: [RF-04](../../03-requerimientos/RF-04.md), [RF-05](../../03-requerimientos/RF-05.md). Estados: [estados-reserva](../estados-reserva.md).
