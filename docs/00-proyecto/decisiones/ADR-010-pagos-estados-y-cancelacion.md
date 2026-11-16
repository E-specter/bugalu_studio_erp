---
id: ADR-010
titulo: Pagos con captura, estados automáticos de la reserva y cancelación con pagos (v1)
estado: aprobado
depende_de: [D-09, D-11, ADR-003, ADR-004, ADR-007, ADR-009]
---

# ADR-010: Pagos con captura, estados automáticos de la reserva y cancelación con pagos (v1)

## Contexto

RF-05 y RF-06 necesitaban cerrar cómo se registra y valida un pago (sin pasarela, [ADR-004](ADR-004-pagos-validacion-manual.md)), qué ve el cliente para pagar, cómo avanza la reserva tras confirmarse y qué pasa al cancelar una reserva con pagos (D-11). Con los pagos funcionando, la regla anterior (nadie cancela con pagos) dejaba bloqueada una reserva pagada que el cliente no puede usar.

## Decisión

Usuario, 2026-11-16 (acepta todas las propuestas de leader):

| Tema | Decisión |
|---|---|
| Monto | Cada pago va contra una cuota con el monto que el cliente realmente pagó. Si no coincide con la cuota, el Administrador lo ve marcado y decide. La cuota queda pagada solo al aprobarse |
| Cuándo se paga | La cuota `al_reservar`, desde que existe la reserva; la `al_terminar` se puede adelantar en cuanto la reserva está `Confirmada` |
| Un pago a la vez | Una cuota no admite otro pago mientras tenga uno en validación |
| Datos para pagar | Un texto por método (banco, cuenta, CCI, número de Yape o Plin, titular) editable por el Administrador; se muestra al registrar el pago y en el correo de la reserva |
| Captura | Una por pago: JPG, PNG o PDF, hasta 5 MB |
| Número de operación | Obligatorio en todos los métodos; no se repite con el mismo método salvo que el anterior se rechazara. Tarjeta: POS del estudio o enlace del banco, con el número del voucher |
| Validación | Solo el Administrador. Rechazo con motivo obligatorio (sugerencias: "el monto no coincide", "operación no encontrada", "captura ilegible"). Una aprobación no se deshace en v1 |
| Avisos | Al cliente: pago aprobado (con la reserva confirmada), pago rechazado con motivo, saldo pendiente al finalizar y cancelación por el estudio. A los administradores: pago por validar y cancelación del cliente |
| Pago sin validar al llegar la sesión | La reserva sigue `Pre-reservada`: no caduca (tiene un pago registrado) ni avanza; la agenda la marca "pago por validar" |
| En curso y Finalizada | Automático por la hora: al inicio, `Confirmada` → `En curso`; al fin, → `Finalizada`, y se avisa del saldo pendiente |
| Personal asignado | Los avisos al personal llegan con la asignación (RF-07/08); por ahora, cliente y administradores |
| Cancelación con pagos (D-11, v1) | El cliente con pagos registrados no cancela por sí mismo: lo pide al estudio. El Administrador sí cancela, con una nota obligatoria de cómo se gestiona el reembolso (o que no lo hay), fuera del sistema. Sustituye la confirmación 2 de [ADR-009](ADR-009-reservas-tarifas-y-caducidad.md) |
| Facturación (D-09) | Fuera de v1: la boleta o factura se emite fuera de la app |

## Parte técnica (leader)

- **Captura:** el backend recibe el formulario con el archivo, valida tamaño y tipo por la firma de los bytes (no por la extensión ni por el `Content-Type`), registra el pago dentro de una transacción, sube la captura a `comprobantes/<id_cliente>/<id_pago>.<ext>` con el token del propio usuario y solo entonces confirma; si la subida falla, la transacción se deshace y no queda nada (si fallara la confirmación tras subir, el archivo queda huérfano y se registra en el log). Políticas RLS en `storage.objects` ([ADR-003](ADR-003-almacenamiento-supabase-storage.md)): el dueño inserta y lee en su carpeta, el Administrador lee todo, nadie actualiza ni borra (la captura es evidencia inmutable). El bucket limita tamaño y tipos como segunda barrera. Para ver una captura, el backend entrega una URL firmada de pocos minutos. Sin clave de servicio en el backend ([ADR-007](ADR-007-acceso-postgres-directo.md)).
- **Caducidad:** `tiene_pagos()` cuenta los pagos en validación o aprobados. Al rechazarse un pago, si no queda otro vigente, `vence_pago` pasa a lo más tarde entre el actual y ahora + `horas_limite_pago`, sin pasar del inicio.
- **Estados:** una función de base en `pg_cron` cada minuto (como la caducidad) avanza las reservas y encola los avisos; es idempotente.
- **Avisos:** por la bandeja `notificacion` (ADR-009) con tipos nuevos.

## Consecuencias

- Tablas `comprobante_pago` e `instruccion_pago`; columna `nota_cancelacion` en `reserva`; políticas de `storage.objects` para `comprobantes`; nuevos tipos de `notificacion` ([modelo-datos](../../01-arquitectura/modelo-datos.md)).
- [RF-05](../../03-requerimientos/RF-05.md) y [RF-06](../../03-requerimientos/RF-06.md) reciben criterios y contrato; RN-04, RN-18, RN-20 y RN-21 se precisan; nuevas RN-22 (datos para pagar) y RN-23 (estados automáticos).
- D-11 queda parcial (política mínima de v1); D-09: facturación fuera de v1. D-07 (proveedor de correo) sigue abierta.
