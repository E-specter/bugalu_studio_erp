---
id: ADR-004
titulo: Pagos sin pasarela en v1, con validación manual
estado: aprobado
depende_de: [D-02]
---

# ADR-004: Pagos sin pasarela en v1, con validación manual

## Contexto

El estudio opera en Perú y cobra en soles (PEN). Hoy sus clientes pagan por transferencia, billetera móvil (Yape, Plin) o tarjeta, envían la captura del comprobante y el estudio la valida antes de dar el pago por bueno. El usuario exige esa validación para aprobar cualquier pago. No hay hosting (D-08), así que no hay URL pública para recibir confirmaciones de una pasarela.

## Opciones consideradas

1. **Sin pasarela: el cliente registra el pago y sube la captura; el Administrador lo valida.**
2. Pasarela peruana (Culqi, Izipay, Niubiz, Mercado Pago): cobro en línea con confirmación automática. Exige cuenta de comercio, validación del negocio y una URL pública para los webhooks, y la validación manual seguiría siendo obligatoria.

## Decisión

Opción 1 (usuario, 2026-11-15). Todo pago se registra con método (`transferencia`, `yape`, `plin`, `tarjeta`), monto en PEN, número de operación y captura, y queda pendiente hasta que el Administrador lo aprueba o lo rechaza con motivo ([RN-04](../../02-dominio/reglas-negocio.md)).

## Consecuencias

- El módulo `pagos` define el puerto `PasarelaPagos` con un único adaptador manual; una pasarela real será otro adaptador, sin tocar el dominio ([backend-hexagonal](../../01-arquitectura/backend-hexagonal.md)).
- La confirmación de una reserva depende de la validación del Administrador, no de una respuesta automática ([RN-03](../../02-dominio/reglas-negocio.md)).
- Las capturas se guardan en el bucket privado `comprobantes` ([ADR-003](ADR-003-almacenamiento-supabase-storage.md)).
- El actor externo deja de ser "Pasarela de Pagos" y pasa a ser "Banco / billetera", sin integración ([actores-roles](../../02-dominio/actores-roles.md)).
- D-09 queda parcialmente cerrada: moneda PEN. Impuestos y facturación electrónica siguen abiertos.
