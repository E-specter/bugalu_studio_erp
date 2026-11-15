---
id: alcance
titulo: Alcance del producto
estado: borrador
depende_de: [vision]
---

# Alcance

## Dentro del alcance (v1)

Usuarios, catálogo con simulación de precio y cotizaciones a medida, franjas y reservas de sala (grabación y ensayo), asesorías, pagos con validación manual, personal técnico, proyectos musicales, entregables de audio, feedback, cierre y reportes.

Cada capacidad tiene su requerimiento en [03-requerimientos](../README.md#requerimientos) (RF-01 a RF-15) y su módulo de backend en [backend-hexagonal](../01-arquitectura/backend-hexagonal.md#módulos-del-backend).

## Fuera del alcance (v1)

- Cuentas para Sello discográfico / Mánager y Músico de sesión ([ADR-008](decisiones/ADR-008-acceso-y-roles-v1.md)); mejora posible: colaboradores invitados por proyecto (RF-08).

## Pendiente de definir

- Impuestos y facturación electrónica (D-09; la moneda ya es PEN).
- Políticas de cancelación y reembolso (D-11).

Ver [decisiones abiertas](decisiones/README.md).
