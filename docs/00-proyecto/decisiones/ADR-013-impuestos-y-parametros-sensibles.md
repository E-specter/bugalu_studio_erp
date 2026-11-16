---
id: ADR-013
titulo: IGV incluido en los precios y cambios de parámetros sensibles con barreras
estado: aprobado
depende_de: [D-09, ADR-009, ADR-010]
---

# ADR-013: IGV incluido en los precios y cambios de parámetros sensibles con barreras

## Contexto

El estudio opera como EIRL y está obligado a emitir boletas o facturas con IGV del 18 %. Faltaba decidir cómo se muestran los impuestos y cómo se protegen los cambios de tarifas y plazos (D-09).

## Decisión

Usuario, 2026-11-16:

- **Precios con IGV incluido.** El cliente ve siempre el total. La app indica "incluye IGV (18 %)" con el desglose informativo en simulaciones, reservas, cotizaciones y pagos.
- **Parámetros sensibles con barreras:** el porcentaje de IGV, la opción "precios incluyen IGV", las **tarifas** y los **plazos de pago** solo los cambia el Administrador en un flujo que muestra el impacto, pide escribir una palabra para confirmar, aplica solo a operaciones nuevas (las existentes guardan su precio) y registra quién, cuándo, valor anterior y nuevo.

## Consecuencias

- Configuración de impuestos y registro de auditoría de cambios ([RF-20](../../03-requerimientos/RF-20.md)); las pantallas de tarifas y parámetros pasan por el flujo.
- La emisión de boletas y facturas sigue fuera de la plataforma en la v1 ([ADR-010](ADR-010-pagos-estados-y-cancelacion.md)), salvo que se decida integrarla con SUNAT.
