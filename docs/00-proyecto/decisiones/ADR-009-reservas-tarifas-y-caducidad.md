---
id: ADR-009
titulo: Franjas, reservas de sala, tarifas y caducidad
estado: aprobado
depende_de: [D-06, ADR-004, ADR-007, ADR-008]
---

# ADR-009: Franjas, reservas de sala, tarifas y caducidad

## Contexto

RF-03 y RF-04 necesitan cerrar cómo se publica la disponibilidad, cómo se calcula el precio y cuánto se mantiene una reserva sin pagar (D-06). El estudio tiene hoy **una sola sala**, en su sede de La Molina (Lima). Los pagos se validan a mano ([ADR-004](ADR-004-pagos-validacion-manual.md)).

## Decisión

Usuario, 2026-11-16 (respuestas a las preguntas de RF-03/04):

| Tema | Decisión |
|---|---|
| Salas | Una sala (sede La Molina). El modelo admite varias salas y sedes; no se construye su gestión |
| Franjas | El Administrador las **publica a mano** según la disponibilidad de los especialistas. Al crear, el sistema **sugiere una plantilla** (editable, no definitiva). Excepciones: cerrar un día u horas (feriados, mantenimiento) o abrir horas extra |
| Tramo libre | Hueco de ≥ 30 min dentro de una franja publicada que el cliente reserva **para un servicio concreto** |
| Servicios que ocupan sala | Grabación (voces, instrumentos, banda en vivo), ensayo y live session. Mezcla y máster no ocupan sala (van por proyecto, RF-11) |
| Precio | Por hora según el servicio, **con recargo por horario** (noche, fin de semana, feriados). Se suman **especialistas** con tarifa propia: **monto fijo + monto variable por lapso** (p. ej. 25 × lapsos + 30). El ingeniero de sonido viene incluido por defecto, con tarifa editable. Otros: ejecutante, especialista audiovisual, productor o arreglista |
| Anticipación | Mínimo 2 horas antes del inicio; máximo 8 semanas. Ajustables |
| Duración | De 30 min a 8 horas por reserva, en múltiplos de 30 min. Varios días = varias reservas |
| Caducidad (cierra D-06) | Sin pago, la reserva se mantiene **hasta 3 días antes del inicio** si se reservó con más de 3 días; si no, **1 hora desde la solicitud**. Ajuste confirmado por el usuario (2026-11-16, [RN-18](../../02-dominio/reglas-negocio.md)): vence lo más tarde entre ambos momentos y nunca después del inicio, para que el cliente tenga siempre al menos esa hora. Se detiene al **registrar un pago con captura**. Si el Administrador lo rechaza, el cliente tiene **1 hora más** para subir otro. Si vence, se cancela por caducidad y el tramo se libera. Los dos plazos son **ajustables** |
| Calendario | Vista **semanal** por defecto y **mensual** con la misma información: cada día muestra en texto cuántas horas libres tiene y abre su semana |
| Visibilidad | Visitante y cliente ven libre u ocupado, nunca quién reservó; el cliente ve sus reservas; personal y Administrador ven todas con cliente y servicio |
| Avisos | Correo al reservar (con la fecha límite de pago) y al caducar |
| Cancelación | El cliente cancela su reserva **sin costo mientras no haya registrado ningún pago**; con anticipo pagado sigue D-11 |
| Acceso social | Genérico: lista configurable de proveedores de Supabase Auth; se activan **Google y Meta (Facebook)** para artistas y clientes ([ADR-008](ADR-008-acceso-y-roles-v1.md)) |

**Modelo de precio (confirmado por el usuario, 2026-11-16):** **cada componente de la reserva** (el servicio y cada especialista) tiene una **parte variable** por tiempo, con su unidad (hora o lapso de 30 min) y sujeta a recargo por horario, y una **parte fija** que se cobra siempre, una vez por reserva (0 si no tiene). El recargo es un porcentaje por tipo de horario sobre la parte variable de los bloques que caen en ese horario, nunca sobre la fija. Los montos los carga el Administrador. Sin casilla de condiciones al reservar hasta que el estudio tenga el texto legal.

**Confirmaciones del usuario (2026-11-16) a decisiones tomadas durante la implementación:**
1. Si en un bloque coinciden varios recargos, se aplica el mayor (en empate, feriado y luego fin de semana), no la suma ([RF-02](../../03-requerimientos/RF-02.md)).
2. Mientras D-11 siga abierta, tampoco el Administrador cancela una reserva con pagos (409 `tiene_pagos`).
3. Plazo de pago (RN-18): vence lo más tarde entre inicio − días e instante de la reserva + horas, nunca después del inicio.
4. Personal y Administrador también pueden reservar para sí mismos.
5. El ensayo exige una reserva previa de otro servicio `Confirmada`, `En curso` o `Finalizada` (la asesoría se suma con RF-15).

## Parte técnica (leader)

- **Parámetros ajustables** en una tabla editable por el Administrador: plazo largo (días), plazo corto (horas), anticipación mínima (horas) y máxima (semanas).
- **Caducidad sin depender de un reloj externo:** la disponibilidad trata como libre una reserva `Pre-reservada` vencida aunque aún no esté marcada; una tarea periódica de la base (`pg_cron`, cada minuto) la marca `Cancelada` por caducidad y encola el aviso.
- **Correos por bandeja de salida:** la tabla `notificacion` guarda cada aviso; el backend los envía por SMTP (Mailpit en local, `http://127.0.0.1:45624`). El proveedor real sigue en D-07.
- **El precio lo calcula el backend** con el mismo motor para la simulación pública (RN-15) y para el monto de la reserva; el cliente nunca envía precios.

## Consecuencias

- Nuevas tablas de catálogo y tarifas (servicio, especialista y tarifa, recargo por horario, feriado), de franjas (plantilla, franja, excepción), parámetros y bandeja de notificaciones ([modelo-datos](../../01-arquitectura/modelo-datos.md)).
- `reserva` pasa de `tipo` a `id_servicio` (la categoría del servicio dice si es ensayo, RN-13) y guarda el precio calculado y su fecha límite de pago.
- RF-03 y RF-04 reciben criterios y contrato; RF-02 aporta el motor de precio (la cotización a medida sigue para más adelante).
- D-06 queda cerrada; D-07 (proveedor de correo) y D-11 (reembolsos) siguen abiertas.
